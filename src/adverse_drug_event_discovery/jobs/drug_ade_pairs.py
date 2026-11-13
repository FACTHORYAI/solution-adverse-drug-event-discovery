"""Drug-ADE pairs by co-occurrence within the same conversation."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.jobs._duck import align, run_query
from adverse_drug_event_discovery.schemas import DRUG_ADE_PAIRS

INPUTS = ("entities",)
OUTPUTS = ("drug_ade_pairs",)


@dataclass(frozen=True)
class Params:
    """Parameters for the drug-ade-pairs job."""

    min_confidence: float = 0.6
    min_conversations: int = 1


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the drug-ADE pairs a conversation mentions together, with their counts."""
    if not 0 <= params.min_confidence <= 1:
        message = f"Parameter min_confidence is {params.min_confidence}; it must be between 0 and 1"
        raise ValueError(message)
    if params.min_conversations < 1:
        message = (
            f"Parameter min_conversations is {params.min_conversations}; it must be at least 1"
        )
        raise ValueError(message)
    table = run_query(
        io.read_sql("drug_ade_pairs"),
        inputs,
        {"min_confidence": params.min_confidence, "min_conversations": params.min_conversations},
    )
    return {"drug_ade_pairs": align(table, DRUG_ADE_PAIRS)}
