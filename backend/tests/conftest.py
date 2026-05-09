"""Test bootstrap.

We don't need a database to test ScanService, MetadataExtractor or
FileService — by design. The only `conftest`-level concern is making
sure imports work; pytest-asyncio is configured in pyproject.toml with
asyncio_mode='auto', so async tests don't need explicit decorators.
"""

import os

# Settings(...) instantiates eagerly when something imports the config
# module. We give it placeholder values so test collection doesn't
# require a real database to be reachable.
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("PGPORT", "5432")
