"""Extract the adverse-drug-event and drug pairs that belong together."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.jobs._duck import align
from adverse_drug_event_discovery.schemas import REJECTED, RELATIONS
from adverse_drug_event_discovery.text.interface import TextModel
from adverse_drug_event_discovery.text.parse import parse_items, validate_relation_item

INPUTS = ("ade_events",)
OUTPUTS = ("relations", "rejected_relations")


@dataclass(frozen=True)
class Params:
    """Parameters for relation extraction."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the related ADE-DRUG pairs and every answer that failed validation."""
    events = inputs["ade_events"]
    instructions = io.read_prompt("extract_relations")
    rows: list[dict] = []
    rejected: list[dict] = []
    for record in events.to_pylist():
        answer = model.complete(instructions, record["text"])
        try:
            items = parse_items(answer)
        except ValueError as error:
            rejected.append(
                {"text_id": record["text_id"], "reason": str(error), "model_answer": answer}
            )
            items = []
        for item in items:
            reason = validate_relation_item(item)
            if reason:
                rejected.append(
                    {"text_id": record["text_id"], "reason": reason, "model_answer": str(item)}
                )
                continue
            rows.append(
                {
                    "text_id": record["text_id"],
                    "relation": item["relation"],
                    "entity1": item["entity1"],
                    "chunk1": item["chunk1"],
                    "entity2": item["entity2"],
                    "chunk2": item["chunk2"],
                    "confidence": float(item["confidence"]),
                }
            )
    return {
        "relations": align(pa.Table.from_pylist(rows, schema=RELATIONS), RELATIONS),
        "rejected_relations": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }
