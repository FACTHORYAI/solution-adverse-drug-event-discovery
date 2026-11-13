task: classify_ade

Decide whether one conversational text reports an adverse drug event: a harmful
reaction a person connects with taking a drug. Mentions of a drug without a
reaction, instructions on how to take a drug, and reactions that are only read
about or expected do not count. Return only one JSON object:

- `predicted_ade`: true when the text reports an adverse drug event, else false.

Return only the JSON object, no prose.
