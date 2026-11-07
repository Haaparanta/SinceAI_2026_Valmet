"""The shared surface: pydantic models == TypeScript interfaces == exported JSON Schema (AGENTS.md S4, S7)."""

from scripts.check_contracts import TS_FILE, main, pydantic_models, ts_interfaces


def test_models_and_ts_interfaces_have_the_same_fields() -> None:
    py = pydantic_models()
    ts = ts_interfaces(TS_FILE.read_text())
    assert set(py) == set(ts)
    for name, model in py.items():
        assert set(model.model_fields) == ts[name], name


def test_exported_json_schema_is_current() -> None:
    assert main(["--check"]) == 0
