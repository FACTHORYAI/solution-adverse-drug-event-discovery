"""PyArrow schemas for every table the jobs read or write."""

import pyarrow as pa

ADE_EVENTS = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("is_ade", pa.bool_()),
    ]
)

ADE_CLASSIFICATION = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("predicted_ade", pa.bool_()),
    ]
)

ENTITIES = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("entity", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

ASSERTIONS = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("entity", pa.string()),
        pa.field("assertion", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

RELATIONS = pa.schema(
    [
        pa.field("id", pa.string()),
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
        pa.field("id", pa.string()),
        pa.field("reason", pa.string()),
        pa.field("model_answer", pa.string()),
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
