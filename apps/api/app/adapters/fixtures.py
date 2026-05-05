from pathlib import Path


def load_adapter_fixture(name: str) -> str:
    api_fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "adapters"
    repo_fixture_root = Path(__file__).resolve().parents[4] / "fixtures" / "adapters"
    requested = Path(name)
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("adapter fixture names must stay within fixtures/adapters")
    for fixture_root in (api_fixture_root, repo_fixture_root):
        path = (fixture_root / requested).resolve()
        if fixture_root.resolve() not in path.parents:
            raise ValueError("adapter fixture names must stay within fixtures/adapters")
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"adapter fixture not found: {name}")
