"""The ADEs mentioned in the most texts with an assertion other than Absent."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.jobs._duck import align, run_query
from adverse_drug_event_discovery.schemas import ASSERTED_ADES

INPUTS = ("assertions",)
OUTPUTS = ("asserted_ades",)


@dataclass(frozen=True)
class Params:
    """Parameters for the asserted-ADE job."""

    limit: int = 20


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the ADEs mentioned in the most texts, leaving out the Absent mentions."""
    if params.limit < 1:
        message = f"Parameter limit is {params.limit}; it must be at least 1"
        raise ValueError(message)
    table = run_query(
        io.read_sql("asserted_ade_frequency"),
        inputs,
        {"limit": params.limit},
    )
    return {"asserted_ades": align(table, ASSERTED_ADES)}
