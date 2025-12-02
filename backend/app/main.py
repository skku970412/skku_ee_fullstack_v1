from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from . import crud, models, routers
from .config import get_settings
from .database import SessionLocal, engine


def create_app() -> FastAPI:
    settings = get_settings()
    logger = logging.getLogger("ev-backend")
    app = FastAPI(
        title="EV Wireless Charging Backend",
        version="0.1.0",
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(routers.health.router)
    app.include_router(routers.reservations.router)
    app.include_router(routers.admin.router)
    app.include_router(routers.user.router)
    app.include_router(routers.battery.router)
    # Plate recognition proxy
    try:
        from .routers import plates as plates_router  # type: ignore

        app.include_router(plates_router.router)
    except Exception:  # pragma: no cover
        # In case of optional import issues – fail softly during startup
        pass

    @app.on_event("startup")
    def _startup() -> None:
        models.Base.metadata.create_all(bind=engine)
        with engine.begin() as connection:
            inspector = inspect(connection)
            columns = {column["name"] for column in inspector.get_columns("reservations")}
            if "contact_email" not in columns:
                connection.execute(
                    text("ALTER TABLE reservations ADD COLUMN contact_email VARCHAR(255)")
                )
        with SessionLocal() as session:
            crud.migrate_reservation_times_to_utc(session)
            crud.ensure_reservation_slots(session)
            session.commit()
        if settings.auto_seed_sessions:
            with SessionLocal() as session:
                crud.ensure_base_sessions(
                    session,
                    names=[f"세션 {idx}" for idx in range(1, 5)],
                )
            logger.info("Auto-seeded default charging sessions.")

    return app
