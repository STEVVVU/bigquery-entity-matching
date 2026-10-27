"""Synthetic, entity-disjoint holdout; never a production quality estimate."""
import random
import time
from difflib import SequenceMatcher

from .core import Entity, decide, match, metrics, normalize


def make_queries(rows, seed):
    rng = random.Random(seed)
    selected = rng.sample(rows, 100)
    queries, truth = [], {}
    for index, (entity_id, name) in enumerate(selected):
        variants = [name.upper(), f"  {name}  ", name.replace("Supply", "Supplies"),
                    name.replace("Vendor", "Vndr"), name.replace(" ", "-"),
                    name.replace("Supply", "Supply Co")]
        query_id = f"{seed}-q-{entity_id}"
        queries.append(Entity(query_id, variants[index % len(variants)]))
        truth[query_id] = entity_id
    for index, (_, name) in enumerate(rng.sample(rows, 30)):
        query_id = f"{seed}-unknown-near-{index}"
        queries.append(Entity(query_id, name + " Branch"))
        truth[query_id] = None
    for index, (_, name) in enumerate(rng.sample(rows, 20)):
        query_id = f"{seed}-unknown-{index}"
        queries.append(Entity(query_id, f"Unrelated bakery {name.split()[1]}"))
        truth[query_id] = None
    return queries, truth


def corpus():
    names_rng = random.Random(1109)
    codes = names_rng.sample(range(100000, 999999), 1200)
    rows = [(f"v{i:04}", f"Vendor {code} Supply") for i, code in enumerate(codes)]
    random.Random(329).shuffle(rows)
    reserved, test = rows[:200], rows[200:]
    assert not {i for i, _ in reserved} & {i for i, _ in test}
    catalog = [Entity(i, name) for i, name in test]
    queries, truth = make_queries(test, 2027)
    return reserved, test, catalog, queries, truth


def calibrate(reserved):
    catalog = [Entity(i, name) for i, name in reserved]
    queries, truth = make_queries(reserved, 3031)
    rankings = []
    for q in queries:
        key = normalize(q.name)
        scores = [(e.id, SequenceMatcher(None, key, normalize(e.name), autojunk=False).ratio())
                  for e in catalog]
        rankings.append((q.id, scores))
    trials = []
    for threshold in (0.8, 0.85, 0.9, 0.95, 1.0):
        for margin in (0.0, 0.01, 0.025, 0.05, 0.1):
            decisions = [decide(q, scores, threshold, margin) for q, scores in rankings]
            stats = metrics(decisions, truth, len(catalog) * len(queries))
            # Precision first, then correct accepted positives; deterministic conservative tie-break.
            trials.append((stats["precision"], stats["tp"], threshold, margin, stats))
    precision, tp, threshold, margin, stats = max(trials, key=lambda t: t[:4])
    return {"seed": 3031, "objective": "maximize precision, then true positives; "
            "ties choose higher threshold then margin", "threshold": threshold, "margin": margin,
            "precision": precision, "tp": tp, "metrics": stats,
            "grid": [{"threshold": t[2], "margin": t[3], "precision": t[0], "tp": t[1]}
                     for t in trials]}


def evaluate(repeats: int = 5) -> dict:
    if repeats < 5 or repeats > 100:
        raise ValueError("repeats must be between 5 and 100")
    reserved, test, catalog, queries, truth = corpus()
    calibration_queries, _ = make_queries(reserved, 3031)
    assert len({q.id for q in calibration_queries}) == len(calibration_queries)
    assert len({q.id for q in queries}) == len(queries)
    assert {q.id for q in calibration_queries}.isdisjoint(q.id for q in queries)
    assert {normalize(q.name) for q in calibration_queries}.isdisjoint(
        normalize(q.name) for q in queries)
    calibration = calibrate(reserved)
    result = {"seeds": {"names": 1109, "split": 329, "queries": 2027},
              "reserved_ids": [r[0] for r in reserved], "test_ids": [r[0] for r in test],
              "catalog_size": len(catalog), "query_count": len(queries),
              "calibration_queries": [{"id": q.id, "normalized": normalize(q.name)}
                                      for q in calibration_queries],
              "holdout_queries": [{"id": q.id, "normalized": normalize(q.name)}
                                  for q in queries],
              "threshold": 0.8, "margin": 0.05, "calibration": calibration,
              "note": "Synthetic lexical comparator, NOT Gemini; calibrated on disjoint IDs.",
              "runs": []}
    for repeat in range(repeats):
        order = ("exact", "fixed", "calibrated")
        order = order[repeat % 3:] + order[:repeat % 3]
        for method in order:
            start = time.perf_counter_ns()
            threshold = calibration["threshold"] if method == "calibrated" else 0.8
            margin = calibration["margin"] if method == "calibrated" else 0.05
            decisions = [match(q, catalog, "exact" if method == "exact" else "lexical",
                               threshold, margin) for q in queries]
            elapsed = (time.perf_counter_ns() - start) / 1_000_000
            result["runs"].append({"repeat": repeat, "method": method, "latency_ms": elapsed} |
                                  metrics(decisions, truth, len(catalog) * len(queries)))
    return result
