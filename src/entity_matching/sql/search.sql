-- Failed embedding rows must be inspected before this query; do not silently skip them.
ASSERT (SELECT COUNTIF(COALESCE(status, 'missing status') != '' OR embedding IS NULL) FROM {{catalog}}) = 0
  AS 'catalog embedding failures';
ASSERT (SELECT COUNTIF(COALESCE(status, 'missing status') != '' OR embedding IS NULL) FROM {{queries}}) = 0
  AS 'query embedding failures';
ASSERT (SELECT COUNT(*) = COUNT(DISTINCT id) AND COUNTIF(id IS NULL) = 0 FROM {{catalog}})
  AS 'catalog IDs must be unique and non-null';
ASSERT (SELECT COUNT(*) = COUNT(DISTINCT id) AND COUNTIF(id IS NULL) = 0 FROM {{queries}})
  AS 'query IDs must be unique and non-null';
ASSERT @threshold BETWEEN 0 AND 1 AND @margin BETWEEN 0 AND 1 AS 'invalid threshold';
SELECT q.id AS query_id, s.base.id AS canonical_id, s.distance
FROM {{queries}} q
LEFT JOIN (
  SELECT * FROM VECTOR_SEARCH(TABLE {{catalog}}, 'embedding', TABLE {{queries}},
    query_column_to_search => 'embedding', top_k => 2, distance_type => 'COSINE',
    options => '{"use_brute_force":true}')
) s ON q.id = s.query.id;
