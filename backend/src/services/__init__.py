"""Application services — the business rules of the system.

Services depend on:
  * `domain` — the language of the problem;
  * `repositories` — for persistence;
  * `storage` — for binary blobs.

Services do NOT depend on:
  * FastAPI — they raise domain exceptions and return domain objects;
  * Celery — they expose plain async methods that any caller can await.

Two operations the same service is invoked from: an HTTP request handler
and a Celery task. Keeping FastAPI/Celery out of the service is what makes
that possible.
"""
