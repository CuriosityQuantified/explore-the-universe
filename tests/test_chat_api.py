"""Tests for the AI chat API endpoint.

POST /api/chat — translates natural-language questions into structured
catalog queries using Claude tool use, executes them against the DB, and
returns an answer with object cards.

All tests are offline-by-construction:
  - The Anthropic client is patched so no real API calls are made.
  - The database session is overridden with a mock so no live DB is needed.

Mock strategy mirrors tests/test_structured_search_api.py:
  - _make_chained_mock() returns a session whose query chain always resolves.
  - The Anthropic client is patched at api.routers.chat.anthropic.Anthropic.
"""

import uuid
import unittest.mock as mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.db.session import get_database_session
from api.routers.chat import SEARCH_OBJECTS_TOOL, router
from api.routers.objects import StructuredSearchFilters
from shared.models import AstronomicalObject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_with_mock_session(mock_session):
    """Return a TestClient with the DB session dependency overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database_session] = lambda: mock_session
    return TestClient(app)


def _make_obj(
    uuid_str: str = "aaaaaaaa-0000-0000-0000-000000000001",
    obj_type: str = "spiral_galaxy",
    name: str = "NGC 1234",
    anomaly: bool = False,
    cutout_prefix: str = None,
    magnitude: float = 15.0,
    obs_uuid: str = "bbbbbbbb-0000-0000-0000-000000000001",
):
    obj = mock.MagicMock(spec=AstronomicalObject)
    obj.object_uuid = uuid_str
    obj.classified_object_type = obj_type
    obj.catalog_object_name = name
    obj.is_anomaly_flagged = anomaly
    obj.cutout_s3_prefix = cutout_prefix
    obj.catalog_magnitude = magnitude
    obj.source_observation_uuid = uuid.UUID(obs_uuid)
    return obj


def _make_chained_mock(objects, count=None, types=None, total=None, mag_row=None):
    """Return a mock session where all SQLAlchemy chain methods resolve properly.

    The chat endpoint calls:
      session.query(AstronomicalObject.classified_object_type)
        .distinct().filter(...).limit(50).all()           <- types list
      session.query(AstronomicalObject).count()            <- total count
      session.query(func.min(...), func.max(...)).first()  <- mag range
      session.query(AstronomicalObject).filter()...        <- main search

    We configure session.query to return mock_query for all these.
    """
    if types is None:
        types = [("spiral_galaxy",), ("elliptical_galaxy",)]
    if total is None:
        total = len(objects)
    if mag_row is None:
        mag_row = (10.0, 20.0)

    mock_session = mock.MagicMock()
    mock_query = mock.MagicMock()

    mock_session.query.return_value = mock_query

    # All chaining methods return the same mock_query
    mock_query.filter.return_value = mock_query
    mock_query.distinct.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query

    # Terminal methods
    mock_query.all.return_value = types  # first call: types list; reused for object list
    mock_query.count.return_value = total
    mock_query.first.return_value = mag_row

    return mock_session, mock_query


def _make_chained_mock_with_objects(objects, types=None, total=None, mag_row=None):
    """Variant where .all() returns object list (not types).

    We configure .all() to return types on the first call and objects on all
    subsequent calls, because the endpoint first queries types then objects.
    """
    if types is None:
        types = [("spiral_galaxy",)]
    if total is None:
        total = len(objects)
    if mag_row is None:
        mag_row = (10.0, 20.0)

    mock_session = mock.MagicMock()
    mock_query = mock.MagicMock()

    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.distinct.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query

    # First .all() call returns types, second returns objects
    mock_query.all.side_effect = [types, objects]
    mock_query.count.return_value = total
    mock_query.first.return_value = mag_row

    return mock_session


def _make_anthropic_response(text: str = None, tool_input: dict = None):
    """Build a mock Anthropic Messages response."""
    content_blocks = []

    if text:
        text_block = mock.MagicMock()
        text_block.type = "text"
        text_block.text = text
        content_blocks.append(text_block)

    if tool_input is not None:
        tool_block = mock.MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "search_objects"
        tool_block.input = tool_input
        content_blocks.append(tool_block)

    response = mock.MagicMock()
    response.content = content_blocks
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChatApi:

    def test_search_objects_tool_matches_structured_schema(self):
        properties = SEARCH_OBJECTS_TOOL["input_schema"]["properties"]

        assert set(properties) == set(StructuredSearchFilters.model_fields)
        assert properties["type"]["maxItems"] == 50
        assert properties["type"]["items"]["maxLength"] == 200
        assert properties["sort_by"]["enum"] == [
            "magnitude",
            "type",
            "angular_separation",
        ]

    def test_chat_logs_executed_query(self, caplog):
        mock_session = _make_chained_mock_with_objects([_make_obj()])
        anthropic_response = _make_anthropic_response(
            text="Found galaxies.",
            tool_input={"type": ["spiral_galaxy"], "limit": 5},
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                with caplog.at_level("INFO", logger="api.routers.chat"):
                    resp = client.post("/api/chat", json={"message": "Find galaxies"})

        assert resp.status_code == 200
        assert any(
            "AI chat executed structured object query" in record.message
            for record in caplog.records
        )

    # ------------------------------------------------------------------
    # 1. Claude returns tool_use block → objects populated
    # ------------------------------------------------------------------

    def test_chat_returns_answer_and_objects(self):
        obj = _make_obj()
        mock_session = _make_chained_mock_with_objects([obj])
        anthropic_response = _make_anthropic_response(
            text="Here are the brightest spiral galaxies.",
            tool_input={"type": ["spiral_galaxy"], "sort_by": "magnitude", "limit": 5},
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post("/api/chat", json={"message": "Show me spiral galaxies"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Here are the brightest spiral galaxies."
        assert len(data["objects"]) == 1
        assert data["objects"][0]["type"] == "spiral_galaxy"
        assert data["objects"][0]["catalog_name"] == "NGC 1234"
        assert data["query_executed"] == {"type": ["spiral_galaxy"], "sort_by": "magnitude", "limit": 5}

    # ------------------------------------------------------------------
    # 2. Claude returns text only (no tool call) → objects=[], query_executed=None
    # ------------------------------------------------------------------

    def test_chat_no_tool_call(self):
        mock_session, _ = _make_chained_mock([])
        anthropic_response = _make_anthropic_response(
            text="I cannot translate that into a catalog query."
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post("/api/chat", json={"message": "What is the meaning of life?"})

        assert resp.status_code == 200
        data = resp.json()
        assert "I cannot translate" in data["answer"]
        assert data["objects"] == []
        assert data["query_executed"] is None

    # ------------------------------------------------------------------
    # 3. Anthropic raises APIError → 503 response
    # ------------------------------------------------------------------

    def test_chat_anthropic_unavailable(self):
        import anthropic as anthropic_lib
        mock_session, _ = _make_chained_mock([])

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.side_effect = anthropic_lib.APIError(
                message="Service unavailable",
                request=mock.MagicMock(),
                body=None,
            )
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post("/api/chat", json={"message": "Find anomalies"})

        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()

    # ------------------------------------------------------------------
    # 4. Empty API key → 503 "AI service not configured"
    # ------------------------------------------------------------------

    def test_chat_no_api_key(self):
        mock_session, _ = _make_chained_mock([])

        with mock.patch("api.routers.chat.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            client = _make_app_with_mock_session(mock_session)
            resp = client.post("/api/chat", json={"message": "Find galaxies"})

        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"]

    # ------------------------------------------------------------------
    # 5. context.observation_uuid passed → included in query
    # ------------------------------------------------------------------

    def test_chat_with_observation_context(self):
        obs_uuid = "bbbbbbbb-0000-0000-0000-000000000001"
        obj = _make_obj(obs_uuid=obs_uuid)
        mock_session = _make_chained_mock_with_objects([obj])
        anthropic_response = _make_anthropic_response(
            text="Found objects in that observation.",
            tool_input={"observation_uuid": obs_uuid, "limit": 10},
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post(
                    "/api/chat",
                    json={
                        "message": "What objects are in this observation?",
                        "context": {"observation_uuid": obs_uuid},
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["query_executed"]["observation_uuid"] == obs_uuid
        assert len(data["objects"]) == 1

    # ------------------------------------------------------------------
    # 6. Tool returns malformed input → no crash, graceful empty response
    # ------------------------------------------------------------------

    def test_chat_graceful_on_invalid_tool_input(self):
        mock_session, _ = _make_chained_mock([])
        # Claude returns tool input with an invalid sort_by value
        anthropic_response = _make_anthropic_response(
            text="",
            tool_input={"sort_by": "invalid_field_xyz", "limit": 5},
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post("/api/chat", json={"message": "Show me stuff"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["objects"] == []
        # query_executed is still returned (the raw tool input)
        assert data["query_executed"] == {"sort_by": "invalid_field_xyz", "limit": 5}

    # ------------------------------------------------------------------
    # 7. detail_url is /objects/{uuid}
    # ------------------------------------------------------------------

    def test_chat_response_includes_detail_url(self):
        uuid_str = "cccccccc-0000-0000-0000-000000000001"
        obj = _make_obj(uuid_str=uuid_str)
        mock_session = _make_chained_mock_with_objects([obj])
        anthropic_response = _make_anthropic_response(
            text="Found one object.",
            tool_input={"type": ["spiral_galaxy"]},
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post("/api/chat", json={"message": "Show galaxies"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["objects"]) == 1
        assert data["objects"][0]["detail_url"] == f"/objects/{uuid_str}"

    # ------------------------------------------------------------------
    # 8. query_executed matches the tool input returned by Claude
    # ------------------------------------------------------------------

    def test_chat_query_executed_returned(self):
        obj = _make_obj()
        mock_session = _make_chained_mock_with_objects([obj])
        tool_input = {
            "type": ["elliptical_galaxy"],
            "is_anomaly": True,
            "sort_by": "magnitude",
            "sort_order": "desc",
            "limit": 10,
        }
        anthropic_response = _make_anthropic_response(
            text="Here are anomaly-flagged elliptical galaxies.",
            tool_input=tool_input,
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post(
                    "/api/chat",
                    json={"message": "Find anomaly-flagged elliptical galaxies, brightest first"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["query_executed"] == tool_input
        assert data["objects"][0]["type"] == "spiral_galaxy"

    # ------------------------------------------------------------------
    # 9. Server enforces observation_uuid when Claude omits it from tool call
    # ------------------------------------------------------------------

    def test_context_uuid_injected_when_claude_omits_it(self):
        obs_uuid = "bbbbbbbb-0000-0000-0000-000000000001"
        obj = _make_obj(obs_uuid=obs_uuid)
        mock_session = _make_chained_mock_with_objects([obj])
        # Claude returns tool call WITHOUT observation_uuid
        anthropic_response = _make_anthropic_response(
            text="Found galaxies.",
            tool_input={"type": ["spiral_galaxy"], "limit": 5},
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post(
                    "/api/chat",
                    json={
                        "message": "Show spiral galaxies",
                        "context": {"observation_uuid": obs_uuid},
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        # Server must have injected the observation_uuid into query_executed
        assert data["query_executed"]["observation_uuid"] == obs_uuid

    def test_context_uuid_cannot_be_overridden_by_claude(self):
        selected_obs_uuid = "bbbbbbbb-0000-0000-0000-000000000001"
        claude_obs_uuid = "bbbbbbbb-0000-0000-0000-000000000002"
        mock_session = _make_chained_mock_with_objects([_make_obj(obs_uuid=selected_obs_uuid)])
        anthropic_response = _make_anthropic_response(
            text="Found galaxies.",
            tool_input={"observation_uuid": claude_obs_uuid, "limit": 5},
        )

        with mock.patch("api.routers.chat.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = anthropic_response
            with mock.patch("api.routers.chat.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = _make_app_with_mock_session(mock_session)
                resp = client.post(
                    "/api/chat",
                    json={
                        "message": "Show galaxies",
                        "context": {"observation_uuid": selected_obs_uuid},
                    },
                )

        assert resp.status_code == 200
        assert resp.json()["query_executed"]["observation_uuid"] == selected_obs_uuid

    # ------------------------------------------------------------------
    # 10. observation_uuid exceeding 36 chars is rejected with 422
    # ------------------------------------------------------------------

    def test_context_uuid_too_long_rejected(self):
        mock_session, _ = _make_chained_mock([])
        long_uuid = "x" * 37  # exceeds max_length=36

        with mock.patch("api.routers.chat.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            client = _make_app_with_mock_session(mock_session)
            resp = client.post(
                "/api/chat",
                json={
                    "message": "Find galaxies",
                    "context": {"observation_uuid": long_uuid},
                },
            )

        assert resp.status_code == 422
