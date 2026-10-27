import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .evaluation import evaluate


def main():
    parser = argparse.ArgumentParser(description="Vendor catalog entity matching")
    sub = parser.add_subparsers(dest="command", required=True)
    local = sub.add_parser("evaluate", help="Run the synthetic held-out lexical evaluation")
    local.add_argument("--output", type=Path, required=True)
    local.add_argument("--repeats", type=int, default=5)
    cloud = sub.add_parser("cloud", help="Run an explicit BigQuery operation (may incur charges)")
    cloud.add_argument("operation", choices=["register", "embed", "search", "baseline"])
    cloud.add_argument("--project", required=True)
    cloud.add_argument("--model")
    cloud.add_argument("--connection")
    cloud.add_argument("--source")
    cloud.add_argument("--destination")
    cloud.add_argument("--catalog")
    cloud.add_argument("--queries")
    cloud.add_argument("--threshold", type=float, default=0.8)
    cloud.add_argument("--margin", type=float, default=0.05)
    args = parser.parse_args()
    if args.command == "evaluate":
        result = evaluate(args.repeats)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return
    required = {"register": ("model", "connection"), "embed": ("model", "source", "destination"),
                "search": ("catalog", "queries"), "baseline": ("source",)}[args.operation]
    if any(not getattr(args, name) for name in required):
        parser.error("operation requires: " + ", ".join("--" + name for name in required))
    from google.cloud import bigquery
    from . import cloud as bq
    client = bigquery.Client(project=args.project)
    if args.operation == "register":
        bq.register(client, args.model, args.connection)
    elif args.operation == "embed":
        bq.embed(client, args.model, args.source, args.destination)
    elif args.operation == "search":
        print(json.dumps([asdict(d) for d in bq.search(client, args.catalog, args.queries,
                                                       args.threshold, args.margin)], indent=2))
    else:
        print(json.dumps([dict(row) for row in bq.query(client, "exact_baseline",
                                                        {"source": args.source})], indent=2))


if __name__ == "__main__":
    main()
