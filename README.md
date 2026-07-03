# Scientometric LLM Ethics Benchmark Data Release

This minimal release contains only the CSV files needed to inspect the benchmark prompts, model responses, and scoring results.

## Directory structure

- `dataset/`: five benchmark prompt CSV files, one for each ethical dimension.
- `model_responses/`: five response CSV files, one for each ethical dimension. Each file includes responses from the eight evaluated models across available runs.
- `scoring_results/`: four score CSV files. Three files contain AI-judge scores from GPT-5.5, DeepSeek-v4-pro, and Qwen3.6-plus. One file contains the merged human-validation scores from three expert raters.

## Notes

The scoring-result CSV files intentionally retain scores and categorical judgments only; long judge rationales, internal analysis notes, and redundant prompt/response text are omitted from this minimal public package.

Please cite the associated manuscript if you use this dataset.
