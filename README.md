# Тестовое задание Fullstack — рефакторинг файлообменника

Бэкенд: FastAPI + SQLAlchemy (async) + Celery + Redis + Postgres.
Фронтенд: Next.js (App Router) + React-Bootstrap + react-query.

Поведение API сохранено байт-в-байт: те же эндпоинты, те же схемы
ответов, те же правила сканирования и алертов. Изменилась внутренняя
структура, добавлены тесты, починены инфраструктурные баги, проведена
неочевидная оптимизация Celery-пайплайна.

## Запуск

```bash
docker compose -f docker-compose.dev.yml up
docker exec -it backend alembic upgrade head
```

- Фронт: `http://localhost:3000/test`
- Бэк (Swagger): `http://localhost:8000/docs`

## Бэкенд: что изменилось

### Архитектура

Монолитный `service.py` распилен на семь слоёв с однонаправленным
графом зависимостей:

```
api ──► services ──► repositories ──► domain
                ╰──► storage
                ╰──► core (config, db, logging)

tasks ──► services ──► repositories ──► domain
                  ╰──► storage
                  ╰──► core
```

| Слой           | Зачем                                                                 |
| -------------- | --------------------------------------------------------------------- |
| `core/`        | Settings (pydantic-settings), DB-фабрика, логирование                 |
| `domain/`      | ORM-модели, enum'ы, доменные исключения. Не знает про FastAPI/Celery |
| `repositories/`| Только запросы. Не коммитят, не валидируют, не raise'ят NotFound      |
| `storage/`     | `FileStorage` Protocol + `LocalFileStorage` с атомарной записью       |
| `services/`    | Бизнес-правила. Поднимают доменные исключения                          |
| `api/`         | Роутеры + DI + exception handlers + DTO. Единственное место с FastAPI |
| `tasks/`       | Celery-задачи. Используют сервисы напрямую                            |

Сервисы и репозитории получают зависимости через конструктор; в
тестах подставляются in-memory fakes (см. `tests/fakes.py`) без БД и
без диска.

### Неочевидная оптимизация

Главное изменение — в `src/tasks/process_file.py`.

Исходный пайплайн состоял из трёх Celery-задач, склеенных через
`.delay()`:

```
scan_file_for_threats(id) ──► extract_file_metadata(id) ──► send_file_alert(id)
```

На каждый загруженный файл это стоило:

- 3 round-trip'а через Redis (по одному на `.delay()`);
- 3 свежих SQLAlchemy-сессии и 3 `SELECT`'а одной и той же строки;
- 3 коммита транзакций;
- скрытая гонка: при redelivery'е брокером два шага могли наложиться,
  переписав поля `StoredFile` друг друга.

При этом задачи **всегда выполнялись вместе и линейно зависели друг
от друга** — никакой выгоды от трёх отдельных тасков не было.

В новом коде это **одна** задача `process_file`, выполняющая всё в
**одной транзакции на одной сессии**. Кросс-таск гонка исчезла по
конструкции (одной сессии не с кем конфликтовать), нагрузка на
Redis/Postgres упала ~3×, поведение пользователя осталось идентичным.

**Trade-off:** теряем гранулярность retry на уровне отдельного шага.
Не страшно: исходный код её не использовал, шаги дешёвые и
идемпотентные.

### Сопутствующие perf-правки

- **Стриминг загрузок** — `UploadFile.read(64*1024)` в цикле
  доходит до `LocalFileStorage.save_stream`, который пишет атомарно
  через `tempfile + os.replace + fsync`. Раньше файл сначала читался
  целиком в память, потом синхронно записывался — для крупных
  загрузок это ОЗУ-вотчина и unsafe-write.
- **SHA-256 в один проход** — хеш считается тем же циклом, что и
  запись; никакого второго чтения файла. Сохраняется в БД (новая
  nullable колонка), используется как fingerprint.
- **PDF через `pypdf`** — ленивое чтение трейлера + xref; вместо
  `read_bytes()` всего файла и эвристического `count(b"/Type /Page")`,
  который к тому же давал неверный ответ для нестандартных PDF.
- **Bounded text reads** — `text/*` файлы читаются максимум до
  `text_metadata_byte_limit` байт (по умолчанию 5 МБ). Раньше
  `read_text()` без ограничения превращал `application/octet-stream`-
  залитый 5 ГБ лог в OOM воркера.

### Атомарность операций

- **Загрузка**: блоб пишется во временный файл в той же директории,
  затем `fsync`, `os.replace`, `fsync` на директорию. Частично
  записанный файл никогда не виден под финальным именем. Если на
  любом шаге падаем — temp удаляется, БД не трогали.
- **Удаление**: сначала commit БД, потом удаление с диска. Сирота на
  диске (запись удалена, файл остался) — recoverable периодическим
  cleanup-job'ом; обратный сценарий (запись есть, файла нет) — 404
  каждый раз. Выбрали меньшее зло.

### Прочее

- `os.environ.get` заменён на `pydantic-settings` — невалидная
  конфигурация падает на старте с понятной ошибкой, а не при первом
  SQL-запросе.
- `REDIS_URL` (которой не было в `.env.dev`) → `CELERY_BROKER_URL`
  (которая была, но игнорировалась).
- `backend` и `backend-worker` теперь оба `depends_on: backend-redis`.
- `processing_status`/`scan_status`/`level` — `Enum`'ы на стороне
  кода; колонки остаются `VARCHAR` (избегаем `ALTER TYPE` и его
  лочной семантики).

## Фронтенд: что изменилось

Монолитный `page.tsx` (367 строк) разнесён по слоям feature-sliced
шаблона:

```
shared/         config, api-клиент, форматтеры, ui-примитивы
entities/file/  типы, api, react-query хук, FilesTable
entities/alert/ типы, api, хук, AlertsTable
features/upload-file/  модалка + мутация
app/            layout (с Providers), page (только композиция, ~80 строк)
```

`page.tsx` теперь только композирует — никакой fetch-логики,
форматирования, рендера таблиц или валидации форм.

### React Query с адаптивным поллингом

`useFiles()` поллит каждые 2 секунды, пока **хотя бы один** файл
находится в нетерминальном состоянии (`uploaded`/`processing`).
Когда все файлы доходят до `processed`/`failed`, поллинг
останавливается сам. Раньше пользователь должен был жать «Обновить»,
чтобы увидеть результат сканирования.

Загрузка — `useMutation` с инвалидацией обоих списков (files и
alerts) на success.

### Прочее

- `API_URL` через `NEXT_PUBLIC_API_URL` (раньше захардкожен в трёх
  местах).
- `tsconfig.json`: `strict: true`, `@/*` → `src/*`.
- Сломанные строки в `Dockerfile` (`COPY .env.production`) и
  `layout.tsx` (`/public/favicon.ico`) убраны.

## Тесты

`uv run pytest` — 24 теста, ~150 ms, без БД и без диска:

- `test_scan_service` — параметризованная таблица правил
  сканирования (расширение/MIME/размер → вердикт). Покрывает
  allow-list PDF, кейс-инсенситив расширений, edge-of-threshold.
- `test_metadata_extractor` — line/char counting под byte-cap'ом,
  парсинг настоящего PDF через pypdf, graceful fallback на
  битом PDF.
- `test_file_service` — контракт create/delete/download против
  in-memory fakes; среди прочего проверяет, что пустая загрузка
  чистит блоб.

## Структура

```
backend/
  src/
    core/         config, db, logging
    domain/       models, enums, exceptions
    repositories/ file_repository, alert_repository
    storage/      base (Protocol), local (atomic POSIX impl)
    services/     file_service, scan_service, metadata_extractor, alert_service
    api/          dependencies, exception_handlers, schemas, routers/
    tasks/        celery_app, process_file
    app.py        FastAPI factory (composition root)
  tests/          24 unit-теста с in-memory fakes
  migrations/     Alembic; добавлена ревизия для sha256

frontend/
  src/
    shared/       config, api-клиент, lib, ui
    entities/     file/, alert/ — types/api/hooks/ui
    features/     upload-file/ — модалка + мутация
    app/          layout, providers, page (композиция)
```

## Что осталось бы сделать на следующем этапе

- Janitor-задача периодической сверки БД и диска (orphan blob
  cleanup).
- Реальный антивирусный сканер (clamd) вместо эвристики по
  расширениям.
- Аутентификация и rate-limit на загрузку.
- Структурированное логирование (JSON) и трассировка через
  OpenTelemetry.
