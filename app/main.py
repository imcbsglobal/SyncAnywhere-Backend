from fastapi import FastAPI
from app.routes import sync

app = FastAPI(
    title="SyncAnywhere API",
    description="API for syncing data between SQL Anywhere and Mobile app",
    version="1.0.0"
)

app.include_router(sync.router)
