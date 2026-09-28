import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import admin, auth
from .pickem_2026 import admin_routes as pickem_2026_admin_routes
from .pickem_2026 import routes as pickem_2026_routes
from .pickem_2026 import schema as pickem_2026_schema
from .fantasy_2026_27 import routes as fantasy_2026_27_routes
from .fantasy_2026_27 import schema as fantasy_2026_27_schema
from .nba import routes as nba_routes
from .nba import schema as nba_schema
from .nba import scheduler as nba_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth.init_schema()            # users — shared across every module
    pickem_2026_schema.init_schema()
    nba_schema.init_schema()      # shared NBA data (schedule, box scores), read by every season
    fantasy_2026_27_schema.init_schema()
    sync_task = nba_scheduler.start()
    yield
    if sync_task:
        sync_task.cancel()


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(pickem_2026_routes.router, prefix="/pickem/2026")
app.include_router(pickem_2026_admin_routes.router, prefix="/pickem/2026")
app.include_router(fantasy_2026_27_routes.router, prefix="/fantasy/2026_27")
app.include_router(nba_routes.router, prefix="/nba")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
