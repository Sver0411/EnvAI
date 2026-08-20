#!/usr/bin/env python3
from __future__ import annotations

import argparse
from common import f1, load_cases, write_result


def evaluate(cases: list[dict]) -> dict:
    expected: set[tuple[str, str]] = set(); detected: set[tuple[str, str]] = set(); critical_expected = critical_detected = 0
    for case in cases:
        actual = {(str(issue["id"]), str(issue.get("severity", ""))) for issue in case.get("expected_issues", [])}
        found = {(str(issue["id"]), str(issue.get("severity", ""))) for issue in case.get("detected_issues", [])}
        expected |= actual; detected |= found
        critical_expected += sum(severity == "critical" for _, severity in actual)
        critical_detected += sum((item, severity) in found and severity == "critical" for item, severity in actual)
    tp = len(expected & detected); precision = tp / len(detected) if detected else 1.0; recall = tp / len(expected) if expected else 1.0
    return {"cases": len(cases), "precision": precision, "recall": recall, "f1": f1(precision, recall),
            "critical_recall": critical_detected / critical_expected if critical_expected else 1.0,
            "false_positive_count": len(detected - expected)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("input"); parser.add_argument("--output", required=True)
    args = parser.parse_args(); write_result(args.output, evaluate(load_cases(args.input)))
