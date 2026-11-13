-- How the assertion statuses distribute over the extracted ADE mentions.
SELECT assertion, count(*) AS assertion_count
FROM assertions
GROUP BY assertion
ORDER BY assertion_count, assertion
