-- The most-mentioned drug and ADE names, optionally for one entity type only.
-- $entity_type empty means both; $min_confidence keeps confident mentions.
SELECT entity,
       lower(chunk) AS name,
       count(*) AS mentions
FROM entities
WHERE confidence >= $min_confidence
  AND chunk <> ''
  AND ($entity_type = '' OR entity = $entity_type)
GROUP BY entity, lower(chunk)
ORDER BY mentions DESC, name
LIMIT $limit
