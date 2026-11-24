"""Failure-injection benchmark.

    python -m daginquest.eval.run_eval --models qwen3:8b llama3.1:8b
"""
import argparse
import asyncio
import json
import time
from pathlib import Path

from daginquest.agent.nodes.rca import analyze
from daginquest.agent.nodes.verify_citations import citation_ratio

CASES_DIR = Path(__file__).parent / "cases"
RESULTS_DIR = Path(__file__).parent / "results"


async def run_model(model: str, cases: list[dict]) -> dict:
    correct = inconclusive = 0
    citation_scores: list[float] = []
    details = []
    for case in cases:
        start = time.perf_counter()
        result = await analyze(case["log"], case.get("dag_source", ""), model=model)
        elapsed = time.perf_counter() - start
        hit = result.category == case["expected_category"]
        correct += hit
        inconclusive += result.category == "INCONCLUSIVE"
        ratio = citation_ratio(result.cited_lines, case["log"])
        citation_scores.append(ratio)
        details.append({
            "id": case["id"], "expected": case["expected_category"], "got": result.category,
            "correct": hit, "confidence": result.confidence, "citation_ratio": ratio,
            "seconds": round(elapsed, 2),
        })
    total = len(cases)
    return {
        "model": model, "total": total, "accuracy": round(correct / total, 3) if total else 0,
        "inconclusive_rate": round(inconclusive / total, 3) if total else 0,
        "avg_citation_validity": round(sum(citation_scores) / total, 3) if total else 0,
        "details": details,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    args = parser.parse_args()

    cases = [json.loads(p.read_text()) for p in sorted(CASES_DIR.glob("*.json"))]
    if not cases:
        raise SystemExit(f"No cases found in {CASES_DIR}")
    RESULTS_DIR.mkdir(exist_ok=True)
    for model in args.models:
        report = await run_model(model, cases)
        out = RESULTS_DIR / f"{model.replace(':', '_').replace('/', '_')}.json"
        out.write_text(json.dumps(report, indent=2))
        print(f"{model}: accuracy={report['accuracy']} "
              f"citations={report['avg_citation_validity']} -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
