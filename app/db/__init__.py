"""Database engine, session, and dependency helpers.

Application code should normally receive sessions through ``app.db.deps`` and
avoid constructing engines or sessions directly. That keeps request lifecycle
management in one place and makes tests easier to override.
"""
