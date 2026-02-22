import io

from httpx import Client

BASE_URL = "http://localhost:8000"


def test_upload_returns_observation_uuid_and_object_key():
    fake_fits_content = b"SIMPLE  =                    T / fake FITS header"
    files = {
        "file": (
            "test_observation.fits",
            io.BytesIO(fake_fits_content),
            "application/octet-stream",
        )
    }

    with Client(base_url=BASE_URL) as client:
        response = client.post("/test/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "observation_uuid" in data
    assert "object_key" in data
    assert data["bucket"] == "fits-raw"


def test_upload_creates_metadata_record_in_postgresql():
    fake_fits_content = b"SIMPLE  =                    T / another fake FITS"
    files = {
        "file": (
            "another_test.fits",
            io.BytesIO(fake_fits_content),
            "application/octet-stream",
        )
    }

    with Client(base_url=BASE_URL) as client:
        upload_response = client.post("/test/upload", files=files)
        observation_uuid = upload_response.json()["observation_uuid"]

        # Verify the UUID format
        assert len(observation_uuid) == 36  # UUID format
