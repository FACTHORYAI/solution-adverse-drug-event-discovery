"""Extract adverse-drug-event and drug mentions from conversational texts."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.jobs._duck import align
from adverse_drug_event_discovery.schemas import ENTITIES, REJECTED
from adverse_drug_event_discovery.text.interface import TextModel
from adverse_drug_event_discovery.text.parse import parse_items, validate_entity_item

INPUTS = ("ade_events",)
OUTPUTS = ("entities", "rejected_entities")


@dataclass(frozen=True)
class Params:
    """Parameters for entity extraction."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the ADE and DRUG mentions and every answer that failed validation."""
    events = inputs["ade_events"]
    instructions = io.read_prompt("extract_entities")
    rows: list[dict] = []
    rejected: list[dict] = []
    for record in events.to_pylist():
        answer = model.complete(instructions, record["text"])
        rows.extend(_extracted_rows(record, answer, rejected))
    return {
        "entities": align(pa.Table.from_pylist(rows, schema=ENTITIES), ENTITIES),
        "rejected_entities": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }


def _extracted_rows(record: dict, answer: str, rejected: list[dict]) -> list[dict]:
    """Turn one model answer into table rows, recording failures in rejected."""
    try:
        items = parse_items(answer)
    except ValueError as error:
        rejected.append(
            {"text_id": record["text_id"], "reason": str(error), "model_answer": answer}
        )
        return []
    rows = []
    for item in items:
        reason = validate_entity_item(item)
        if reason:
            rejected.append(
                {"text_id": record["text_id"], "reason": reason, "model_answer": str(item)}
            )
            continue
        rows.append(
            {
                "text_id": record["text_id"],
                "chunk": item["chunk"],
                "entity": item["entity"],
                "confidence": float(item["confidence"]),
            }
        )
    return rows
