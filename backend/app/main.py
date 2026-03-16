from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.generate import router as generate_router
from app.api.routes import router
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Smartbox Content Engine",
    description="Content automation API for Smartbox Group",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(generate_router)

# Serve generated images from the static directory
static_path = Path(__file__).parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
logger.info("static_mounted", path=str(static_path))

# Serve frontend static files — no build step required
frontend_path = Path(__file__).parent.parent.parent / "frontend" / "src"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info("frontend_mounted", path=str(frontend_path))
else:
    logger.warning("frontend_not_found", path=str(frontend_path))
