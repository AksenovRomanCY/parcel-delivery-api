"""Background task scheduler and delivery recalculation jobs.

Task functions are importable from both the standalone scheduler process and
manual operational HTTP endpoints. Keep task code idempotent where possible so
either entrypoint can trigger it safely.
"""
