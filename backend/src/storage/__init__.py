"""Binary storage abstraction.

The interface deliberately models a generic blob store so that the local
filesystem implementation can be swapped for S3 / GCS without touching
service code. We don't have that requirement today, but the abstraction
costs almost nothing and immediately pays back in two ways:

  * Services depend on a `FileStorage` protocol, not on `Path` arithmetic
    sprinkled through business logic.
  * Tests use an in-memory fake storage instead of writing real files,
    which makes them faster and free of cleanup boilerplate.
"""
