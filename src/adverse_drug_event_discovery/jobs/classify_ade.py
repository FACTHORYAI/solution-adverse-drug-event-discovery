"""Classify conversational texts as reporting an adverse drug event or not."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.jobs._duck import align
from adverse_drug_event_discovery.schemas import ADE_CLASSIFICATION, REJECTED
from adverse_drug_event_discovery.text.interface import TextModel
from adverse_drug_event_discovery.text.parse import parse_object, validate_classification_item

INPUTS = ("ade_events",)
OUTPUTS = ("ade_classification", "rejected_classifications")


@dataclass(frozen=True)
class Params:
    """Parameters for ADE classification."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the predicted ADE flag per text and every answer that failed validation."""
    events = inputs["ade_events"]
    instructions = io.read_prompt("classify_ade")
    rows: list[dict] = []
    rejected: list[dict] = []
    for record in events.to_pylist():
        answer = model.complete(instructions, record["text"])
        try:
            item = parse_object(answer)
            reason = validate_classification_item(item)
        except ValueError as error:
            reason = str(error)
        if reason:
            rejected.append({"id": record["id"], "reason": reason, "model_answer": answer})
            continue
        rows.append({"id": record["id"], "predicted_ade": bool(item["predicted_ade"])})
    return {
        "ade_classification": align(
            pa.Table.from_pylist(rows, schema=ADE_CLASSIFICATION), ADE_CLASSIFICATION
        ),
        "rejected_classifications": align(
            pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED
        ),
    }
