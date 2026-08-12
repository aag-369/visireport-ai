import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.api.ws_routes import router as ws_router
from app.config import get_settings
from app.vision.inference import YoloEngine
from app.ws.progress_hub import run_event_relay

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("visireport.main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    YoloEngine.instance().load()
    relay_task = asyncio.create_task(run_event_relay())
    logger.info("VisiReport AI backend started (environment=%s)", settings.environment)
    yield
    relay_task.cancel()


app = FastAPI(
    title="VisiReport AI",
    description="Automated Optical Inspection (AOI) backend for medical-grade PCBA - "
    "real YOLO inference, tiling, schema validation, RabbitMQ, LLM narrative synthesis.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)
