-- The share of conversational texts whose predicted ADE flag matches the label.
SELECT CAST(SUM(CASE WHEN e.is_ade = c.predicted_ade THEN 1 ELSE 0 END) AS DOUBLE)
       / count(*) AS accuracy
FROM ade_classification AS c
JOIN ade_events AS e
    ON e.id = c.id
