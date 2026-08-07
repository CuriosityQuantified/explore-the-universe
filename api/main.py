from fastapi import FastAPI

from api.routers.health import router as health_router
from api.routers.ingest import router as ingest_router
from api.routers.objects import router as objects_router
from api.routers.observations import router as observations_router
from api.routers.test_upload import router as test_upload_router
from api.routers.tiles import router as tiles_router

app = FastAPI(
    title="Explore the Universe",
    version="0.1.0",
    description="Galactic encyclopedia API",
)

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(objects_router)
app.include_router(observations_router)
app.include_router(test_upload_router)
app.include_router(tiles_router)
