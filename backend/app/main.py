from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging
import threading
from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import create_tables, engine
from app.routers import demo, documents, health

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # An unreachable database must not stop the API from booting: /health exists to
    # report that condition, which it cannot do if startup aborts.
    if engine is not None:
        try:
            create_tables()
        except SQLAlchemyError:
            logging.getLogger(__name__).warning(
                "Could not create tables; database is unreachable. See GET /health."
            )
    # Loading the offline risk model takes ~20s, which would leave the first analysis after
    # every restart sitting at 0%. Load it in the background so startup is not delayed.
    threading.Thread(target=_warm_risk_model, daemon=True).start()
    yield


def _warm_risk_model() -> None:
    try:
        from app.classifier.api import classify_clause

        classify_clause("The tenant shall pay rent monthly.", approach="trained")
    except Exception:  # noqa: BLE001 - warming is an optimisation; analysis loads it on demand
        logging.getLogger(__name__).warning("Could not pre-load the offline risk model.", exc_info=True)

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(demo.router)
