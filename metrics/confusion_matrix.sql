-- Actual versus predicted ADE per conversational text.
SELECT e.is_ade AS actual_ade,
       c.predicted_ade AS predicted_ade,
       count(*) AS texts
FROM ade_classification AS c
JOIN ade_events AS e
    ON e.text_id = c.text_id
GROUP BY e.is_ade, c.predicted_ade
ORDER BY actual_ade, predicted_ade
