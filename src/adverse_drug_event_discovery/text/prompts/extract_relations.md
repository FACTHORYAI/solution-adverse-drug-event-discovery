task: extract_relations

Extract the pairs of adverse-drug-event and drug mentions that belong together
in one conversational text. Return only a JSON array, one object per pair, with
these keys:

- `relation`: "1" when the pair is related in the text, "0" when not.
- `entity1`: "ADE", `chunk1`: the adverse-event text.
- `entity2`: "DRUG", `chunk2`: the drug text.
- `confidence`: a number between 0 and 1.

Return [] when the text names no such pair. Return only the JSON array.
