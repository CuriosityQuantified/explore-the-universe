from api.routers.revision import get_revision
from shared.config import settings


def test_revision_endpoint_returns_configured_revision():
    original_revision = settings.app_revision
    settings.app_revision = "test-revision"
    try:
        response = get_revision()
    finally:
        settings.app_revision = original_revision

    assert response == {"revision": "test-revision"}
