# Adverse Drug Event Discovery

Find adverse drug events and the drugs they follow in conversational text.

## Start here

1. Look at the sample tables in `data/sample` (synthetic): `ade_events` holds conversational texts (`text_id`, `text`) with their ADE label, and `ade_classification`, `entities`, `assertions`, `relations` hold what the extraction jobs produce, each row with the `text_id` of its text. `graph_nodes` and `graph_edges` are the graph built from them.
2. Read `entities`: every row is one ADE or DRUG mention with its confidence; `assertions` says whether each ADE mention is Present, Absent, Possible, Hypothetical, Conditional or Someone_else; `relations` links ADE-DRUG pairs (relation "1" when the text ties them together).
3. Read `graph_nodes` and `graph_edges`: every edge is one fact — `Drug -> ADE` (`HAS_ADVERSE_EVENT`) for a linked pair, or `ADE -> status` (`ASSERTION`) for an assertion. Each fact names the text it came from and the text span.
4. Ask an analysis question and run its job:

| Question | Job |
| --- | --- |
| Which drugs and ADEs are mentioned most? | `most_common_entities` |
| Which ADEs are mentioned most, leaving out those the text denies? | `asserted_ade_frequency` |
| Which drug and ADE are talked about together? | `drug_ade_pairs` |
| Which drug-ADE pairs are directly linked? | `linked_drug_ade_pairs` |
| Does this text report an ADE? | `classify_ade` |
| Show me the drugs and ADEs as a graph | `build_knowledge_graph` |

Named measures for the classifier, the assertion statuses and the graph's linked pairs live in `metrics/`.

## Notes

- The sample data is synthetic; real conversations never enter this project.
- The four extraction jobs need a text model behind `adverse_drug_event_discovery.text.interface`; a recorded stand-in exists for tests and demos. The graph and analysis jobs run without any model.
- Co-occurrence is not causation, and no disproportionality statistics are included: `drug_ade_pairs` counts texts that mention a drug and an ADE together, `linked_drug_ade_pairs` counts linked pairs.
- The predicted flags in `ade_classification` are invented to exercise the metrics.
- Results are for research and pharmacovigilance analytics, not clinical decisions.
