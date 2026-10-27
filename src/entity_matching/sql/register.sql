CREATE MODEL IF NOT EXISTS {{model}}
REMOTE WITH CONNECTION {{connection}}
OPTIONS (ENDPOINT = 'gemini-embedding-001');
