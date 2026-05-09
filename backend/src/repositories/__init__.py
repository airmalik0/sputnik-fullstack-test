"""Repository layer.

A thin wrapper over SQLAlchemy that turns "here is a question for the DB"
into "here is a method call". Repositories are deliberately dumb: they hold
no business rules, only queries.

Why bother having a layer at all when SQLAlchemy is already an abstraction?
Two reasons:

  * It pins the DB query patterns to one place. Tomorrow we may want to add
    `selectinload`, eager-loading, or rewrite a query for performance —
    that change happens in one file, not scattered across services.
  * Services can be unit-tested with hand-written fakes (in-memory dicts)
    that satisfy the same shape, without spinning up a database.

Repositories receive an `AsyncSession` from the caller and never commit.
The caller (a service or task) owns the transaction boundary, which keeps
multi-step business operations atomic.
"""
