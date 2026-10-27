-- Group exact normalized names to expose collisions before mapping.
SELECT LOWER(TRIM(content)) AS normalized_name, ARRAY_AGG(id ORDER BY id) AS ids,
       COUNT(*) AS entity_count
FROM {{source}}
GROUP BY normalized_name;
