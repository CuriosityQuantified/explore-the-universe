"""Regression suite: Phase 6 — observations list API endpoint.

GET /api/observations  — all ingested observations with pipeline status,
object/classified/anomaly counts, and processing step timeline.

All tests are offline — no network, no live DB, no running services required.
Uses FastAPI TestClient with a mock database session dependency.
"""

import uuid
import unittest.mock as mock
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from shared.models import AstronomicalObject, Observation, ProcessingStep


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(mock_session):
    from api.main import app
    from api.db.session import get_database_session

    app.dependency_overrides[get_database_session] = lambda: mock_session
    return app


def _teardown(app):
    from api.db.session import get_database_session

    app.dependency_overrides.pop(get_database_session, None)


def _make_obs(
    obs_uuid=None,
    archive_id="jw01234001001_04101_00001_nrca1",
    pipeline_status=None,
    ingested_at=None,
):
    from shared.models import PipelineStatus

    obs = mock.MagicMock(spec=Observation)
    obs.observation_uuid = obs_uuid or uuid.uuid4()
    obs.archive_observation_id = archive_id
    obs.pipeline_status = pipeline_status or PipelineStatus.completed
    obs.ingested_at = ingested_at or datetime(2026, 8, 7, 12, 0, 0)
    return obs


def _make_step(
    step_name="download_fits",
    step_status=None,
    step_started_at=None,
    step_completed_at=None,
):
    from shared.models import StepStatus

    step = mock.MagicMock(spec=ProcessingStep)
    step.step_name = step_name
    step.step_status = step_status or StepStatus.completed
    step.step_started_at = step_started_at or datetime(2026, 8, 7, 12, 0, 0)
    step.step_completed_at = step_completed_at or datetime(2026, 8, 7, 12, 0, 30)
    return step


def _session_for(
    obs_list,
    steps,
    object_count=3,
    classified_count=2,
    anomaly_count=1,
):
    """Build a mock Session routing query() calls by model class.

    AstronomicalObject queries are count-only — we return the supplied counts
    in call order (object_count first, then classified_count, then
    anomaly_count) per observation.
    """
    mock_session = mock.MagicMock()

    # Track how many times AstronomicalObject has been queried to cycle counts.
    ao_call_count = {"n": 0}
    counts_cycle = (
        [object_count, classified_count, anomaly_count] * len(obs_list)
        if obs_list
        else []
    )

    def query_side_effect(model_class):
        q = mock.MagicMock()
        if model_class is Observation:
            q.order_by.return_value.all.return_value = obs_list
        elif model_class is AstronomicalObject:
            idx = ao_call_count["n"]
            ao_call_count["n"] += 1
            count_val = counts_cycle[idx] if idx < len(counts_cycle) else 0
            q.filter.return_value.count.return_value = count_val
        elif model_class is ProcessingStep:
            q.filter.return_value.order_by.return_value.all.return_value = steps
        return q

    mock_session.query.side_effect = query_side_effect
    return mock_session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestObservationsList:
    def test_empty_list_returns_200_empty_array(self):
        mock_session = _session_for(obs_list=[], steps=[])
        app = _make_app(mock_session)
        try:
            with TestClient(app) as client:
                resp = client.get("/api/observations")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            _teardown(app)

    def test_single_observation_structure(self):
        obs_uuid = uuid.uuid4()
        obs = _make_obs(obs_uuid=obs_uuid, archive_id="jw99999001001_test")
        step = _make_step(step_name="download_fits")
        mock_session = _session_for(
            obs_list=[obs],
            steps=[step],
            object_count=10,
            classified_count=8,
            anomaly_count=2,
        )
        app = _make_app(mock_session)
        try:
            with TestClient(app) as client:
                resp = client.get("/api/observations")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            item = data[0]
            assert item["observation_uuid"] == str(obs_uuid)
            assert item["archive_observation_id"] == "jw99999001001_test"
            assert item["pipeline_status"] == "completed"
            assert "ingested_at" in item
            assert item["object_count"] == 10
            assert item["classified_count"] == 8
            assert item["anomaly_count"] == 2
        finally:
            _teardown(app)

    def test_steps_included_in_response(self):
        obs = _make_obs()
        step1 = _make_step(step_name="download_fits")
        step2 = _make_step(
            step_name="validate_wcs",
            step_completed_at=datetime(2026, 8, 7, 12, 1, 0),
        )
        mock_session = _session_for(obs_list=[obs], steps=[step1, step2])
        app = _make_app(mock_session)
        try:
            with TestClient(app) as client:
                resp = client.get("/api/observations")
            data = resp.json()
            steps = data[0]["steps"]
            assert len(steps) == 2
            assert steps[0]["step_name"] == "download_fits"
            assert steps[0]["step_status"] == "completed"
            assert steps[0]["step_completed_at"] is not None
            assert steps[1]["step_name"] == "validate_wcs"
        finally:
            _teardown(app)

    def test_pipeline_status_values_preserved(self):
        from shared.models import PipelineStatus

        for status in PipelineStatus:
            obs = _make_obs(pipeline_status=status)
            mock_session = _session_for(obs_list=[obs], steps=[])
            app = _make_app(mock_session)
            try:
                with TestClient(app) as client:
                    resp = client.get("/api/observations")
                assert resp.status_code == 200
                assert resp.json()[0]["pipeline_status"] == status.value
            finally:
                _teardown(app)

    def test_observation_with_no_steps(self):
        obs = _make_obs()
        mock_session = _session_for(obs_list=[obs], steps=[])
        app = _make_app(mock_session)
        try:
            with TestClient(app) as client:
                resp = client.get("/api/observations")
            data = resp.json()
            assert data[0]["steps"] == []
        finally:
            _teardown(app)

    def test_multiple_observations_returned(self):
        obs1 = _make_obs(archive_id="jw00001")
        obs2 = _make_obs(archive_id="jw00002")
        mock_session = _session_for(
            obs_list=[obs1, obs2],
            steps=[],
            object_count=5,
            classified_count=3,
            anomaly_count=0,
        )
        app = _make_app(mock_session)
        try:
            with TestClient(app) as client:
                resp = client.get("/api/observations")
            data = resp.json()
            assert len(data) == 2
            archive_ids = {d["archive_observation_id"] for d in data}
            assert archive_ids == {"jw00001", "jw00002"}
        finally:
            _teardown(app)

    def test_required_fields_present(self):
        obs = _make_obs()
        mock_session = _session_for(obs_list=[obs], steps=[])
        app = _make_app(mock_session)
        try:
            with TestClient(app) as client:
                resp = client.get("/api/observations")
            item = resp.json()[0]
            for field in (
                "observation_uuid",
                "archive_observation_id",
                "pipeline_status",
                "ingested_at",
                "object_count",
                "classified_count",
                "anomaly_count",
                "steps",
            ):
                assert field in item, f"Missing field: {field}"
        finally:
            _teardown(app)
