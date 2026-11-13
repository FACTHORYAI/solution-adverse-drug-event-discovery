-- Drug-ADE pairs the relation extraction actually linked within one conversation
-- (relation "1"), with each pair's share of the busiest drug for its ADE.
WITH pairs AS (
    SELECT DISTINCT text_id, lower(chunk2) AS drug, chunk1 AS ade
    FROM relations
    WHERE relation = '1'
      AND entity1 = 'ADE'
      AND entity2 = 'DRUG'
      AND confidence >= $min_confidence
      AND chunk1 <> ''
      AND chunk2 <> ''
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
