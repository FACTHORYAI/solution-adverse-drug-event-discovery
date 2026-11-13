task: extract_entities

Extract the adverse-drug-event and drug mentions from one conversational text.
Return only a JSON array, one object per mention, with these keys:

- `chunk`: the mentioned text.
- `entity`: "ADE" for a harmful reaction the text connects with taking a drug,
  "DRUG" for a drug by its name.
- `confidence`: a number between 0 and 1.

Return [] when the text mentions neither. Return only the JSON array, no prose.
