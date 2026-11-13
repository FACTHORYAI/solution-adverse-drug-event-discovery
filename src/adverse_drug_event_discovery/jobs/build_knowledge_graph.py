"""Build the adverse-drug-event knowledge graph as node and edge tables."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from adverse_drug_event_discovery import io
from adverse_drug_event_discovery.jobs._duck import align, run_query
from adverse_drug_event_discovery.schemas import GRAPH_EDGES, GRAPH_NODES

INPUTS = ("ade_events", "entities", "assertions", "relations")
OUTPUTS = ("graph_nodes", "graph_edges")


@dataclass(frozen=True)
class Params:
    """Parameters for the knowledge-graph build."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return graph_nodes and graph_edges built from texts, entities, assertions and relations."""
    nodes = align(run_query(io.read_sql("build_graph_nodes"), inputs), GRAPH_NODES)
    edges = align(run_query(io.read_sql("build_graph_edges"), inputs), GRAPH_EDGES)
    return {"graph_nodes": nodes, "graph_edges": edges}
