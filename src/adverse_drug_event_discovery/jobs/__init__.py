"""The jobs of this solution: plain functions from named tables to named tables."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pyarrow as pa

from adverse_drug_event_discovery.jobs import (
    asserted_ade_frequency,
    classify_ade,
    drug_ade_pairs,
    extract_assertions,
    extract_entities,
    extract_relations,
    linked_drug_ade_pairs,
    most_common_entities,
)


@dataclass(frozen=True)
class JobSpec:
    """One job: its callable, its parameter class and its input and output tables."""

    name: str
    description: str
    run: Callable[..., dict[str, pa.Table]]
    params_cls: type
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    needs_model: bool = False


REGISTRY: dict[str, JobSpec] = {
    spec.name: spec
    for spec in (
        JobSpec(
            name="classify_ade",
            description="Classify conversational texts as reporting an adverse drug event or not.",
            run=classify_ade.run,
            params_cls=classify_ade.Params,
            inputs=classify_ade.INPUTS,
            outputs=classify_ade.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="extract_entities",
            description="Extract the ADE and DRUG mentions from conversational texts.",
            run=extract_entities.run,
            params_cls=extract_entities.Params,
            inputs=extract_entities.INPUTS,
            outputs=extract_entities.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="extract_assertions",
            description="Judge whether each ADE mention is actually experienced.",
            run=extract_assertions.run,
            params_cls=extract_assertions.Params,
            inputs=extract_assertions.INPUTS,
            outputs=extract_assertions.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="extract_relations",
            description="Extract the ADE-DRUG pairs that belong together.",
            run=extract_relations.run,
            params_cls=extract_relations.Params,
            inputs=extract_relations.INPUTS,
            outputs=extract_relations.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="most_common_entities",
            description="The most-mentioned drug and ADE names.",
            run=most_common_entities.run,
            params_cls=most_common_entities.Params,
            inputs=most_common_entities.INPUTS,
            outputs=most_common_entities.OUTPUTS,
        ),
        JobSpec(
            name="asserted_ade_frequency",
            description="The ADEs most often reported as actually experienced.",
            run=asserted_ade_frequency.run,
            params_cls=asserted_ade_frequency.Params,
            inputs=asserted_ade_frequency.INPUTS,
            outputs=asserted_ade_frequency.OUTPUTS,
        ),
        JobSpec(
            name="drug_ade_pairs",
            description="Drug-ADE pairs by co-occurrence within the same conversation.",
            run=drug_ade_pairs.run,
            params_cls=drug_ade_pairs.Params,
            inputs=drug_ade_pairs.INPUTS,
            outputs=drug_ade_pairs.OUTPUTS,
        ),
        JobSpec(
            name="linked_drug_ade_pairs",
            description="Drug-ADE pairs the relation extraction linked.",
            run=linked_drug_ade_pairs.run,
            params_cls=linked_drug_ade_pairs.Params,
            inputs=linked_drug_ade_pairs.INPUTS,
            outputs=linked_drug_ade_pairs.OUTPUTS,
        ),
    )
}


def param_values(spec: JobSpec, args: Any) -> Any:
    """Build the job's Params instance from parsed command-line arguments."""
    values = {
        field.name: getattr(args, field.name)
        for field in spec.params_cls.__dataclass_fields__.values()
    }
    return spec.params_cls(**values)


def call_run(
    spec: JobSpec, inputs: dict[str, pa.Table], params: Any, model: Any
) -> dict[str, pa.Table]:
    """Call the job's run with the arguments its signature asks for."""
    if spec.needs_model:
        return spec.run(inputs=inputs, params=params, model=model)
    return spec.run(inputs=inputs, params=params)
