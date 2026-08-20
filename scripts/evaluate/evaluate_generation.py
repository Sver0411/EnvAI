#!/usr/bin/env python3
"""Aggregate human-verified generation labels and hard contamination checks."""
from __future__ import annotations

import argparse
from common import load_cases, write_result


def evaluate(cases: list[dict]) -> dict:
    measures = ("fact_accuracy", "numeric_accuracy", "citation_accuracy", "missing_information_accuracy", "professional_acceptability")
    totals = {key: 0.0 for key in measures}; unsupported = contamination = fabricated_citations = source_markers = 0
    for case in cases:
        labels = case.get("human_labels", {})
        for key in measures: totals[key] += float(labels.get(key, 0))
        text = case.get("generated_text", "")
        unsupported += int(case.get("unsupported_claim_count", 0)); contamination += int(case.get("case_contamination_count", 0))
        fabricated_citations += int(case.get("fabricated_citation_count", 0)); source_markers += int("[[" in text and "]]" in text)
    total = len(cases) or 1
    return {"cases": len(cases), **{key: value / total for key, value in totals.items()}, "unsupported_claim_count": unsupported,
            "case_contamination_count": contamination, "fabricated_citation_count": fabricated_citations, "internal_source_marker_count": source_markers}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("input"); parser.add_argument("--output", required=True)
    args = parser.parse_args(); write_result(args.output, evaluate(load_cases(args.input)))
