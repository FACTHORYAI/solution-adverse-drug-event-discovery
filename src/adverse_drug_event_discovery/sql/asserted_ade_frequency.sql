-- The ADEs most often reported as experienced: one row per ADE name, counting
-- the distinct conversations in which it appears with an assertion other than Absent.
SELECT lower(chunk) AS ade,
       count(DISTINCT text_id) AS conversations
FROM assertions
WHERE assertion <> 'Absent'
  AND assertion <> ''
  AND chunk <> ''
GROUP BY lower(chunk)
ORDER BY conversations DESC, ade
LIMIT $limit
