"""Cross-cutting infrastructure: configuration, logging, database wiring.

Modules here are leaf dependencies — they must not import from `domain`,
`services`, `repositories`, `api` or `tasks`. This keeps the dependency graph
acyclic and makes `core` safe to import from anywhere, including Alembic and
Celery worker bootstrap.
"""
