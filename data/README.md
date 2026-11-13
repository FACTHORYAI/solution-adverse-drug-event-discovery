# Sample data

Every file below is synthetic, generated for this repository from hand-written
conversational texts; no real patient data and no real conversations. Licence:
CC0-1.0. The folder is a few kilobytes in total, far under the 5 MB per file and
20 MB per folder limits.

| File | What it is | Where it came from | Licence | Synthetic |
| --- | --- | --- | --- | --- |
| `ade_events.parquet` | 15 conversational texts with their ADE label: id, text, is_ade | Hand-written for this repository | CC0-1.0 | yes |
| `ade_classification.parquet` | The predicted ADE flag per text, as the `classify_ade` job produces it | Hand-written to match `ade_events.parquet` | CC0-1.0 | yes |
| `entities.parquet` | ADE and DRUG mentions per conversation: id, chunk, entity, confidence | Hand-written to match `ade_events.parquet` | CC0-1.0 | yes |
| `assertions.parquet` | Assertion status per ADE mention: Present, Absent, Someone_else and more | Hand-written to match `ade_events.parquet` | CC0-1.0 | yes |
| `relations.parquet` | Related ADE-DRUG pairs per conversation: relation, entity1, chunk1, entity2, chunk2, confidence | Hand-written to match `ade_events.parquet` | CC0-1.0 | yes |

The original solution's dataset (ADE Corpus V2, about 20,000 conversational
texts from the ADE corpus collection) was **not** republished here: its licence
was not verified for redistribution, so this repository ships its own smaller
synthetic sample instead. A workspace run points the same jobs at the corpus
through Facthory's own storage.
