"""Judge whether each adverse-drug-event mention is actually experienced."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.jobs._duck import align
from adverse_drug_event_discovery.schemas import ASSERTIONS, REJECTED
from adverse_drug_event_discovery.text.interface import TextModel
from adverse_drug_event_discovery.text.parse import parse_items, validate_assertion_item

INPUTS = ("ade_events",)
OUTPUTS = ("assertions", "rejected_assertions")


@dataclass(frozen=True)
class Params:
    """Parameters for assertion extraction."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the assertion status per ADE mention and every answer that failed validation."""
    events = inputs["ade_events"]
    instructions = io.read_prompt("extract_assertions")
    rows: list[dict] = []
    rejected: list[dict] = []
    for record in events.to_pylist():
        answer = model.complete(instructions, record["text"])
        try:
            items = parse_items(answer)
        except ValueError as error:
            rejected.append({"id": record["id"], "reason": str(error), "model_answer": answer})
            items = []
        for item in items:
            reason = validate_assertion_item(item)
            if reason:
                rejected.append({"id": record["id"], "reason": reason, "model_answer": str(item)})
                continue
            rows.append(
                {
                    "id": record["id"],
                    "chunk": item["chunk"],
                    "entity": "ADE",
                    "assertion": item["assertion"],
                    "confidence": float(item["confidence"]),
                }
            )
    return {
        "assertions": align(pa.Table.from_pylist(rows, schema=ASSERTIONS), ASSERTIONS),
        "rejected_assertions": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }
