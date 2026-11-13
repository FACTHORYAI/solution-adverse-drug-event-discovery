# Adverse Drug Event Discovery

Find adverse drug events and the drugs they follow in conversational text.

## Start here

1. Look at the sample tables in `data/sample` (synthetic): `ade_events` holds conversational texts with their ADE label, and `ade_classification`, `entities`, `assertions`, `relations` hold what the extraction jobs produce.
2. Read `entities`: every row is one ADE or DRUG mention with its confidence; `assertions` says whether each ADE mention is Present, Absent, Possible, Hypothetical, Conditional or Someone_else; `relations` links ADE-DRUG pairs (relation "1").
3. Ask an analysis question and run its job:

| Question | Job |
| --- | --- |
| Which drugs and ADEs are mentioned most? | `most_common_entities` |
| Which ADEs are actually experienced most often? | `asserted_ade_frequency` |
| Which drug and ADE are talked about together? | `drug_ade_pairs` |
| Which drug-ADE pairs are directly linked? | `linked_drug_ade_pairs` |
| Does this text report an ADE? | `classify_ade` |

Named measures for the classifier and the assertion statuses live in `metrics/`.

## Notes

- The sample data is synthetic; real conversations never enter this project.
- The four extraction jobs need a text model behind `adverse_drug_event_discovery.text.interface`; a recorded stand-in exists for tests and demos. The analysis jobs run without any model.
- Co-occurrence is not causation: `drug_ade_pairs` counts mentions together, `linked_drug_ade_pairs` counts linked pairs.
- Results are for research and pharmacovigilance analytics, not clinical decisions.
