from dataclasses import asdict, dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class Entity:
    id: str
    name: str


@dataclass(frozen=True)
class Decision:
    query_id: str
    canonical_id: str | None
    status: str
    score: float | None


def normalize(value: str) -> str:
    return value.strip().lower()


def decide(query_id: str, candidates: list[tuple[str, float]], threshold: float, margin: float) -> Decision:
    if not 0 <= threshold <= 1 or not 0 <= margin <= 1:
        raise ValueError("threshold and margin must be between 0 and 1")
    if any(not 0 <= score <= 1 for _, score in candidates):
        raise ValueError("scores must be between 0 and 1")
    ranked = sorted(candidates, key=lambda x: (-x[1], x[0]))
    if not ranked or ranked[0][1] < threshold:
        return Decision(query_id, None, "rejected", ranked[0][1] if ranked else None)
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] <= margin:
        return Decision(query_id, None, "ambiguous", ranked[0][1])
    return Decision(query_id, ranked[0][0], "matched", ranked[0][1])


def match(query: Entity, catalog: list[Entity], method: str, threshold: float = 0.8,
          margin: float = 0.05) -> Decision:
    if method not in ("exact", "lexical"):
        raise ValueError("unknown method")
    key = normalize(query.name)
    candidates = []
    for entity in catalog:
        other = normalize(entity.name)
        score = float(bool(key) and key == other) if method == "exact" else (
            SequenceMatcher(None, key, other, autojunk=False).ratio() if key and other else 0.0
        )
        candidates.append((entity.id, score))
    return decide(query.id, candidates, 1.0 if method == "exact" else threshold, margin)


def metrics(decisions: list[Decision], truth: dict[str, str | None], comparisons: int) -> dict:
    tp = sum(d.canonical_id is not None and d.canonical_id == truth[d.query_id] for d in decisions)
    fp = sum(d.canonical_id is not None and d.canonical_id != truth[d.query_id] for d in decisions)
    fn = sum(truth[d.query_id] is not None and d.canonical_id != truth[d.query_id] for d in decisions)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    unknown = [d for d in decisions if truth[d.query_id] is None]
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "unknown_count": len(unknown),
            "unknown_rejected": sum(d.status == "rejected" for d in unknown),
            "unknown_accepted": sum(d.status == "matched" for d in unknown),
            "accepted": sum(d.status == "matched" for d in decisions),
            "coverage": sum(d.status == "matched" for d in decisions) / len(decisions)
            if decisions else 0.0,
            "ambiguous": sum(d.status == "ambiguous" for d in decisions),
            "rejected": sum(d.status == "rejected" for d in decisions),
            "comparisons": comparisons, "predictions": [asdict(d) for d in decisions]}
