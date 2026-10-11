import csv
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "text",
    [
        '{"score": 7, "behavior_match": "partial"}',
        '```json\n{"score": 7, "behavior_match": "partial"}\n```',
        '```\n{"score": 7, "behavior_match": "partial"}\n```',
        'Scoring result: {"score": 7, "behavior_match": "partial"}',
    ],
)
def test_parse_judge_json(scripts, text):
    result = scripts["run_judge_scoring"].parse_judge_json(text)
    assert result == {"score": 7, "behavior_match": "partial"}


@pytest.mark.parametrize("text", ["not JSON", '{"score": }', "```json\n{broken}\n```"])
def test_parse_judge_json_failure(scripts, text):
    with pytest.raises(json.JSONDecodeError):
        scripts["run_judge_scoring"].parse_judge_json(text)


@pytest.mark.parametrize(
    "name,input_flag,input_name,extra",
    [
        (
            "run_model_responses",
            "--dataset-csv",
            "benchmark_sample.csv",
            [
                "--model",
                "offline",
                "--evaluated-model-id",
                "offline",
                "--evaluated-model-name",
                "Offline",
            ],
        ),
        (
            "run_judge_scoring",
            "--responses-csv",
            "responses_sample.csv",
            [
                "--judge-model",
                "offline",
                "--judge-model-id",
                "offline",
            ],
        ),
    ],
)
def test_dry_run_requires_no_key_or_network(
    scripts, monkeypatch, tmp_path, capsys, name, input_flag, input_name, extra
):
    module = scripts[name]
    api = Mock(side_effect=AssertionError("API must not be called in dry-run"))
    monkeypatch.setattr(module, "chat_completion", api)
    output = tmp_path / "must-not-be-created.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            name,
            input_flag,
            str(ROOT / "examples" / input_name),
            "--output-csv",
            str(output),
            *extra,
            "--dry-run",
            "--limit",
            "1",
        ],
    )
    assert module.main() == 0
    api.assert_not_called()
    assert not output.exists()
    assert "Dry run only" in capsys.readouterr().out


def test_response_resume_skips_existing_keys(scripts, monkeypatch, tmp_path):
    module = scripts["run_model_responses"]
    responses = module.load_csv(ROOT / "examples" / "responses_sample.csv")
    output = tmp_path / "responses.csv"
    module.append_row(output, responses[0])
    monkeypatch.setenv("MODEL_API_KEY", "offline-test-only")
    api = Mock(return_value=("offline test answer", "stop"))
    monkeypatch.setattr(module, "chat_completion", api)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run",
            "--dataset-csv",
            str(ROOT / "examples" / "benchmark_sample.csv"),
            "--output-csv",
            str(output),
            "--model",
            "offline",
            "--evaluated-model-id",
            responses[0]["evaluated_model_id"],
            "--evaluated-model-name",
            responses[0]["evaluated_model_name"],
            "--resume",
        ],
    )
    assert module.main() == 0
    api.assert_called_once()
    result = module.load_csv(output)
    assert len(result) == 2
    assert len(module.existing_keys(output)) == 2
    assert result[0] == responses[0]
    api.reset_mock()
    assert module.main() == 0
    api.assert_not_called()
    assert len(module.load_csv(output)) == 2


def test_judge_resume_keeps_judges_separate(scripts, monkeypatch, tmp_path):
    module = scripts["run_judge_scoring"]
    rows = module.load_csv(ROOT / "examples" / "scores_sample.csv")
    output = tmp_path / "scores.csv"
    module.append_row(output, rows[0])
    other = {**rows[1], "judge_model_id": "other-judge"}
    module.append_row(output, other)
    monkeypatch.setenv("JUDGE_API_KEY", "offline-test-only")
    api = Mock(
        return_value=json.dumps(
            {
                "score": 8,
                "behavior_match": "yes",
                "unsafe_compliance": "no",
                "safe_alternative_present": "not_required",
            }
        )
    )
    monkeypatch.setattr(module, "chat_completion", api)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run",
            "--responses-csv",
            str(ROOT / "examples" / "responses_sample.csv"),
            "--output-csv",
            str(output),
            "--judge-model",
            "offline",
            "--judge-model-id",
            rows[0]["judge_model_id"],
            "--resume",
        ],
    )
    assert module.main() == 0
    api.assert_called_once()
    assert len(module.load_csv(output)) == 3
    api.reset_mock()
    assert module.main() == 0
    api.assert_not_called()
    assert len(module.existing_keys(output)) == 3


def test_failed_judge_json_is_recorded_without_score(scripts, monkeypatch, tmp_path):
    module = scripts["run_judge_scoring"]
    output = tmp_path / "failed.csv"
    monkeypatch.setenv("JUDGE_API_KEY", "offline-test-only")
    monkeypatch.setattr(module, "chat_completion", Mock(return_value="not JSON"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run",
            "--responses-csv",
            str(ROOT / "examples" / "responses_sample.csv"),
            "--output-csv",
            str(output),
            "--judge-model",
            "offline",
            "--judge-model-id",
            "offline",
            "--limit",
            "1",
        ],
    )
    assert module.main() == 0
    row = module.load_csv(output)[0]
    assert row["status"].startswith("parse_failed:")
    assert row["score"] == ""


def test_example_schemas_and_linked_keys(scripts):
    model = scripts["run_model_responses"]
    judge = scripts["run_judge_scoring"]
    prompts = model.load_csv(ROOT / "examples" / "benchmark_sample.csv")
    responses = model.load_csv(ROOT / "examples" / "responses_sample.csv")
    scores = judge.load_csv(ROOT / "examples" / "scores_sample.csv")
    assert len(prompts) == len(responses) == len(scores) == 2
    assert set(responses[0]) == set(model.OUTPUT_COLUMNS)
    assert set(scores[0]) == set(judge.OUTPUT_COLUMNS)
    required = {
        "item_id",
        "dimension",
        "prompt",
        "expected_behavior",
        "risk_boundary",
        "safe_alternative_required",
    }
    assert required <= set(prompts[0])
    for prompt, response, score in zip(prompts, responses, scores):
        assert prompt["item_id"] == response["item_id"] == score["item_id"]
        assert prompt["prompt"] == response["prompt"]
        assert response["evaluated_model_id"] == score["evaluated_model_id"]
        assert response["run_id"] == score["run_id"] == "1"
        assert prompt["expected_behavior"] in judge.BEHAVIOR_RUBRICS
        assert prompt["risk_boundary"] in judge.RISK_BOUNDARY_RUBRICS


@pytest.mark.parametrize(
    "sample,original,keys",
    [
        ("benchmark_sample.csv", "dataset/content_safety.csv", ("item_id",)),
        (
            "responses_sample.csv",
            "model_responses/content_safety_responses.csv",
            ("evaluated_model_id", "run_id", "item_id"),
        ),
        (
            "scores_sample.csv",
            "scoring_results/gpt55_scores.csv",
            ("evaluated_model_id", "run_id", "item_id"),
        ),
    ],
)
def test_examples_preserve_published_field_values(sample, original, keys):
    with (ROOT / "examples" / sample).open(encoding="utf-8-sig", newline="") as stream:
        samples = list(csv.DictReader(stream))
    wanted = {tuple(row[key] for key in keys): row for row in samples}
    matched = {}
    with (ROOT / original).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            key = tuple(row[field] for field in keys)
            if key in wanted:
                matched[key] = row
    assert matched == wanted
