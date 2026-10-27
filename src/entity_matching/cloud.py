"""BigQuery SDK boundary. Operations are explicit and can incur cloud charges."""
import re
from pathlib import Path

from google.cloud import bigquery

from .core import decide

SQL = Path(__file__).parent / "sql"


def identifier(value: str, connection: bool = False) -> str:
    parts = value.split(".")
    if len(parts) != 3 or not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", parts[0]):
        raise ValueError("expected project.dataset.object")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*" if not connection else
                        r"[A-Za-z0-9_-]+", parts[1]):
        raise ValueError("invalid dataset or location")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*" if not connection else
                        r"[A-Za-z0-9_-]+", parts[2]):
        raise ValueError("invalid resource identifier")
    return f"`{value}`"


def query(client: bigquery.Client, name: str, resources: dict[str, str], parameters=()):
    text = (SQL / f"{name}.sql").read_text(encoding="utf-8")
    for key, value in resources.items():
        text = text.replace("{{" + key + "}}", identifier(value, connection=key == "connection"))
    if "{{" in text:
        raise ValueError("missing SQL resource")
    config = bigquery.QueryJobConfig(query_parameters=list(parameters))
    return client.query(text, job_config=config).result()


def register(client: bigquery.Client, model: str, connection: str):
    return query(client, "register", {"model": model, "connection": connection})


def embed(client: bigquery.Client, model: str, source: str, destination: str):
    return query(client, "embed", {"model": model, "source": source, "destination": destination})


def search(client: bigquery.Client, catalog: str, queries: str, threshold: float, margin: float):
    if not 0 <= threshold <= 1 or not 0 <= margin <= 1:
        raise ValueError("threshold and margin must be between 0 and 1")
    rows = query(client, "search", {"catalog": catalog, "queries": queries}, [
        bigquery.ScalarQueryParameter("threshold", "FLOAT64", threshold),
        bigquery.ScalarQueryParameter("margin", "FLOAT64", margin),
    ])
    grouped = {}
    for row in rows:
        grouped.setdefault(row.query_id, [])
        if row.canonical_id is not None:
            grouped[row.query_id].append((row.canonical_id, 1 - row.distance / 2))
    return [decide(q, candidates, threshold, margin) for q, candidates in grouped.items()]
