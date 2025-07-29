from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routes import sync
from app.logging_config import setup_logging
import logging

# ✅ Set up logging BEFORE FastAPI starts
setup_logging()


app = FastAPI(
    title="SyncAnywhere API",
    description="API for syncing data between SQL Anywhere and Mobile app",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "details": str(exc)}
    )

app.include_router(sync.router)
