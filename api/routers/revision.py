from fastapi import APIRouter

from shared.config import settings

router = APIRouter()


@router.get("/api/revision")
def get_revision():
    return {"revision": settings.app_revision}