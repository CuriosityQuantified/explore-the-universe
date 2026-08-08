"""AI chat interface router.

POST /api/chat — translates a natural-language question about the astronomical
catalog into a structured query using Claude's tool-use API, executes the
query against the database, and returns an answer with matching object cards.
"""

import logging
import uuid as _uuid_module
from typing import Any, Dict, List, Optional

import anthropic
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.db.session import get_database_session
from api.routers.objects import (
    StructuredSearchFilters,
    _make_cutout_thumbnail_url,
)
from shared.config import settings
from shared.models import AstronomicalObject

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ChatContext(BaseModel):
    observation_uuid: Optional[str] = Field(None, max_length=36)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    context: Optional[ChatContext] = None


class ChatObjectResult(BaseModel):
    uuid: str
    type: Optional[str] = None
    catalog_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    detail_url: str


class ChatResponse(BaseModel):
    answer: str
    objects: List[ChatObjectResult]
    query_executed: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Tool definition — mirrors StructuredSearchFilters
# ---------------------------------------------------------------------------

SEARCH_OBJECTS_TOOL: Dict[str, Any] = {
    "name": "search_objects",
    "description": (
        "Search the astronomical object catalog with structured filters. "
        "Call this whenever the user asks to find, show, or list objects."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "array",
                "maxItems": 50,
                "items": {"type": "string", "maxLength": 200},
                "description": "One or more classified_object_type values (OR-combined, max 50).",
            },
            "magnitude_min": {
                "type": "number",
                "description": "Minimum catalog magnitude (inclusive).",
            },
            "magnitude_max": {
                "type": "number",
                "description": "Maximum catalog magnitude (inclusive).",
            },
            "redshift_min": {
                "type": "number",
                "description": "Minimum catalog redshift (inclusive).",
            },
            "redshift_max": {
                "type": "number",
                "description": "Maximum catalog redshift (inclusive).",
            },
            "is_anomaly": {
                "type": "boolean",
                "description": "When true, restrict to anomaly-flagged objects only.",
            },
            "observation_uuid": {
                "type": "string",
                "description": "Scope results to one observation UUID.",
            },
            "sort_by": {
                "type": "string",
                "enum": ["magnitude", "type", "angular_separation"],
                "description": "Sort field (magnitude, type, or angular separation).",
            },
            "sort_order": {
                "type": "string",
                "enum": ["asc", "desc"],
                "description": "Sort direction.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 500,
                "description": "Number of results to return (default 24).",
            },
            "offset": {
                "type": "integer",
                "minimum": 0,
                "description": "Page offset (default 0).",
            },
        },
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/api/chat", response_model=ChatResponse)
def chat_query(
    request: ChatRequest = Body(...),
    database_session: Session = Depends(get_database_session),
) -> ChatResponse:
    """Translate a natural-language question into a catalog query and return results."""

    # Require a configured API key before building any prompt
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Build schema summary from live catalog
    types_rows = (
        database_session.query(AstronomicalObject.classified_object_type)
        .distinct()
        .filter(AstronomicalObject.classified_object_type.isnot(None))
        .limit(50)
        .all()
    )
    # Strip newlines and truncate — prevents DB-sourced strings from injecting
    # into the system prompt if catalog type names are ever maliciously crafted.
    types: List[str] = [
        r[0].replace("\n", " ").replace("\r", "").strip()[:64]
        for r in types_rows
        if r[0]
    ]
    total: int = database_session.query(AstronomicalObject).count()
    mag_row = (
        database_session.query(
            func.min(AstronomicalObject.catalog_magnitude),
            func.max(AstronomicalObject.catalog_magnitude),
        ).first()
    )

    schema_summary = f"Catalog has {total} objects."
    if types:
        schema_summary += f" Types: {', '.join(types)}."
    if mag_row and mag_row[0] is not None:
        schema_summary += f" Magnitude range: {mag_row[0]:.1f}–{mag_row[1]:.1f}."

    context_obs_uuid: Optional[str] = None
    context_note = ""
    if request.context and request.context.observation_uuid:
        # Validate UUID format before embedding in the system prompt
        try:
            _uuid_module.UUID(request.context.observation_uuid)
            context_obs_uuid = request.context.observation_uuid
            context_note = f" Active observation UUID: {context_obs_uuid}."
        except ValueError:
            pass

    system_prompt = (
        "You are an AI assistant for an astronomical catalog explorer. "
        f"{schema_summary}{context_note} "
        "When the user asks to find, show, or list objects use the search_objects tool. "
        "If the question cannot be translated to a catalog query, explain why in plain text."
    )

    # Call the Anthropic API
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            tools=[SEARCH_OBJECTS_TOOL],
            messages=[{"role": "user", "content": request.message}],
        )
    except anthropic.APIError:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    # Parse Claude's response into text and optional tool call
    answer_parts: List[str] = []
    tool_input: Optional[Dict[str, Any]] = None

    for block in response.content:
        if block.type == "text":
            answer_parts.append(block.text)
        elif block.type == "tool_use" and block.name == "search_objects":
            tool_input = block.input

    answer = " ".join(answer_parts).strip() or "I searched the catalog for you."

    # No tool call: return text answer with empty object list
    if tool_input is None:
        return ChatResponse(answer=answer, objects=[], query_executed=None)

    # Server-enforce context observation scoping: Claude cannot broaden a query
    # beyond the observation selected by the caller.
    if context_obs_uuid:
        tool_input = {**tool_input, "observation_uuid": context_obs_uuid}

    # Filter tool_input through known StructuredSearchFilters fields before
    # returning in query_executed — prevents unexpected keys from Claude reaching
    # the client response.
    _ALLOWED_QUERY_FIELDS = {
        "type", "magnitude_min", "magnitude_max", "redshift_min", "redshift_max",
        "is_anomaly", "observation_uuid", "sort_by", "sort_order", "limit", "offset",
    }
    query_executed: Dict[str, Any] = {k: v for k, v in tool_input.items() if k in _ALLOWED_QUERY_FIELDS}

    # Validate tool input against the StructuredSearchFilters schema
    try:
        filters = StructuredSearchFilters(**tool_input)
    except Exception:
        return ChatResponse(answer=answer, objects=[], query_executed=query_executed)

    logger.info("AI chat executed structured object query: %s", query_executed)

    # Execute the structured query
    query = database_session.query(AstronomicalObject)

    if filters.type:
        query = query.filter(AstronomicalObject.classified_object_type.in_(filters.type))
    if filters.is_anomaly is not None:
        query = query.filter(AstronomicalObject.is_anomaly_flagged.is_(filters.is_anomaly))
    if filters.observation_uuid:
        try:
            obs_uuid = _uuid_module.UUID(filters.observation_uuid)
            query = query.filter(AstronomicalObject.source_observation_uuid == obs_uuid)
        except ValueError:
            pass
    if filters.magnitude_min is not None:
        query = query.filter(AstronomicalObject.catalog_magnitude >= filters.magnitude_min)
    if filters.magnitude_max is not None:
        query = query.filter(AstronomicalObject.catalog_magnitude <= filters.magnitude_max)
    if filters.redshift_min is not None:
        query = query.filter(AstronomicalObject.catalog_redshift >= filters.redshift_min)
    if filters.redshift_max is not None:
        query = query.filter(AstronomicalObject.catalog_redshift <= filters.redshift_max)

    # Sorting
    sort_by = filters.sort_by or "magnitude"
    sort_col = (
        AstronomicalObject.classified_object_type
        if sort_by == "type"
        else AstronomicalObject.catalog_magnitude
    )
    if (filters.sort_order or "asc") == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    limit = filters.limit if filters.limit is not None else 24
    objs = query.offset(filters.offset or 0).limit(limit).all()

    results = [
        ChatObjectResult(
            uuid=str(obj.object_uuid),
            type=obj.classified_object_type,
            catalog_name=obj.catalog_object_name,
            thumbnail_url=_make_cutout_thumbnail_url(obj.cutout_s3_prefix),
            detail_url=f"/objects/{obj.object_uuid}",
        )
        for obj in objs
    ]

    return ChatResponse(answer=answer, objects=results, query_executed=query_executed)
