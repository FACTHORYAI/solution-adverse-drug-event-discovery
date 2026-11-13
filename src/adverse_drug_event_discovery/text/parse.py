"""Parse and validate model answers before they become table rows."""

from __future__ import annotations

import json

ENTITY_TYPES = ("ADE", "DRUG")
ASSERTION_STATUSES = (
    "Present",
    "Absent",
    "Possible",
    "Hypothetical",
    "Conditional",
    "Someone_else",
)


def parse_items(answer: str) -> list[dict]:
    """Parse a model answer that must be a JSON array of objects."""
    try:
        items = json.loads(answer)
    except json.JSONDecodeError as error:
        message = f"model answer is not JSON: {error.msg} at position {error.pos}"
        raise ValueError(message) from error
    if not isinstance(items, list):
        message = "model answer is not a JSON array"
        raise ValueError(message)
    return [item for item in items if isinstance(item, dict)]


def parse_object(answer: str) -> dict:
    """Parse a model answer that must be one JSON object."""
    try:
        item = json.loads(answer)
    except json.JSONDecodeError as error:
        message = f"model answer is not JSON: {error.msg} at position {error.pos}"
        raise ValueError(message) from error
    if not isinstance(item, dict):
        message = "model answer is not a JSON object"
        raise ValueError(message)
    return item


def _check_confidence(item: dict) -> str:
    confidence = item.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return "confidence is not a number"
    if not 0 <= float(confidence) <= 1:
        return "confidence is not between 0 and 1"
    return ""


def validate_classification_item(item: dict) -> str:
    """Return the reason the classification is rejected, or "" when it is valid."""
    predicted = item.get("predicted_ade")
    if not isinstance(predicted, bool):
        return "predicted_ade is not a boolean"
    return ""


def validate_entity_item(item: dict) -> str:
    """Return the reason the entity row is rejected, or "" when it is valid."""
    chunk = item.get("chunk")
    if not isinstance(chunk, str) or not chunk.strip():
        return "missing or empty chunk"
    entity = item.get("entity")
    if entity not in ENTITY_TYPES:
        return f"entity is not one of {ENTITY_TYPES}"
    return _check_confidence(item)


def validate_assertion_item(item: dict) -> str:
    """Return the reason the assertion row is rejected, or "" when it is valid."""
    chunk = item.get("chunk")
    if not isinstance(chunk, str) or not chunk.strip():
        return "missing or empty chunk"
    assertion = item.get("assertion")
    if assertion not in ASSERTION_STATUSES:
        return f"assertion is not one of {ASSERTION_STATUSES}"
    return _check_confidence(item)


def validate_relation_item(item: dict) -> str:
    """Return the reason the relation row is rejected, or "" when it is valid."""
    relation = item.get("relation")
    if relation not in ("0", "1"):
        return 'relation is not "0" or "1"'
    for key in ("entity1", "entity2"):
        if item.get(key) not in ENTITY_TYPES:
            return f"{key} is not one of {ENTITY_TYPES}"
    for key in ("chunk1", "chunk2"):
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            return f"missing or empty {key}"
    return _check_confidence(item)
