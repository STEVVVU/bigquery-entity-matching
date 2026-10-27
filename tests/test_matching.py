import pytest

from entity_matching.core import Entity, decide, match, metrics, normalize
from entity_matching.evaluation import calibrate, corpus, make_queries
from entity_matching.cloud import embed, identifier, register, search
from types import SimpleNamespace
from importlib.resources import files


def test_reject_ambiguity_and_empty():
    assert decide("q", [], .8, .05).status == "rejected"
    assert decide("q", [("a", .9), ("b", .89)], .8, .05).status == "ambiguous"
    assert match(Entity("q", ""), [Entity("a", "")], "exact").status == "rejected"
    assert match(Entity("q", "Acme"), [Entity("a", "Acme"), Entity("b", "acme")],
                 "exact").status == "ambiguous"


def test_metrics_wrong_mapping_counts_fp_and_fn():
    m = metrics([decide("q", [("wrong", .9)], .8, .05)], {"q": "right"}, 1)
    assert (m["tp"], m["fp"], m["fn"]) == (0, 1, 1)


def test_held_out_and_reproducible_predictions():
    reserved, test, catalog, queries, truth = corpus()
    assert len(catalog) == 1000 and len(queries) == 150
    assert {r[0] for r in reserved}.isdisjoint(r[0] for r in test)
    assert corpus() == (reserved, test, catalog, queries, truth)
    assert sum(v is None for v in truth.values()) == 50


def test_calibration_uses_reserved_entities_and_declared_objective():
    reserved, test, _, holdout_queries, _ = corpus()
    calibration_queries, _ = make_queries(reserved, 3031)
    for queries in (calibration_queries, holdout_queries):
        assert len({q.id for q in queries}) == len(queries)
    assert {q.id for q in calibration_queries}.isdisjoint(q.id for q in holdout_queries)
    assert {normalize(q.name) for q in calibration_queries}.isdisjoint(
        normalize(q.name) for q in holdout_queries)
    result = calibrate(reserved)
    best = max(result["grid"], key=lambda t: (t["precision"], t["tp"], t["threshold"], t["margin"]))
    assert (result["threshold"], result["margin"]) == (best["threshold"], best["margin"])
    assert all("-q-" not in d["query_id"] or
               d["query_id"].split("-q-")[1] in {r[0] for r in reserved}
               for d in result["metrics"]["predictions"])
    assert {r[0] for r in reserved}.isdisjoint(r[0] for r in test)


def test_sql_identifier_and_parameter_boundary():
    assert identifier("my-project.dataset.table") == "`my-project.dataset.table`"
    with pytest.raises(ValueError):
        identifier("my-project.dataset.table`; DROP TABLE x")

    class Client:
        rows = []

        def query(self, text, job_config):
            self.text, self.config = text, job_config
            return self

        def result(self):
            return self.rows

    client = Client()
    register(client, "my-project.data.model", "my-project.us.connection")
    assert "CREATE MODEL IF NOT EXISTS" in client.text and "REMOTE WITH CONNECTION" in client.text
    embed(client, "my-project.data.model", "my-project.data.source", "my-project.data.dest")
    assert "ML.GENERATE_EMBEDDING" in client.text and "`my-project.data.dest`" in client.text
    client.rows = [SimpleNamespace(query_id="q", canonical_id="c", distance=.1)]
    assert search(client, "my-project.data.catalog", "my-project.data.q", .8, .05)[0].canonical_id == "c"
    assert "VECTOR_SEARCH" in client.text
    assert "@threshold" in client.text
    assert [(p.name, p.value) for p in client.config.query_parameters] == [
        ("threshold", .8), ("margin", .05)]
    assert files("entity_matching").joinpath("sql", "embed.sql").is_file()

    class Failed(Client):
        def result(self):
            raise RuntimeError("job failed")

    with pytest.raises(RuntimeError, match="job failed"):
        register(Failed(), "my-project.data.model", "my-project.us.connection")
