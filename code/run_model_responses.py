from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request


OUTPUT_COLUMNS = [
    "evaluated_model_id",
    "evaluated_model_name",
    "run_id",
    "dimension",
    "item_id",
    "prompt",
    "response",
    "expected_behavior",
    "risk_boundary",
    "safe_alternative_required",
    "risk_level",
    "difficulty_level",
    "prompt_language",
    "context_type",
    "turn_type",
    "adaptation_operation",
    "contrast_set_id",
    "finish_reason",
]

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant for scientometric and research-evaluation tasks. "
    "Respond to the user's request."
)


def env_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    top_p: float,
    max_tokens: int,
    retries: int,
    retry_sleep: float,
) -> tuple[str, str]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    endpoint = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = request.Request(endpoint, data=body, headers=headers, method="POST")
            with request.urlopen(req, timeout=180) as response:
                data = json.loads(response.read().decode("utf-8"))
            if data.get("error"):
                raise RuntimeError(json.dumps(data["error"], ensure_ascii=False))
            choices = data.get("choices") or []
            if not choices:
                return "", ""
            choice = choices[0]
            message = choice.get("message") or {}
            content = message.get("content") or choice.get("text") or ""
            return str(content or ""), str(choice.get("finish_reason") or "")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"HTTP {exc.code}: {detail}")
        except Exception as exc:  # pragma: no cover - requires live API
            last_error = exc
        if attempt < retries:
            time.sleep(retry_sleep)
    raise RuntimeError(str(last_error))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({column: row.get(column, "") for column in OUTPUT_COLUMNS})


def existing_keys(path: Path) -> set[tuple[str, str, str]]:
    if not path.exists():
        return set()
    keys: set[tuple[str, str, str]] = set()
    for row in load_csv(path):
        keys.add((row.get("evaluated_model_id", ""), row.get("run_id", ""), row.get("item_id", "")))
    return keys


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Generate model responses for one benchmark dataset CSV.")
    parser.add_argument("--dataset-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--model", required=True, help="Provider model id sent to the API.")
    parser.add_argument("--evaluated-model-id", required=True, help="Public model id written to the output CSV.")
    parser.add_argument("--evaluated-model-name", required=True, help="Public display name written to the output CSV.")
    parser.add_argument("--run-id", type=int, default=1)
    parser.add_argument("--base-url", default=env_value("MODEL_BASE_URL", "OPENAI_BASE_URL") or "https://api.openai.com/v1")
    parser.add_argument("--api-key-env", default="MODEL_API_KEY", help="Environment variable containing the API key. Falls back to OPENAI_API_KEY.")
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep", type=float, default=5.0)
    parser.add_argument("--request-sleep", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = load_csv(args.dataset_csv)
    if args.limit is not None:
        rows = rows[: args.limit]

    print(f"Loaded {len(rows)} benchmark items from {args.dataset_csv}")
    if args.dry_run:
        print("Dry run only. No API calls will be made.")
        print(f"Output schema: {', '.join(OUTPUT_COLUMNS)}")
        return 0

    api_key = env_value(args.api_key_env, "OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(f"Missing API key. Set {args.api_key_env} or OPENAI_API_KEY.")

    done = existing_keys(args.output_csv) if args.resume else set()
    for index, item in enumerate(rows, start=1):
        key = (args.evaluated_model_id, str(args.run_id), item["item_id"])
        if key in done:
            continue
        messages = [
            {"role": "system", "content": args.system_prompt},
            {"role": "user", "content": item["prompt"]},
        ]
        content, finish_reason = chat_completion(
            base_url=args.base_url,
            api_key=api_key,
            model=args.model,
            messages=messages,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            retries=args.retries,
            retry_sleep=args.retry_sleep,
        )
        output = {
            **item,
            "evaluated_model_id": args.evaluated_model_id,
            "evaluated_model_name": args.evaluated_model_name,
            "run_id": args.run_id,
            "response": content,
            "finish_reason": finish_reason,
        }
        append_row(args.output_csv, output)
        print(f"[{index}/{len(rows)}] wrote {item['item_id']}")
        if args.request_sleep:
            time.sleep(args.request_sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
