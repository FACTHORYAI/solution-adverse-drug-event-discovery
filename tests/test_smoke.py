"""One smoke test per job, on the synthetic sample data."""

from __future__ import annotations

from pathlib import Path

import pytest

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.config import Settings
from adverse_drug_event_discovery.jobs import REGISTRY, call_run
from adverse_drug_event_discovery.jobs.asserted_ade_frequency import Params as AssertedParams
from adverse_drug_event_discovery.jobs.classify_ade import Params as ClassifyParams
from adverse_drug_event_discovery.jobs.drug_ade_pairs import Params as PairParams
from adverse_drug_event_discovery.jobs.extract_assertions import Params as AssertionsParams
from adverse_drug_event_discovery.jobs.extract_entities import Params as EntitiesParams
from adverse_drug_event_discovery.jobs.extract_relations import Params as RelationsParams
from adverse_drug_event_discovery.jobs.linked_drug_ade_pairs import Params as LinkedParams
from adverse_drug_event_discovery.jobs.most_common_entities import Params as CommonParams
from adverse_drug_event_discovery.schemas import (
    ADE_CLASSIFICATION,
    ASSERTED_ADES,
    ASSERTIONS,
    DRUG_ADE_PAIRS,
    ENTITIES,
    LINKED_PAIRS,
    MOST_COMMON,
    RELATIONS,
)
from adverse_drug_event_discovery.text.recorded import RecordedTextModel, load_answers

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings(sample_dir=REPO / "data" / "sample", output_dir=REPO / "output")


@pytest.fixture(scope="module")
def recorded_model() -> RecordedTextModel:
    return RecordedTextModel(load_answers(io.read_json(REPO / "tests" / "recorded_answers.json")))


@pytest.fixture(scope="module")
def tables() -> dict[str, object]:
    return {
        name: io.read_table(name, SETTINGS)
        for name in ("ade_events", "ade_classification", "entities", "assertions", "relations")
    }


def run_job(name: str, tables: dict, params, model=None):
    return call_run(REGISTRY[name], tables, params, model)


def as_pairs(table) -> set[tuple]:
    return {tuple(row.values()) for row in table.to_pylist()}


def test_classify_ade(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "classify_ade", {"ade_events": tables["ade_events"]}, ClassifyParams(), recorded_model
    )
    classification = outputs["ade_classification"]
    assert classification.schema.equals(ADE_CLASSIFICATION)
    assert classification.equals(tables["ade_classification"].select(ADE_CLASSIFICATION.names))
    assert outputs["rejected_classifications"].num_rows == 0


def test_extract_entities(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_entities", {"ade_events": tables["ade_events"]}, EntitiesParams(), recorded_model
    )
    entities = outputs["entities"]
    assert entities.schema.equals(ENTITIES)
    assert entities.equals(tables["entities"].select(ENTITIES.names))
    assert entities.num_rows == 23
    assert outputs["rejected_entities"].num_rows == 0


def test_extract_assertions(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_assertions",
        {"ade_events": tables["ade_events"]},
        AssertionsParams(),
        recorded_model,
    )
    assertions = outputs["assertions"]
    assert assertions.schema.equals(ASSERTIONS)
    assert assertions.equals(tables["assertions"].select(ASSERTIONS.names))
    assert assertions.num_rows == 11
    assert outputs["rejected_assertions"].num_rows == 0


def test_extract_relations(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_relations", {"ade_events": tables["ade_events"]}, RelationsParams(), recorded_model
    )
    relations = outputs["relations"]
    assert relations.schema.equals(RELATIONS)
    assert relations.equals(tables["relations"].select(RELATIONS.names))
    assert relations.num_rows == 10
    assert outputs["rejected_relations"].num_rows == 0


def test_most_common_entities(tables: dict) -> None:
    common = run_job("most_common_entities", {"entities": tables["entities"]}, CommonParams())[
        "most_common"
    ]
    assert common.schema.equals(MOST_COMMON)
    rows = {(row["entity"], row["name"]): row["mentions"] for row in common.to_pylist()}
    assert rows[("ADE", "nausea")] == 3
    assert rows[("ADE", "thrombocytopenia")] == 2
    assert rows[("DRUG", "heparin")] == 2
    assert rows[("DRUG", "morphine")] == 2
    assert rows[("DRUG", "insulin")] == 1

    drugs = run_job(
        "most_common_entities",
        {"entities": tables["entities"]},
        CommonParams(entity_type="DRUG"),
    )["most_common"]
    assert {row["entity"] for row in drugs.to_pylist()} == {"DRUG"}


def test_asserted_ade_frequency(tables: dict) -> None:
    asserted = run_job(
        "asserted_ade_frequency", {"assertions": tables["assertions"]}, AssertedParams()
    )["asserted_ades"]
    assert asserted.schema.equals(ASSERTED_ADES)
    rows = {row["ade"]: row["conversations"] for row in asserted.to_pylist()}
    assert rows["nausea"] == 3
    assert rows["thrombocytopenia"] == 1
    assert "thrombocytopenia" in rows


def test_drug_ade_pairs(tables: dict) -> None:
    pairs = run_job("drug_ade_pairs", {"entities": tables["entities"]}, PairParams())[
        "drug_ade_pairs"
    ]
    assert pairs.schema.equals(DRUG_ADE_PAIRS)
    rows = {(row["drug"], row["ade"]): row for row in pairs.to_pylist()}
    assert len(rows) == 9
    assert rows[("heparin", "thrombocytopenia")]["conversations"] == 2
    assert rows[("morphine", "nausea")]["conversations"] == 2
    assert rows[("morphine", "nausea")]["normalized_count"] == 1.0
    assert rows[("metformin", "nausea")]["normalized_count"] == 0.0

    frequent = run_job(
        "drug_ade_pairs", {"entities": tables["entities"]}, PairParams(min_conversations=2)
    )["drug_ade_pairs"]
    assert {(row["drug"], row["ade"]) for row in frequent.to_pylist()} == {
        ("heparin", "thrombocytopenia"),
        ("morphine", "nausea"),
    }


def test_linked_drug_ade_pairs(tables: dict) -> None:
    linked = run_job("linked_drug_ade_pairs", {"relations": tables["relations"]}, LinkedParams())[
        "linked_pairs"
    ]
    assert linked.schema.equals(LINKED_PAIRS)
    rows = {(row["drug"], row["ade"]): row for row in linked.to_pylist()}
    assert len(rows) == 9
    assert rows[("heparin", "thrombocytopenia")]["conversations"] == 1
    assert rows[("morphine", "nausea")]["conversations"] == 2
    assert rows[("morphine", "nausea")]["normalized_count"] == 1.0
