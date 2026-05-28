"""Cross-cutting infrastructure helpers used by the application.

The ``core`` package is intentionally framework-adjacent: settings, logging,
security, rate limiting, caching, metrics, Sentry, OpenAPI customization, and
domain exceptions live here because they are shared by multiple feature areas.
"""
