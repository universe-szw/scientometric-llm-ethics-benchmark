from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCORE_COLUMNS = {
    "judge_model_id",
    "evaluated_model_id",
    "evaluated_model_name",
    "run_id",
    "dimension",
    "item_id",
    "score",
    "status",
}
HUMAN_COLUMNS = {
    "evaluated_model_id",
    "run_id",
    "item_id",
    "gpt55_score",
    "human_score_E1",
    "human_score_E2",
    "human_score_E3",
    "human_mean_score",
}
SUMMARY_COLUMNS = [
    "judge_model_id",
    "evaluated_model_id",
    "evaluated_model_name",
    "dimension",
    "n_items",
    "n_scores",
    "n_runs",
    "mean_score",
    "item_mean_sd",
    "min_item_mean",
    "max_item_mean",
]
SUCCESS_STATUSES = {"scored", "ok"}


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(sorted(missing))}")
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError(f"{path}: malformed CSV row")
    return rows


def numeric_score(value: str, context: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context}: invalid numeric score {value!r}") from exc
    if not math.isfinite(score) or not 0 <= score <= 10:
        raise ValueError(f"{context}: score must be finite and between 0 and 10")
    return score


def aggregate_scores(
    paths: list[Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    # Average runs per item before averaging items, matching the paper's weighting.
    item_scores: dict[tuple[str, str, str, str, str], list[tuple[str, float]]] = defaultdict(list)
    seen: set[tuple[str, str, str, str]] = set()
    identities: dict[tuple[str, str], str] = {}
    dimensions: dict[str, str] = {}
    exclusions: Counter[str] = Counter()
    files = []
    for path in paths:
        rows = read_csv(path, SCORE_COLUMNS)
        included = 0
        for number, row in enumerate(rows, start=2):
            context = f"{path}:{number}"
            identifiers = [
                row[field].strip()
                for field in (
                    "judge_model_id",
                    "evaluated_model_id",
                    "run_id",
                    "item_id",
                )
            ]
            if not all(identifiers) or not row["dimension"].strip():
                raise ValueError(f"{context}: empty record identifier or dimension")
            key = tuple(identifiers)
            if key in seen:
                raise ValueError(f"{context}: duplicate score key {key}")
            seen.add(key)
            status = row["status"].strip()
            if status not in SUCCESS_STATUSES:
                exclusions[status or "empty_status"] += 1
                continue
            score = numeric_score(row["score"], context)
            judge, model, run, item = identifiers
            name = row["evaluated_model_name"].strip()
            dimension = row["dimension"].strip()
            if not name:
                raise ValueError(f"{context}: empty model display name")
            identity = (judge, model)
            if identity in identities and identities[identity] != name:
                raise ValueError(f"{context}: inconsistent model display name for {model}")
            identities[identity] = name
            if item in dimensions and dimensions[item] != dimension:
                raise ValueError(f"{context}: inconsistent dimension for {item}")
            dimensions[item] = dimension
            item_scores[(judge, model, name, dimension, item)].append((run, score))
            included += 1
        files.append({"path": str(path), "rows_read": len(rows), "rows_included": included})
    if not item_scores:
        raise ValueError("No successfully scored records found")

    grouped: dict[tuple[str, str, str, str], list[list[tuple[str, float]]]] = defaultdict(list)
    overall: dict[tuple[str, str, str, str], list[list[tuple[str, float]]]] = defaultdict(list)
    for (judge, model, name, dimension, _), observations in item_scores.items():
        grouped[(judge, model, name, dimension)].append(observations)
        overall[(judge, model, name, "all")].append(observations)

    def summarize(groups: dict) -> list[dict[str, Any]]:
        result = []
        for (judge, model, name, dimension), items in sorted(groups.items()):
            means = [statistics.mean(score for _, score in item) for item in items]
            result.append(
                {
                    "judge_model_id": judge,
                    "evaluated_model_id": model,
                    "evaluated_model_name": name,
                    "dimension": dimension,
                    "n_items": len(items),
                    "n_scores": sum(len(item) for item in items),
                    "n_runs": len({run for item in items for run, _ in item}),
                    "mean_score": statistics.mean(means),
                    "item_mean_sd": statistics.stdev(means) if len(means) > 1 else None,
                    "min_item_mean": min(means),
                    "max_item_mean": max(means),
                }
            )
        return result

    metadata = {
        "method": "Mean available runs per item, then equally weight observed items; judges kept separate.",
        "item_mean_sd": "Sample SD across item means, not a CI or run-to-run SD.",
        "missing_values": "No imputation; non-success statuses excluded; malformed successful rows rejected.",
        "files": files,
        "excluded_status_counts": dict(sorted(exclusions.items())),
        "included_score_count": sum(len(item) for item in item_scores.values()),
        "included_model_item_count": len(item_scores),
        "available_runs_per_item_counts": dict(
            sorted(Counter(len(observations) for observations in item_scores.values()).items())
        ),
    }
    return summarize(overall), summarize(grouped), metadata


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) < 2 or min(x) == max(x) or min(y) == max(y):
        return None
    return statistics.correlation(x, y)


def human_comparison(path: Path) -> dict[str, Any]:
    rows = read_csv(path, HUMAN_COLUMNS)
    if not rows:
        raise ValueError(f"{path}: no human-validation rows")
    human = []
    automated = []
    seen = set()
    for number, row in enumerate(rows, start=2):
        context = f"{path}:{number}"
        key = (row["evaluated_model_id"], row["run_id"], row["item_id"])
        if not all(key) or key in seen:
            raise ValueError(f"{context}: empty or duplicate human-validation key {key}")
        seen.add(key)
        expert_scores = [numeric_score(row[f"human_score_E{i}"], context) for i in (1, 2, 3)]
        mean = statistics.mean(expert_scores)
        recorded_mean = numeric_score(row["human_mean_score"], context)
        if not math.isclose(mean, recorded_mean, rel_tol=0, abs_tol=1e-6):
            raise ValueError(f"{context}: human_mean_score does not match the three expert scores")
        human.append(mean)
        automated.append(numeric_score(row["gpt55_score"], context))
    differences = [ai - person for ai, person in zip(automated, human)]
    return {
        "source": str(path),
        "n_pairs": len(rows),
        "pearson": correlation(human, automated),
        "spearman": correlation(average_ranks(human), average_ranks(automated)),
        "mae": statistics.mean(abs(value) for value in differences),
        "mean_signed_difference_automated_minus_human": statistics.mean(differences),
        "method": "Pairwise full-range comparison against the three-expert arithmetic mean; ties use average ranks.",
        "undefined_correlations": "null for fewer than two pairs or a constant score/rank vector",
        "scope": "Descriptive subset statistics; no new confidence intervals, ICC, or reliability claims.",
    }


def validate_output_dir(output: Path, inputs: list[Path]) -> None:
    root = Path(__file__).resolve().parents[1]
    destination = output.resolve()
    for name in ("dataset", "model_responses", "scoring_results", "examples", "assets"):
        if destination.is_relative_to(root / name):
            raise ValueError(f"Output directory must not be inside the released {name}/ assets")
    filenames = {
        "model_summary.csv",
        "model_dimension_summary.csv",
        "aggregation_metadata.json",
        "human_validation_summary.json",
    }
    targets = {destination / name for name in filenames}
    if any(path.resolve() in targets for path in inputs):
        raise ValueError("An output path would overwrite an input file")


def write_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{value:.8f}" if isinstance(value, float) else value
                    for key, value in row.items()
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Describe existing scores without model API calls."
    )
    parser.add_argument("--scores-csv", type=Path, nargs="+", required=True)
    parser.add_argument("--human-validation-csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/summary"))
    args = parser.parse_args()
    try:
        inputs = args.scores_csv + (
            [args.human_validation_csv] if args.human_validation_csv else []
        )
        validate_output_dir(args.output_dir, inputs)
        if (
            not args.human_validation_csv
            and (args.output_dir / "human_validation_summary.json").exists()
        ):
            raise ValueError(
                "Output directory has an earlier human summary; choose a new --output-dir"
            )
        overall, dimensions, metadata = aggregate_scores(args.scores_csv)
        human = human_comparison(args.human_validation_csv) if args.human_validation_csv else None
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_summary(args.output_dir / "model_summary.csv", overall)
    write_summary(args.output_dir / "model_dimension_summary.csv", dimensions)
    for name, result in (
        ("aggregation_metadata.json", metadata),
        ("human_validation_summary.json", human),
    ):
        if result is not None:
            (args.output_dir / name).write_text(
                json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
    print(f"Summarized {metadata['included_score_count']} scores into {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
