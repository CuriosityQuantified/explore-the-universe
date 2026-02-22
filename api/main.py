from fastapi import FastAPI

from api.routers.health import router as health_router

app = FastAPI(
    title="Explore the Universe",
    version="0.1.0",
    description="Galactic encyclopedia API",
)

app.include_router(health_router)
