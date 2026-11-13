"""One smoke test per job, on the synthetic sample data."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import pyarrow as pa
import pytest

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.config import Settings
from adverse_drug_event_discovery.jobs import REGISTRY, call_run
from adverse_drug_event_discovery.jobs.asserted_ade_frequency import Params as AssertedParams
from adverse_drug_event_discovery.jobs.build_knowledge_graph import Params as GraphParams
from adverse_drug_event_discovery.jobs.classify_ade import Params as ClassifyParams
from adverse_drug_event_discovery.jobs.drug_ade_pairs import Params as PairParams
from adverse_drug_event_discovery.jobs.extract_assertions import Params as AssertionsParams
from adverse_drug_event_discovery.jobs.extract_entities import Params as EntitiesParams
from adverse_drug_event_discovery.jobs.extract_relations import Params as RelationsParams
from adverse_drug_event_discovery.jobs.linked_drug_ade_pairs import Params as LinkedParams
from adverse_drug_event_discovery.jobs.most_common_entities import Params as CommonParams
from adverse_drug_event_discovery.schemas import (
    ADE_CLASSIFICATION,
    ADE_EVENTS,
    ASSERTED_ADES,
    ASSERTIONS,
    DRUG_ADE_PAIRS,
    ENTITIES,
    GRAPH_EDGES,
    GRAPH_NODES,
    LINKED_PAIRS,
    MOST_COMMON,
    RELATIONS,
)
from adverse_drug_event_discovery.text.parse import ASSERTION_STATUSES
from adverse_drug_event_discovery.text.recorded import RecordedTextModel, load_answers

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings(sample_dir=REPO / "data" / "sample", output_dir=REPO / "output")
TABLE_NAMES = (
    "ade_events",
    "ade_classification",
    "entities",
    "assertions",
    "relations",
    "graph_nodes",
    "graph_edges",
)


@pytest.fixture(scope="module")
def recorded_model() -> RecordedTextModel:
    return RecordedTextModel(load_answers(io.read_json(REPO / "tests" / "recorded_answers.json")))


@pytest.fixture(scope="module")
def tables() -> dict[str, pa.Table]:
    return {name: io.read_table(name, SETTINGS) for name in TABLE_NAMES}


def run_job(name: str, tables: dict, params, model=None):
    return call_run(REGISTRY[name], tables, params, model)


def rows(tables: dict, name: str) -> list[dict]:
    return tables[name].to_pylist()


def test_sample_is_a_mix_of_texts(tables: dict) -> None:
    events = rows(tables, "ade_events")
    assert len(events) == 300
    assert len({row["text_id"] for row in events}) == len(events)
    assert len({row["text"] for row in events}) == len(events)
    assert {row["is_ade"] for row in events} == {True, False}
    assert {row["assertion"] for row in rows(tables, "assertions")} == set(ASSERTION_STATUSES)


def test_recorded_answers_match_the_prompts(tables: dict) -> None:
    answers = io.read_json(REPO / "tests" / "recorded_answers.json")
    tasks = {
        io.read_prompt(spec.name).splitlines()[0].removeprefix("task:").strip()
        for spec in REGISTRY.values()
        if spec.needs_model
    }
    assert set(answers) == tasks
    texts = {row["text"] for row in rows(tables, "ade_events")}
    assert all(set(task_answers) == texts for task_answers in answers.values())


# The extraction jobs return exactly the sample tables, because the sample is written from the
# same templates as the texts.


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
    assert outputs["rejected_assertions"].num_rows == 0


def test_extract_relations(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_relations", {"ade_events": tables["ade_events"]}, RelationsParams(), recorded_model
    )
    relations = outputs["relations"]
    assert relations.schema.equals(RELATIONS)
    assert relations.equals(tables["relations"].select(RELATIONS.names))
    assert outputs["rejected_relations"].num_rows == 0


def test_build_knowledge_graph(tables: dict) -> None:
    inputs = {name: tables[name] for name in ("ade_events", "entities", "assertions", "relations")}
    outputs = run_job("build_knowledge_graph", inputs, GraphParams())
    assert outputs["graph_nodes"].schema.equals(GRAPH_NODES)
    assert outputs["graph_edges"].schema.equals(GRAPH_EDGES)
    assert outputs["graph_nodes"].equals(tables["graph_nodes"].select(GRAPH_NODES.names))
    assert outputs["graph_edges"].equals(tables["graph_edges"].select(GRAPH_EDGES.names))


def test_graph_tables_follow_the_contract(tables: dict) -> None:
    nodes = rows(tables, "graph_nodes")
    edges = rows(tables, "graph_edges")
    texts = {row["text_id"]: row["text"] for row in rows(tables, "ade_events")}
    node_ids = {node["node_id"] for node in nodes}
    assert len(node_ids) == len(nodes)
    assert all(node["node_id"] == f"{node['node_type']}:{node['key']}" for node in nodes)
    assert {node["node_type"] for node in nodes} == {"Drug", "ADE"}
    assert len({edge["edge_id"] for edge in edges}) == len(edges)
    assert {edge["relationship"] for edge in edges} == {"HAS_ADVERSE_EVENT", "ASSERTION"}
    for edge in edges:
        assert edge["source_id"] in node_ids
        # A fact points at a node or holds a literal value, never both.
        assert (edge["target_id"] in node_ids) != (edge["value"] is not None)
        assert edge["evidence_document_id"] in texts
        assert edge["valid_from"] is None
        assert edge["valid_to"] is None
        if edge["relationship"] == "HAS_ADVERSE_EVENT":
            assert edge["source_id"].startswith("Drug:")
            assert edge["target_id"].startswith("ADE:")
            ade_id = edge["target_id"]
        else:
            assert edge["value"] in ASSERTION_STATUSES
            ade_id = edge["source_id"]
        # The evidence span is the ADE text as written in the text it came from.
        assert edge["evidence_start"] is not None
        span = texts[edge["evidence_document_id"]][edge["evidence_start"] : edge["evidence_end"]]
        assert span.lower() == ade_id.removeprefix("ADE:")


def test_graph_edges_match_the_linked_and_asserted_rows(tables: dict) -> None:
    texts = {row["text_id"]: row["text"] for row in rows(tables, "ade_events")}

    def span(text_id: str, chunk: str) -> tuple[int, int]:
        start = texts[text_id].find(chunk)
        return start, start + len(chunk)

    expected = {
        (
            f"Drug:{r['chunk2'].strip().lower()}",
            f"ADE:{r['chunk1'].strip().lower()}",
            "HAS_ADVERSE_EVENT",
            None,
            r["text_id"],
            *span(r["text_id"], r["chunk1"]),
        )
        for r in rows(tables, "relations")
        if r["relation"] == "1"
    } | {
        (
            f"ADE:{r['chunk'].strip().lower()}",
            None,
            "ASSERTION",
            r["assertion"],
            r["text_id"],
            *span(r["text_id"], r["chunk"]),
        )
        for r in rows(tables, "assertions")
    }
    actual = {
        (
            e["source_id"],
            e["target_id"],
            e["relationship"],
            e["value"],
            e["evidence_document_id"],
            e["evidence_start"],
            e["evidence_end"],
        )
        for e in rows(tables, "graph_edges")
    }
    assert actual == expected
    assert len(rows(tables, "graph_edges")) == len(expected)
    # Linked pairs of the text and its ADE assertions are both in the graph.
    assert any(edge[2] == "HAS_ADVERSE_EVENT" for edge in actual)
    assert any(edge[2] == "ASSERTION" for edge in actual)


def test_graph_edges_without_found_text_have_no_span_and_repeats_are_merged() -> None:
    events = [
        {"text_id": "a", "text": "Rash after aspirin.", "is_ade": True},
        {"text_id": "b", "text": "I felt fine.", "is_ade": False},
    ]
    entities = [
        {"text_id": "a", "chunk": "aspirin", "entity": "DRUG", "confidence": 0.9},
        {"text_id": "a", "chunk": "Rash", "entity": "ADE", "confidence": 0.9},
    ]
    assertions = [
        {
            "text_id": "a",
            "chunk": "Rash",
            "entity": "ADE",
            "assertion": "Present",
            "confidence": 0.9,
        },
        {
            "text_id": "b",
            "chunk": "nausea",
            "entity": "ADE",
            "assertion": "Absent",
            "confidence": 0.8,
        },
    ]
    pair = {"relation": "1", "entity1": "ADE", "entity2": "DRUG"}
    relations = [
        {"text_id": "a", "chunk1": "Rash", "chunk2": "aspirin", "confidence": 0.7, **pair},
        {"text_id": "a", "chunk1": "Rash", "chunk2": "aspirin", "confidence": 0.9, **pair},
        {"text_id": "b", "chunk1": "nausea", "chunk2": "aspirin", "confidence": 0.6, **pair},
    ]
    inputs = {
        "ade_events": pa.Table.from_pylist(events, schema=ADE_EVENTS),
        "entities": pa.Table.from_pylist(entities, schema=ENTITIES),
        "assertions": pa.Table.from_pylist(assertions, schema=ASSERTIONS),
        "relations": pa.Table.from_pylist(relations, schema=RELATIONS),
    }
    outputs = run_job("build_knowledge_graph", inputs, GraphParams())
    nodes = {row["node_id"]: row["label"] for row in outputs["graph_nodes"].to_pylist()}
    assert nodes == {
        "ADE:nausea": "nausea",
        "ADE:rash": "Rash",
        "Drug:aspirin": "aspirin",
    }
    edges = {
        (e["source_id"], e["relationship"], e["evidence_document_id"]): e
        for e in outputs["graph_edges"].to_pylist()
    }
    assert len(edges) == outputs["graph_edges"].num_rows == 4
    found = edges[("Drug:aspirin", "HAS_ADVERSE_EVENT", "a")]
    assert (found["evidence_start"], found["evidence_end"], found["confidence"]) == (0, 4, 0.9)
    missing = edges[("Drug:aspirin", "HAS_ADVERSE_EVENT", "b")]
    assert (missing["evidence_start"], missing["evidence_end"]) == (None, None)
    assert missing["target_id"] == "ADE:nausea"
    absent = edges[("ADE:nausea", "ASSERTION", "b")]
    assert (absent["evidence_start"], absent["evidence_end"], absent["value"]) == (
        None,
        None,
        "Absent",
    )


# The analysis tests compare each job with a plain-Python reference over the extracted rows.


def expected_pairs(
    pairs: set[tuple[str, str, str]], min_conversations: int
) -> dict[tuple[str, str], tuple[int, float]]:
    """Count the texts per (drug, ADE) and scale each count within its ADE (min-max)."""
    counts = Counter((drug, ade) for _text, drug, ade in pairs)
    counts = Counter({pair: n for pair, n in counts.items() if n >= min_conversations})
    by_ade: dict[str, list[int]] = defaultdict(list)
    for (_drug, ade), n in counts.items():
        by_ade[ade].append(n)
    result = {}
    for (drug, ade), n in counts.items():
        low, high = min(by_ade[ade]), max(by_ade[ade])
        result[(drug, ade)] = (n, 0.0 if high == low else (n - low) / (high - low))
    return result


def assert_pairs(table: pa.Table, expected: dict[tuple[str, str], tuple[int, float]]) -> None:
    actual = {
        (row["drug"], row["ade"]): (row["conversations"], row["normalized_count"])
        for row in table.to_pylist()
    }
    assert actual.keys() == expected.keys()
    for pair, (conversations, normalized) in expected.items():
        assert actual[pair][0] == conversations
        assert actual[pair][1] == pytest.approx(normalized)


def test_most_common_entities(tables: dict) -> None:
    counts = Counter(
        (row["entity"], row["chunk"].lower())
        for row in rows(tables, "entities")
        if row["confidence"] >= 0.6 and row["chunk"]
    )
    expected = sorted(counts.items(), key=lambda item: (-item[1], item[0][1]))[:30]
    common = run_job("most_common_entities", {"entities": tables["entities"]}, CommonParams())[
        "most_common"
    ]
    assert common.schema.equals(MOST_COMMON)
    assert [
        ((row["entity"], row["name"]), row["mentions"]) for row in common.to_pylist()
    ] == expected
    assert common.num_rows == 30

    drugs = run_job(
        "most_common_entities",
        {"entities": tables["entities"]},
        CommonParams(entity_type="DRUG", limit=100),
    )["most_common"]
    expected_drugs = {name: n for (entity, name), n in counts.items() if entity == "DRUG"}
    assert expected_drugs
    assert {row["name"]: row["mentions"] for row in drugs.to_pylist()} == expected_drugs
    assert {row["entity"] for row in drugs.to_pylist()} == {"DRUG"}


def test_asserted_ade_frequency(tables: dict) -> None:
    texts: dict[str, set[str]] = defaultdict(set)
    for row in rows(tables, "assertions"):
        if row["assertion"] not in ("", "Absent") and row["chunk"]:
            texts[row["chunk"].lower()].add(row["text_id"])
    expected = sorted(((ade, len(ids)) for ade, ids in texts.items()), key=lambda i: (-i[1], i[0]))
    asserted = run_job(
        "asserted_ade_frequency", {"assertions": tables["assertions"]}, AssertedParams()
    )["asserted_ades"]
    assert asserted.schema.equals(ASSERTED_ADES)
    assert expected
    assert [(row["ade"], row["conversations"]) for row in asserted.to_pylist()] == expected[:20]


def test_drug_ade_pairs(tables: dict) -> None:
    drugs: dict[str, set[str]] = defaultdict(set)
    ades: dict[str, set[str]] = defaultdict(set)
    for row in rows(tables, "entities"):
        if row["confidence"] >= 0.6 and row["chunk"]:
            if row["entity"] == "DRUG":
                drugs[row["text_id"]].add(row["chunk"].lower())
            else:
                ades[row["text_id"]].add(row["chunk"])
    pairs = {(t, d, a) for t in drugs for d in drugs[t] for a in ades.get(t, ())}
    inputs = {"entities": tables["entities"]}
    result = run_job("drug_ade_pairs", inputs, PairParams())["drug_ade_pairs"]
    assert result.schema.equals(DRUG_ADE_PAIRS)
    expected = expected_pairs(pairs, 1)
    assert expected
    assert_pairs(result, expected)

    frequent = run_job("drug_ade_pairs", inputs, PairParams(min_conversations=3))["drug_ade_pairs"]
    expected_frequent = expected_pairs(pairs, 3)
    assert expected_frequent
    assert len(expected_frequent) < len(expected)
    assert_pairs(frequent, expected_frequent)


def test_linked_drug_ade_pairs(tables: dict) -> None:
    pairs = {
        (row["text_id"], row["chunk2"].lower(), row["chunk1"])
        for row in rows(tables, "relations")
        if row["relation"] == "1" and row["confidence"] >= 0.6
    }
    inputs = {"relations": tables["relations"]}
    linked = run_job("linked_drug_ade_pairs", inputs, LinkedParams())["linked_pairs"]
    assert linked.schema.equals(LINKED_PAIRS)
    expected = expected_pairs(pairs, 1)
    assert expected
    assert_pairs(linked, expected)

    frequent = run_job("linked_drug_ade_pairs", inputs, LinkedParams(min_conversations=3))[
        "linked_pairs"
    ]
    expected_frequent = expected_pairs(pairs, 3)
    assert expected_frequent
    assert_pairs(frequent, expected_frequent)


def test_metrics_run_on_the_sample(tables: dict) -> None:
    connection = duckdb.connect()
    for name in ("ade_events", "ade_classification", "assertions", "graph_edges"):
        connection.register(name, tables[name])

    def query(metric: str) -> list[tuple]:
        return connection.sql((REPO / "metrics" / f"{metric}.sql").read_text("utf-8")).fetchall()

    labels = {row["text_id"]: row["is_ade"] for row in rows(tables, "ade_events")}
    predicted = {row["text_id"]: row["predicted_ade"] for row in rows(tables, "ade_classification")}
    matches = sum(labels[text_id] == flag for text_id, flag in predicted.items())
    assert query("classifier_accuracy")[0][0] == pytest.approx(matches / len(predicted))
    assert 0 < matches < len(predicted)
    confusion = Counter((labels[text_id], flag) for text_id, flag in predicted.items())
    assert {(a, p): n for a, p, n in query("confusion_matrix")} == dict(confusion)
    statuses = Counter(row["assertion"] for row in rows(tables, "assertions"))
    assert dict(query("assertion_breakdown")) == dict(statuses)
    linked = {
        (row["source_id"], row["target_id"])
        for row in rows(tables, "graph_edges")
        if row["relationship"] == "HAS_ADVERSE_EVENT"
    }
    assert linked
    assert query("linked_pairs")[0][0] == len(linked)
