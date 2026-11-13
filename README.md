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

Find adverse drug events and the drugs they follow in conversational text, and analyse them as tables and charts in Facthory.

## How it will work in Facthory

- You install it into a workspace and get a project: sample data, the analysis, the agent's instructions and starting pages.
- Its results are tables and pages in your workspace, so you can query them, chart them and ask the agent about them, inside your permissions.
- Sample data in this repository is synthetic or openly licensed. No real patient data.

## Not for clinical use

This is software for research and analytics. It is not a medical device and must not be used to diagnose or treat a patient. Results can be wrong; a qualified person reviews them.

## Licence

Apache-2.0. See [LICENSE](LICENSE). "Facthory" and the Facthory logo are trademarks of their owner and are not covered by that licence.

## Jobs

| Job | What it does | Inputs | Outputs |
| --- | --- | --- | --- |
| `classify_ade` | Decides whether each conversational text reports an adverse drug event | `ade_events` | `ade_classification`, `rejected_classifications` |
| `extract_entities` | Extracts the ADE and DRUG mentions with their confidence | `ade_events` | `entities`, `rejected_entities` |
| `extract_assertions` | Judges whether each ADE mention is Present, Absent, Possible, Hypothetical, Conditional or Someone_else | `ade_events` | `assertions`, `rejected_assertions` |
| `extract_relations` | Extracts the ADE-DRUG pairs that belong together (relation "1") | `ade_events` | `relations`, `rejected_relations` |
| `most_common_entities` | The most-mentioned drug and ADE names | `entities` | `most_common` |
| `asserted_ade_frequency` | The ADEs most often reported as actually experienced | `assertions` | `asserted_ades` |
| `drug_ade_pairs` | Drug-ADE pairs by co-occurrence within the same conversation, normalised per ADE | `entities` | `drug_ade_pairs` |
| `linked_drug_ade_pairs` | Drug-ADE pairs the relation extraction linked, normalised per ADE | `relations` | `linked_pairs` |

The four extraction jobs take a `TextModel` (see `src/adverse_drug_event_discovery/text/interface.py`) as a third argument; Facthory provides model access, and every model answer is validated before it becomes a row. Named measures for the classifier and the assertion statuses live in `metrics/`.

## Data

The sample tables in `data/sample/` are synthetic and openly licensed (CC0-1.0): `ade_events`, `ade_classification`, `entities`, `assertions` and `relations`. See [data/README.md](data/README.md) for one row per file with origin and licence. No real patient data and no real conversations.

## Run it locally

```
uv sync
uv run python -m adverse_drug_event_discovery most_common_entities --entity-type DRUG
uv run python -m adverse_drug_event_discovery drug_ade_pairs --min-conversations 2
uv run pytest
```

`uv run python -m adverse_drug_event_discovery --help` lists every job; each job has its own `--help`. The four extraction jobs additionally take `--model-answers <file>` with a recorded-answers JSON (see `tests/recorded_answers.json`), since they read texts through a model behind `text.interface`; the analysis jobs run without any model.

Co-occurrence is not causation: `drug_ade_pairs` counts the conversations that mention a drug and an ADE together, `linked_drug_ade_pairs` counts the pairs the relation extraction links, and `normalized_count` expresses each pair's count as a share of the busiest drug for its ADE.

