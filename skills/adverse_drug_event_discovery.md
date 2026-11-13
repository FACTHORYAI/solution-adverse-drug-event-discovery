# Adverse Drug Event Discovery — agent instructions

You help members find and analyse adverse drug events (ADEs) in conversational texts: patient support calls, forum posts, sales conversations.

## What the project provides

- Sample tables in `data/sample` (synthetic): `ade_events` (texts with their ADE label), and the extraction outputs `ade_classification`, `entities`, `assertions` and `relations`.
- Jobs under `src/adverse_drug_event_discovery/jobs`: four extraction jobs that read texts through a `TextModel` (`text/interface.py`) — classification, entities, assertions, relations — and four analysis jobs over the extracted tables.

## How to answer an ADE question

1. Classify what the member asks: whether a text reports an ADE (`classify_ade`), which drugs and ADEs are mentioned (`extract_entities`), whether an ADE is actually experienced (`extract_assertions`), which ADE follows which drug (`extract_relations` or `linked_drug_ade_pairs`), what is most talked about (`most_common_entities`, `asserted_ade_frequency`), or which drugs and ADEs go together (`drug_ade_pairs`).
2. Check the parameters with `uv run python -m adverse_drug_event_discovery <job> --help`; `min_confidence` keeps confident mentions, `limit` trims result tables, `min_conversations` drops one-off pairs.
3. Run the job, or answer directly from the tables: `entities` holds ADE and DRUG mentions with confidence; `assertions` holds the status per ADE mention (Present, Absent, Possible, Hypothetical, Conditional, Someone_else); `relations` holds the linked ADE-DRUG pairs (relation "1").
4. Report results as a table with the counts behind them (`mentions`, `conversations`, `normalized_count`). Never guess beyond the tables; say which rows come from which job.

## Data care

- The sample data is synthetic and openly licensed; real conversations and patient data never enter this project.
- The four extraction jobs need a model behind `text.interface`; the repository ships a recorded stand-in for tests and demos.
- Results are for research and pharmacovigilance analytics, not clinical decisions. Say so when a result could be read as medical advice, and remember that co-occurrence is not causation: `drug_ade_pairs` counts mentions together, `linked_drug_ade_pairs` counts linked pairs.
