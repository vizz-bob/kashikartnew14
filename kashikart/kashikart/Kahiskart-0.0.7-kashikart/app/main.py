import sys
import asyncio
import os
from pathlib import Path

# Ensure project root on sys.path when running as a script
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Windows event loop policy is deprecated in Python 3.16; gate it
if sys.platform.startswith("win") and sys.version_info < (3, 13):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import engine, Base
from app.core.scheduler import scheduler, start_scheduler
from fastapi import WebSocket, WebSocketDisconnect
from app.core.realtime import manager

from fastapi.staticfiles import StaticFiles
# One-Drive
from app.core.onedrivescheduler import OneDriveScheduler

# Import routers
from app.routers import (
    auth,
    tenders,
    keywords,
    sources,
    fetch,
    notifications,
    scrape_router,
    onedrive,
    powerbi,
    app_settings,
    excel_control,
    admin_login,
    dashboard,
    system_logs
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Tender Intel System...")

    #  ASYNC SAFE TABLE CREATION
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning(f"Database connection failed, skipping table creation: {str(e)}")

    # Start scheduler
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down Tender Intel System...")
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")

    await engine.dispose()



app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/uploads",
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads",
)

app.mount(
    "/branding",
    StaticFiles(directory=settings.BRANDING_UPLOAD_DIR),
    name="branding"
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(tenders.router, prefix="/api/tenders", tags=["Tenders"])
app.include_router(keywords.router, prefix="/api/keywords", tags=["Keywords"])
app.include_router(sources.router, prefix="/api/sources", tags=["Sources"])
app.include_router(fetch.router, prefix="/api/fetch", tags=["Fetch"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
# Scarpe_Router
app.include_router(scrape_router.router, prefix="/scrape", tags=["Scraping"])
app.include_router(onedrive.router, prefix=settings.API_V1_PREFIX)

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

app.include_router(excel_control.router, prefix="/api/excel_control", tags=["Excel_Control"])
app.include_router(app_settings.router)

app.include_router(admin_login.router)
app.include_router(system_logs.router, prefix="/api/system-logs", tags=["System Logs"])

@app.get("/")
async def root():
    return {
        "message": "Tender Intel API",
        "version": settings.APP_VERSION,
        "status": "operational"
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "running" if scheduler.running else "stopped"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", os.getenv("PORT", "8000")))
    uvicorn.run(app, host=host, port=port, log_level="info")

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
