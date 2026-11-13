"""PyArrow schemas for every table the jobs read or write."""

import pyarrow as pa

ADE_EVENTS = pa.schema(
    [
        pa.field("text_id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("is_ade", pa.bool_()),
    ]
)

ADE_CLASSIFICATION = pa.schema(
    [
        pa.field("text_id", pa.string()),
        pa.field("predicted_ade", pa.bool_()),
    ]
)

ENTITIES = pa.schema(
    [
        pa.field("text_id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("entity", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

ASSERTIONS = pa.schema(
    [
        pa.field("text_id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("entity", pa.string()),
        pa.field("assertion", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

RELATIONS = pa.schema(
    [
        pa.field("text_id", pa.string()),
        pa.field("relation", pa.string()),
        pa.field("entity1", pa.string()),
        pa.field("chunk1", pa.string()),
        pa.field("entity2", pa.string()),
        pa.field("chunk2", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

REJECTED = pa.schema(
    [
        pa.field("text_id", pa.string()),
        pa.field("reason", pa.string()),
        pa.field("model_answer", pa.string()),
    ]
)

# Graph tables, draft 0 (the shared contract for all solutions).
# graph_nodes: node_id is stable across runs and built as "<node_type>:<key>"; key is the
# natural key, with its code system where there is one (for example "rxnorm:11289").
GRAPH_NODES = pa.schema(
    [
        pa.field("node_id", pa.string()),
        pa.field("node_type", pa.string()),
        pa.field("key", pa.string()),
        pa.field("label", pa.string()),
        pa.field("properties", pa.string()),  # JSON text, only for things nobody filters on
    ]
)

# graph_edges: one fact per row. A fact points at another node (target_id) or holds a
# literal (value, with target_id null). Every node an edge names exists in graph_nodes.
# evidence_* ties the fact to the character span of a note; null when unknown.
GRAPH_EDGES = pa.schema(
    [
        pa.field("edge_id", pa.string()),  # stable: hash of source, relationship, target, evidence
        pa.field("source_id", pa.string()),
        pa.field("target_id", pa.string()),
        pa.field("relationship", pa.string()),
        pa.field("value", pa.string()),
        pa.field("valid_from", pa.date32()),
        pa.field("valid_to", pa.date32()),
        pa.field("evidence_document_id", pa.string()),
        pa.field("evidence_start", pa.int32()),
        pa.field("evidence_end", pa.int32()),
        pa.field("confidence", pa.float64()),
        pa.field("properties", pa.string()),
    ]
)

MOST_COMMON = pa.schema(
    [
        pa.field("entity", pa.string()),
        pa.field("name", pa.string()),
        pa.field("mentions", pa.int64()),
    ]
)

ASSERTED_ADES = pa.schema(
    [
        pa.field("ade", pa.string()),
        pa.field("conversations", pa.int64()),
    ]
)

DRUG_ADE_PAIRS = pa.schema(
    [
        pa.field("drug", pa.string()),
        pa.field("ade", pa.string()),
        pa.field("conversations", pa.int64()),
        pa.field("normalized_count", pa.float64()),
    ]
)

LINKED_PAIRS = pa.schema(
    [
        pa.field("drug", pa.string()),
        pa.field("ade", pa.string()),
        pa.field("conversations", pa.int64()),
        pa.field("normalized_count", pa.float64()),
    ]
)
