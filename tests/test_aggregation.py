import csv
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def score_row(item="A", run="1", score="0", judge="judge", status="scored"):
    return {
        "judge_model_id": judge,
        "evaluated_model_id": "model",
        "evaluated_model_name": "Model",
        "dimension": "content_safety",
        "item_id": item,
        "run_id": run,
        "score": score,
        "status": status,
    }


def test_item_weighting_with_missing_runs(scripts, tmp_path):
    rows = [score_row(), score_row(run="2", score="10"), score_row(item="B", score="9")]
    path = write_rows(tmp_path / "scores.csv", rows)
    overall, dimensions, metadata = scripts["aggregate_results"].aggregate_scores([path])
    assert overall[0]["mean_score"] == 7  # Mean of item means 5 and 9, not 19/3.
    assert dimensions[0]["mean_score"] == 7
    assert overall[0]["n_items"] == 2
    assert overall[0]["n_scores"] == 3
    assert overall[0]["n_runs"] == 2
    assert overall[0]["item_mean_sd"] == pytest.approx(math.sqrt(8))
    assert metadata["available_runs_per_item_counts"] == {1: 1, 2: 1}


def test_judges_are_not_pooled_and_failures_are_excluded(scripts, tmp_path):
    rows = [
        score_row(score="3"),
        score_row(score="9", judge="second"),
        score_row(item="failed", score="", status="parse_failed: bad JSON"),
    ]
    path = write_rows(tmp_path / "scores.csv", rows)
    overall, _, metadata = scripts["aggregate_results"].aggregate_scores([path])
    assert [row["mean_score"] for row in overall] == [3, 9]
    assert metadata["included_score_count"] == 2
    assert metadata["excluded_status_counts"] == {"parse_failed: bad JSON": 1}


def test_duplicate_score_keys_are_rejected(scripts, tmp_path):
    path = write_rows(tmp_path / "scores.csv", [score_row(), score_row()])
    with pytest.raises(ValueError, match="duplicate score key"):
        scripts["aggregate_results"].aggregate_scores([path])


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "11", "", "not a number"])
def test_invalid_successful_scores_are_rejected(scripts, tmp_path, value):
    path = write_rows(tmp_path / "scores.csv", [score_row(score=value)])
    with pytest.raises(ValueError, match="score"):
        scripts["aggregate_results"].aggregate_scores([path])


def test_missing_csv_columns_are_rejected(scripts, tmp_path):
    path = write_rows(tmp_path / "scores.csv", [{"score": "9"}])
    with pytest.raises(ValueError, match="missing columns"):
        scripts["aggregate_results"].aggregate_scores([path])


def human_rows():
    return [
        {
            "evaluated_model_id": "model",
            "run_id": "1",
            "item_id": str(index),
            "human_score_E1": str(human),
            "human_score_E2": str(human),
            "human_score_E3": str(human),
            "human_mean_score": str(human),
            "gpt55_score": str(ai),
        }
        for index, (human, ai) in enumerate([(0, 1), (1, 2), (1, 2), (3, 4)])
    ]


def test_human_comparison_ties_and_difference_direction(scripts, tmp_path):
    module = scripts["aggregate_results"]
    path = write_rows(tmp_path / "human.csv", human_rows())
    result = module.human_comparison(path)
    assert result["pearson"] == pytest.approx(1)
    assert result["spearman"] == pytest.approx(1)
    assert result["mae"] == 1
    assert result["mean_signed_difference_automated_minus_human"] == 1
    assert result["n_pairs"] == 4
    assert module.average_ranks([0, 1, 1, 3]) == [1, 2.5, 2.5, 4]


def test_constant_scores_have_undefined_correlations(scripts, tmp_path):
    rows = human_rows()
    for row in rows:
        row["gpt55_score"] = "5"
    result = scripts["aggregate_results"].human_comparison(write_rows(tmp_path / "human.csv", rows))
    assert result["pearson"] is None
    assert result["spearman"] is None


def test_inconsistent_human_mean_is_rejected(scripts, tmp_path):
    rows = human_rows()
    rows[0]["human_mean_score"] = "2"
    with pytest.raises(ValueError, match="does not match"):
        scripts["aggregate_results"].human_comparison(write_rows(tmp_path / "human.csv", rows))


def test_aggregation_cli_writes_descriptive_outputs(scripts, monkeypatch, tmp_path):
    out = tmp_path / "summary"
    human = write_rows(tmp_path / "human.csv", human_rows())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "aggregate",
            "--scores-csv",
            str(ROOT / "examples" / "scores_sample.csv"),
            "--human-validation-csv",
            str(human),
            "--output-dir",
            str(out),
        ],
    )
    assert scripts["aggregate_results"].main() == 0
    assert {p.name for p in out.iterdir()} == {
        "model_summary.csv",
        "model_dimension_summary.csv",
        "aggregation_metadata.json",
        "human_validation_summary.json",
    }
    metadata = json.loads((out / "aggregation_metadata.json").read_text(encoding="utf-8"))
    assert metadata["included_score_count"] == 2


@pytest.mark.parametrize(
    "directory", ["dataset", "model_responses", "scoring_results", "examples", "assets"]
)
def test_aggregation_refuses_output_inside_release_assets(scripts, directory):
    with pytest.raises(ValueError, match="released"):
        scripts["aggregate_results"].validate_output_dir(ROOT / directory / "new-output", [])


def test_aggregation_refuses_overwriting_input(scripts, tmp_path):
    with pytest.raises(ValueError, match="overwrite"):
        scripts["aggregate_results"].validate_output_dir(tmp_path, [tmp_path / "model_summary.csv"])


def test_aggregation_does_not_leave_a_stale_human_summary(scripts, monkeypatch, tmp_path):
    summary = tmp_path / "human_validation_summary.json"
    summary.write_text('{"n_pairs": 42}', encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "aggregate",
            "--scores-csv",
            str(ROOT / "examples" / "scores_sample.csv"),
            "--output-dir",
            str(tmp_path),
        ],
    )
    with pytest.raises(SystemExit) as error:
        scripts["aggregate_results"].main()
    assert error.value.code == 2
    assert summary.read_text(encoding="utf-8") == '{"n_pairs": 42}'
    assert not (tmp_path / "model_summary.csv").exists()
