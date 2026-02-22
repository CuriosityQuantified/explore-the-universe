from fastapi import FastAPI

from api.routers.health import router as health_router
from api.routers.test_upload import router as test_upload_router

app = FastAPI(
    title="Explore the Universe",
    version="0.1.0",
    description="Galactic encyclopedia API",
)

app.include_router(health_router)
app.include_router(test_upload_router)
