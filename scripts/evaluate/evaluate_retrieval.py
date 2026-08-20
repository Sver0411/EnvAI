#!/usr/bin/env python3
from __future__ import annotations

import argparse
from common import load_cases, write_result


def evaluate(cases: list[dict]) -> dict:
    recall5 = recall10 = mrr = wrong_jurisdiction = wrong_version = 0.0
    for case in cases:
        expected = set(case["expected_document_ids"]); result = case.get("result_document_ids", [])
        recall5 += bool(expected & set(result[:5])); recall10 += bool(expected & set(result[:10]))
        ranks = [index + 1 for index, item in enumerate(result) if item in expected]
        mrr += 1 / min(ranks) if ranks else 0
        wrong_jurisdiction += sum(1 for item in case.get("returned_metadata", []) if item.get("jurisdiction") not in {None, case.get("expected_jurisdiction")})
        wrong_version += sum(1 for item in case.get("returned_metadata", []) if item.get("is_superseded") is True)
    total = len(cases) or 1
    return {"cases": len(cases), "recall_at_5": recall5 / total, "recall_at_10": recall10 / total, "mrr": mrr / total,
            "wrong_jurisdiction_count": int(wrong_jurisdiction), "superseded_source_count": int(wrong_version)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("input"); parser.add_argument("--output", required=True)
    args = parser.parse_args(); write_result(args.output, evaluate(load_cases(args.input)))
