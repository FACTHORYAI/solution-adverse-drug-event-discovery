-- How many distinct drug-ADE pairs the knowledge graph links, across all texts.
SELECT count(DISTINCT source_id || '|' || target_id) AS linked_pairs
FROM graph_edges
WHERE relationship = 'HAS_ADVERSE_EVENT';
