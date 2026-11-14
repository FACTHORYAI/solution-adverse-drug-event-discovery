<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FACTHORYAI/.github/main/brand/word-mark-only-mono.svg">
    <img alt="Facthory" src="https://raw.githubusercontent.com/FACTHORYAI/.github/main/brand/word-mark-only.svg" width="360">
  </picture>
</p>

# Adverse Drug Event Discovery

Find adverse drug events and the drugs they follow in conversational text, and analyse them as tables and charts in Facthory.

![Licence: Apache-2.0](https://img.shields.io/badge/licence-Apache--2.0-blue) ![Runs on Facthory](https://img.shields.io/badge/runs%20on-Facthory-1f6feb) ![Status: install coming](https://img.shields.io/badge/status-install%20coming-lightgrey)

> **Install coming.** This is a Facthory solution: its data, analysis code, agent skill and starting pages load into a Facthory workspace as a ready project. Installing from this page is not available yet; this repository is being prepared for it.

## What it does

Adverse Drug Event Discovery reads conversational texts, such as forum posts and support calls, and turns them into tables: which texts report an adverse drug event (ADE), which drugs and ADEs they mention, whether the ADE really happened, and which drug each ADE belongs to. It then builds a knowledge graph from those rows and ranks what is talked about.

1. **Classify.** `classify_ade` reads each text through a text model and says whether it reports an ADE: a harmful reaction a person connects with taking a drug.
2. **Extract entities.** `extract_entities` returns the ADE and DRUG mentions in each text, with a confidence.
3. **Judge assertions.** `extract_assertions` judges each ADE mention as Present, Absent, Possible, Hypothetical, Conditional or Someone_else, so "no rash at all", "I'm worried it might cause nausea" and "my mum gets nausea from metformin" are told apart from a rash the writer has.
4. **Extract relations.** `extract_relations` returns the ADE-DRUG pairs: relation "1" when the text ties the ADE to the drug, "0" when it keeps them apart. Answers that fail validation go to `rejected_*` tables with the reason.
5. **Build the graph.** One SQL job turns the extracted rows into two tables, `graph_nodes` and `graph_edges`: drug and ADE nodes, `Drug -HAS_ADVERSE_EVENT-> ADE` for every linked pair, and the assertion status of each ADE mention. Every edge records the text and the text span it came from.
6. **Analyse.** Four SQL jobs rank the results:
   - the most-mentioned drug and ADE names;
   - the ADEs mentioned in the most texts, leaving out the ones the text denies;
   - drug-ADE pairs by co-occurrence in the same text;
   - drug-ADE pairs the relation extraction linked.

The two pair jobs also scale each pair's count from 0 to 1 across the drugs of the same ADE (`normalized_count`).

Steps 1 to 4 need a text model. Steps 5 and 6 are plain SQL on DuckDB and need none.

## How it works in Facthory

- Jobs read tables and write tables. They draw no screens and own no storage; querying, charting, joining with your own data, permissions and audit belong to the platform.
- The knowledge graph is two tables, not a graph database. See "Graph tables" below. Any graph view can be drawn from them.
- The agent skill in `skills/` and the starter page in `pages/` describe how to work with the tables and the jobs.
- Sample data in this repository is synthetic. No real patient data and no real conversations.

## What the result could look like

![Mock-up of a Facthory report page titled "Adverse drug event signals", marked "Sample data": four figures (texts read, texts reporting an event, linked drug and event pairs, classifier accuracy), a table of the most linked drug and adverse event pairs with their text counts, a bar chart of the most mentioned adverse events, and a bar chart of how the text asserts each event.](docs/images/adverse-event-signals-mockup.png)

A design illustration of a report built from this solution's tables, drawn from this repository's own sample data (300 invented texts). It is a mock-up: the page layout is a design, not a screenshot of a released feature, and the accuracy shown compares invented predictions with the labels.

## Jobs

| Job | What it does | Inputs | Outputs |
| --- | --- | --- | --- |
| `classify_ade` | Decides whether each conversational text reports an adverse drug event | `ade_events` | `ade_classification`, `rejected_classifications` |
| `extract_entities` | Extracts the ADE and DRUG mentions with their confidence | `ade_events` | `entities`, `rejected_entities` |
| `extract_assertions` | Judges whether each ADE mention is Present, Absent, Possible, Hypothetical, Conditional or Someone_else | `ade_events` | `assertions`, `rejected_assertions` |
| `extract_relations` | Extracts the ADE-DRUG pairs that belong together (relation "1") or not ("0") | `ade_events` | `relations`, `rejected_relations` |
| `build_knowledge_graph` | Builds the adverse-drug-event knowledge graph as node and edge tables | `ade_events`, `entities`, `assertions`, `relations` | `graph_nodes`, `graph_edges` |
| `most_common_entities` | The most-mentioned drug and ADE names | `entities` | `most_common` |
| `asserted_ade_frequency` | The ADEs mentioned in the most texts with an assertion other than Absent | `assertions` | `asserted_ades` |
| `drug_ade_pairs` | Drug-ADE pairs by co-occurrence within the same text, scaled per ADE | `entities` | `drug_ade_pairs` |
| `linked_drug_ade_pairs` | Drug-ADE pairs the relation extraction linked, scaled per ADE | `relations` | `linked_pairs` |

The four extraction jobs take a `TextModel` (see `src/adverse_drug_event_discovery/text/interface.py`) as a third argument; Facthory provides model access, and every model answer is validated before it becomes a row. The table of texts and every table extracted from it have a `text_id` column that names the text; the graph's `evidence_document_id` holds the same value. Named measures for the classifier, the assertion statuses and the graph's linked pairs live in `metrics/`.

### Graph tables

The graph follows the "graph tables, draft 0" shape that all Facthory solutions share.

- `graph_nodes`: `node_id` (stable across runs, `<node_type>:<key>`), `node_type`, `key` (the natural key), `label`, `properties` (JSON text).
- `graph_edges`: `edge_id` (stable hash of source, relationship, target or value, and evidence), `source_id`, `target_id` (null when the fact is a literal), `relationship`, `value` (the literal, else null), `valid_from` and `valid_to` (dates the fact held; `valid_to` is null when unknown), `evidence_document_id`, `evidence_start`, `evidence_end` (character offsets in that text; null when the text was not found), `confidence` (null when not scored), `properties`.

Every node an edge names exists in `graph_nodes`, and a fact has either `target_id` or `value`, never both. In this repository the nodes are `Drug` and `ADE`, with the lower-cased, trimmed mention as key (`Drug:metformin`, `ADE:nausea`) and the mention as written as label. There are two kinds of fact:

- `Drug -HAS_ADVERSE_EVENT-> ADE` for every relation row with relation "1", with the confidence of that row.
- `ADE -ASSERTION-> <status>` for every assertion row: a literal edge with the status (Present, Absent, Possible, Hypothetical, Conditional or Someone_else) in `value` and the confidence of that row.

A linked pair is what the text ties together, not a confirmed reaction: whether the ADE happened is in the assertion fact. To read one as the other, join the two facts on the ADE node and on `evidence_document_id`. A drug node and an ADE node are shared by all texts; the text in `evidence_document_id` (a `text_id` of `ade_events`) says which text a fact belongs to. The evidence span is the first occurrence of the ADE text in that text (`evidence_start` inclusive, `evidence_end` exclusive, 0-based). The texts carry no date, so `valid_from` and `valid_to` are always null.

## Data

The sample tables in `data/sample/` are synthetic and CC0-1.0: `ade_events`, `ade_classification`, `entities`, `assertions`, `relations`, `graph_nodes` and `graph_edges`. They hold 300 invented forum-style and support-call-style texts about 25 drugs and 30 side effects, 574 entity rows, 243 assertions, 262 relations, 55 graph nodes and 462 edges, made by `data/generate_sample.py`. See [data/README.md](data/README.md) for origin and licence per file. No real patient data and no real conversations.

## Run it locally

```
uv sync
uv run python -m adverse_drug_event_discovery most_common_entities --entity-type DRUG
uv run python -m adverse_drug_event_discovery drug_ade_pairs --min-conversations 2
uv run python -m adverse_drug_event_discovery build_knowledge_graph
uv run pytest
```

`uv run python -m adverse_drug_event_discovery --help` lists every job; each job has its own `--help`. The four extraction jobs additionally take `--model-answers <file>` with a recorded-answers JSON (see `tests/recorded_answers.json`), since they read texts through a model behind `text.interface`; the other jobs run without any model. Verified on the synthetic sample data only, not yet in a Facthory workspace.

## Open points

- **No text model ships.** The four extraction jobs run through the `TextModel` interface. The only implementation is `text/recorded.py`, which replays recorded answers for the sample texts. A model must be plugged in behind `text/interface.py` before new texts can be processed.
- **Evidence spans are found by text search**, not reported by the model: `evidence_start` and `evidence_end` mark the first occurrence of the ADE text in the text, and are null when it is not found (for example a word the model normalised). `valid_from` and `valid_to` are always null.
- **No codes are resolved.** ADE names are not mapped to a vocabulary such as MedDRA, and drugs are not mapped to a drug vocabulary. A name is the text as written, lower-cased for the node key, so synonyms and brand and generic names of one drug are separate nodes.
- **Co-occurrence is not causation, and no disproportionality statistics are included.** `drug_ade_pairs` counts the texts that mention a drug and an ADE together, `linked_drug_ade_pairs` the pairs the relation extraction links, and `normalized_count` only scales a count within its ADE. None of this is a signal score or a reporting ratio.
- **`asserted_ade_frequency` leaves out only the Absent mentions.** Possible, Hypothetical, Conditional and Someone_else mentions count too.
- **The pair jobs lower-case the drug but not the ADE text**, so "Rash" and "rash" count as two ADEs there, while the graph keys lower-case both. The sample writes every ADE in lower case, so the difference does not show in it.
- **The predictions in `ade_classification` are invented** to exercise the metrics: they equal the label except for a fixed 6 percent of the texts. They are not the output of a model, and the accuracy and confusion matrix in `metrics/` say nothing about any classifier.
- **The sample is invented.** It is generated from templates, so its texts are cleaner than real forum posts and calls, and it shows the shape of the tables, not realistic volumes or accuracy. The extracted rows are exact by construction, not model output.
- **A query that reads `entities` twice** (`drug_ade_pairs` joins it with itself) counts it as one dataset in the analytics engine: to confirm against the engine; it has not been run against it.
- **Installing into Facthory is not available yet.** The code is verified on the sample data on a laptop only.
- **The Dockerfile has not been built or verified.**
- **DuckDB 2.x only.** The code uses the DuckDB 2.0 Arrow API (`to_arrow_table`).

## Not for clinical use

This is software for research and analytics. It is not a medical device and must not be used to diagnose or treat a patient. Results can be wrong; a qualified person reviews them.

## Disclaimers

Bandpey GmbH (“Facthory”) does not dispense medical, diagnosis, or treatment advice. This Solution (“tool”) is for informational purposes only and may not be used as a substitute for professional medical advice, treatment, or diagnosis. This tool may not be used within Facthory to process Protected Health Information (“PHI”) as defined in the Health Insurance Portability and Accountability Act of 1996, unless you have executed with Facthory a contract that allows for processing PHI, an accompanying Business Associate Agreement (BAA), and are running this tool within a HIPAA Account.

## Licence

Apache-2.0. See [LICENSE](LICENSE). "Facthory" and the Facthory logo are trademarks of their owner and are not covered by that licence. This includes the logo shown in the image under `docs/images/`.

