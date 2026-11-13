-- Edges of the adverse-drug-event knowledge graph (graph tables, draft 0): one fact per row.
--   Drug -HAS_ADVERSE_EVENT-> ADE            from every relation row with relation '1'
--   ADE -ASSERTION-> (literal status)        from every assertion row; the status is in value
-- Every fact carries the text it came from and, when the ADE text is found in it, the
-- character span of its first occurrence (evidence_start inclusive, evidence_end
-- exclusive, 0-based). The texts carry no date, so valid_from and valid_to are null.
WITH linked AS (
    SELECT r.text_id,
           'Drug:' || lower(trim(r.chunk2)) AS drug_id,
           'ADE:' || lower(trim(r.chunk1)) AS ade_id,
           r.chunk1 AS chunk,
           r.confidence,
           instr(e.text, r.chunk1) - 1 AS start
    FROM relations AS r
    LEFT JOIN ade_events AS e ON e.text_id = r.text_id
    WHERE r.relation = '1'
      AND r.entity1 = 'ADE'
      AND r.entity2 = 'DRUG'
      AND trim(r.chunk1) <> ''
      AND trim(r.chunk2) <> ''
),
asserted AS (
    SELECT a.text_id,
           'ADE:' || lower(trim(a.chunk)) AS ade_id,
           a.assertion,
           a.chunk,
           a.confidence,
           instr(e.text, a.chunk) - 1 AS start
    FROM assertions AS a
    LEFT JOIN ade_events AS e ON e.text_id = a.text_id
    WHERE a.assertion <> '' AND trim(a.chunk) <> ''
),
facts AS (
    SELECT drug_id AS source_id,
           ade_id AS target_id,
           'HAS_ADVERSE_EVENT' AS relationship,
           NULL::VARCHAR AS value,
           NULL::DATE AS valid_from,
           text_id AS evidence_document_id,
           CASE WHEN start >= 0 THEN start END AS evidence_start,
           CASE WHEN start >= 0 THEN start + length(chunk) END AS evidence_end,
           confidence
    FROM linked

    UNION ALL

    SELECT ade_id,
           NULL::VARCHAR,
           'ASSERTION',
           assertion,
           NULL::DATE,
           text_id,
           CASE WHEN start >= 0 THEN start END,
           CASE WHEN start >= 0 THEN start + length(chunk) END,
           confidence
    FROM asserted
),
keyed AS (
    SELECT md5(concat_ws('|', source_id, relationship, coalesce(target_id, ''),
                         coalesce(value, ''), evidence_document_id,
                         coalesce(evidence_start, -1))) AS edge_id,
           *
    FROM facts
)
SELECT edge_id,
       any_value(source_id) AS source_id,
       any_value(target_id) AS target_id,
       any_value(relationship) AS relationship,
       any_value(value) AS value,
       NULL::DATE AS valid_from,
       NULL::DATE AS valid_to,
       any_value(evidence_document_id) AS evidence_document_id,
       any_value(evidence_start) AS evidence_start,
       any_value(evidence_end) AS evidence_end,
       max(confidence) AS confidence,
       NULL::VARCHAR AS properties
FROM keyed
GROUP BY edge_id
ORDER BY evidence_document_id, source_id, relationship, target_id, value, evidence_start
