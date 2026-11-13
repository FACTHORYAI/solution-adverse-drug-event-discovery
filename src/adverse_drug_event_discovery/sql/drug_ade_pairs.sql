-- Drug-ADE pairs by co-occurrence within the same conversation, with each pair's
-- share of the busiest drug for its ADE (the per-ADE min-max normalisation of the
-- co-occurrence counts).
WITH pairs AS (
    SELECT DISTINCT e.id, lower(e.chunk) AS drug, a.chunk AS ade
    FROM entities AS e
    JOIN entities AS a
        ON a.id = e.id
    WHERE e.entity = 'DRUG'
      AND a.entity = 'ADE'
      AND e.confidence >= $min_confidence
      AND a.confidence >= $min_confidence
      AND e.chunk <> ''
      AND a.chunk <> ''
),
counts AS (
    SELECT drug, ade, count(*) AS conversations
    FROM pairs
    GROUP BY drug, ade
    HAVING count(*) >= $min_conversations
)
SELECT drug,
       ade,
       conversations,
       CASE
           WHEN max(conversations) OVER (PARTITION BY ade)
                = min(conversations) OVER (PARTITION BY ade) THEN 0.0
           ELSE (conversations - min(conversations) OVER (PARTITION BY ade))
                / (max(conversations) OVER (PARTITION BY ade)
                   - min(conversations) OVER (PARTITION BY ade))
       END AS normalized_count
FROM counts
ORDER BY drug, ade
