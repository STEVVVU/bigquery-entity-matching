CREATE TABLE {{destination}} AS
SELECT id, content, ml_generate_embedding_result AS embedding, ml_generate_embedding_status AS status
FROM ML.GENERATE_EMBEDDING(
  MODEL {{model}},
  (SELECT id, content FROM {{source}}),
  STRUCT(TRUE AS flatten_json_output, 'SEMANTIC_SIMILARITY' AS task_type)
);
