-- Nodes of the adverse-drug-event knowledge graph (graph tables, draft 0).
-- node_id = node_type || ':' || key, stable across runs. key is the lower-cased,
-- trimmed mention; label is the mention as written. A drug or an ADE is one node
-- however many texts mention it.
WITH mentions AS (
    SELECT CASE entity WHEN 'DRUG' THEN 'Drug' ELSE 'ADE' END AS node_type,
           lower(trim(chunk)) AS key,
           trim(chunk) AS label
    FROM entities
    WHERE entity IN ('DRUG', 'ADE') AND chunk IS NOT NULL AND trim(chunk) <> ''

    UNION ALL

    SELECT 'ADE', lower(trim(chunk)), trim(chunk)
    FROM assertions
    WHERE chunk IS NOT NULL AND trim(chunk) <> ''

    UNION ALL

    SELECT 'ADE', lower(trim(chunk1)), trim(chunk1)
    FROM relations
    WHERE entity1 = 'ADE' AND chunk1 IS NOT NULL AND trim(chunk1) <> ''

    UNION ALL

    SELECT 'Drug', lower(trim(chunk2)), trim(chunk2)
    FROM relations
    WHERE entity2 = 'DRUG' AND chunk2 IS NOT NULL AND trim(chunk2) <> ''
)
SELECT node_type || ':' || key AS node_id,
       node_type,
       key,
       min(label) AS label,
       NULL::VARCHAR AS properties
FROM mentions
GROUP BY node_type, key
ORDER BY node_id
