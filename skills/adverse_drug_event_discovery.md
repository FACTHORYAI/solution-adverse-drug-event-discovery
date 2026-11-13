# Adverse Drug Event Discovery — agent instructions

You help members find and analyse adverse drug events (ADEs) in conversational texts: patient support calls, forum posts, sales conversations.

## What the project provides

- Sample tables in `data/sample` (synthetic): `ade_events` (texts with their ADE label), the extraction outputs `ade_classification`, `entities`, `assertions` and `relations`, and `graph_nodes` / `graph_edges` (the knowledge graph as tables). Every row names its text in `text_id`. All synthetic.
- Jobs under `src/adverse_drug_event_discovery/jobs`: four extraction jobs that read texts through a `TextModel` (`text/interface.py`) — classification, entities, assertions, relations — one job that turns the extracted rows into graph node and edge tables, and four analysis jobs over the extracted tables.

## How to answer an ADE question

1. Classify what the member asks: whether a text reports an ADE (`classify_ade`), which drugs and ADEs are mentioned (`extract_entities`), whether an ADE is actually experienced (`extract_assertions`), which ADE follows which drug (`extract_relations` or `linked_drug_ade_pairs`), what is most talked about (`most_common_entities`, `asserted_ade_frequency`), which drugs and ADEs go together (`drug_ade_pairs`), or the graph of drugs and ADEs (`build_knowledge_graph`).
2. Check the parameters with `uv run python -m adverse_drug_event_discovery <job> --help`; `min_confidence` keeps confident mentions, `limit` trims result tables, `min_conversations` drops one-off pairs.
3. Run the job, or answer directly from the tables: `entities` holds ADE and DRUG mentions with confidence; `assertions` holds the status per ADE mention (Present, Absent, Possible, Hypothetical, Conditional, Someone_else); `relations` holds the ADE-DRUG pairs (relation "1" when the text ties them together, "0" when not). `graph_nodes` holds one row per `Drug` or `ADE` node (`node_id`, `node_type`, `key`, `label`); `graph_edges` holds one fact per row: `Drug -HAS_ADVERSE_EVENT-> ADE` for each linked pair, and `ADE -ASSERTION-> status` (the status in `value`) for each assertion. Join edges to nodes on `source_id` / `target_id`; filter with SQL.
4. Every edge names the text it came from (`evidence_document_id`, a `text_id` of `ade_events`) and, when found, the character span (`evidence_start`, `evidence_end`) in that text. Drug and ADE nodes are shared by all texts, so this is how you tell which text a fact belongs to. A linked pair is not a confirmed reaction: read the `ASSERTION` fact for the same ADE and text to see whether it was experienced. Quote that evidence when you explain a result.
5. Report results as a table with the counts behind them (`mentions`, `conversations`, `normalized_count`). Never guess beyond the tables; say which rows come from which job.

## Data care

- The sample data is synthetic and openly licensed; real conversations and patient data never enter this project.
- The four extraction jobs need a model behind `text.interface`; the repository ships a recorded stand-in for tests and demos. The `ade_classification` predictions in the sample are invented, so do not read their accuracy as a measure of a classifier.
- Results are for research and pharmacovigilance analytics, not clinical decisions. Say so when a result could be read as medical advice, and remember that co-occurrence is not causation and that no disproportionality statistics are included: `drug_ade_pairs` counts texts that mention a drug and an ADE together, `linked_drug_ade_pairs` counts linked pairs, and `normalized_count` only scales a count within its ADE.
- `asserted_ade_frequency` leaves out only the Absent mentions; Possible, Hypothetical, Conditional and Someone_else count too.
