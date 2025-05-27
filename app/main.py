from fastapi import FastAPI

from app.core.logger import setup_logging

setup_logging()

app = FastAPI(
    title="Parcel-Delivery-API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
)
