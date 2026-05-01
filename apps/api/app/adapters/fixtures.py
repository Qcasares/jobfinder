from pathlib import Path


def load_adapter_fixture(name: str) -> str:
    fixture_root = Path(__file__).resolve().parents[4] / "fixtures" / "adapters"
    requested = Path(name)
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("adapter fixture names must stay within fixtures/adapters")
    path = (fixture_root / requested).resolve()
    if fixture_root.resolve() not in path.parents:
        raise ValueError("adapter fixture names must stay within fixtures/adapters")
    return path.read_text(encoding="utf-8")
