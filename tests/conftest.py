import importlib.util
from pathlib import Path
from urllib import request

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not make network requests")

    monkeypatch.setattr(request, "urlopen", blocked)
    for key in ("MODEL_API_KEY", "JUDGE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(scope="session")
def scripts():
    modules = {}
    for name in ("run_model_responses", "run_judge_scoring", "aggregate_results"):
        spec = importlib.util.spec_from_file_location(name, ROOT / "code" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules[name] = module
    return modules
