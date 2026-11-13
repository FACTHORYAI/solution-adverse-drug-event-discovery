"""The most-mentioned drug and adverse-drug-event names."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.jobs._duck import align, run_query
from adverse_drug_event_discovery.schemas import MOST_COMMON

INPUTS = ("entities",)
OUTPUTS = ("most_common",)


@dataclass(frozen=True)
class Params:
    """Parameters for the most-common-entities job."""

    entity_type: str = ""
    min_confidence: float = 0.6
    limit: int = 30


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the most-mentioned names, optionally for one entity type only."""
    if params.entity_type not in ("", "ADE", "DRUG"):
        message = (
            f"Parameter entity_type is {params.entity_type!r}; "
            "most_common_entities needs '', 'ADE' or 'DRUG'"
        )
        raise ValueError(message)
    if not 0 <= params.min_confidence <= 1:
        message = f"Parameter min_confidence is {params.min_confidence}; it must be between 0 and 1"
        raise ValueError(message)
    if params.limit < 1:
        message = f"Parameter limit is {params.limit}; it must be at least 1"
        raise ValueError(message)
    table = run_query(
        io.read_sql("most_common_entities"),
        inputs,
        {
            "entity_type": params.entity_type,
            "min_confidence": params.min_confidence,
            "limit": params.limit,
        },
    )
    return {"most_common": align(table, MOST_COMMON)}
