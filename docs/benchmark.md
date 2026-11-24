# Failure-injection benchmark

Each case in `backend/src/daginquest/eval/cases/*.json` has a log excerpt and a known
root-cause category. Run:

    make eval MODELS="qwen3:8b llama3.1:8b"

Metrics: category accuracy, citation validity rate, inconclusive rate, latency.
Grow the suite to 25-30 cases (import errors, timeouts, bad SQL, missing connections,
auth failures, OOM, upstream data missing). Publish results per model in the README.
