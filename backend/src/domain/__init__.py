"""Domain layer.

Contains the language of the problem: what a `StoredFile` is, what statuses
it can be in, what alerts mean. The domain layer is intentionally free of
infrastructure concerns — it doesn't know about FastAPI, Celery, S3 or HTTP.

Anything in this package should be safe to use from a unit test without
spinning up a database.
"""
