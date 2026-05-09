"""HTTP transport layer.

Routers, request/response schemas, dependency wiring and exception
handlers live here. This is the only layer aware of FastAPI; everything
below this line is framework-agnostic.

The package is structured so a hypothetical second transport (gRPC, a
CLI) could be added beside `api/` and reuse `services` and `repositories`
unchanged.
"""
