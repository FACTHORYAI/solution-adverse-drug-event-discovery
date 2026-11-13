task: extract_assertions

For every adverse-drug-event mention in one conversational text, judge whether
it is actually experienced. Return only a JSON array, one object per mention,
with these keys:

- `chunk`: the adverse-event text.
- `assertion`: one of Present, Absent, Possible, Hypothetical, Conditional,
  Someone_else. "Present" when the person experiences it; "Someone_else" when
  another person does; "Absent" when the text denies it; "Hypothetical" when it
  is only read about or imagined; "Conditional" when it depends on something
  happening first; "Possible" when the text is unsure.
- `confidence`: a number between 0 and 1.

Return [] when the text names no adverse event. Return only the JSON array.
