from app.main import app


@app.get("/health", include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}
