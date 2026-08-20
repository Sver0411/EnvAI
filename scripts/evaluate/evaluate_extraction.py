#!/usr/bin/env python3
"""Evaluate structured extraction exports; inputs must be expert-verified JSON."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation

from common import f1, load_cases, write_result


ENTITY_FIELDS = ("products", "equipment", "raw_materials", "environmental_facilities")


def _key(item: dict) -> str:
    return str(item.get("name") or item.get("entity_key") or "").strip().lower()


def _number(value) -> str:
    try: return format(Decimal(str(value)).normalize(), "f")
    except (InvalidOperation, ValueError): return str(value or "").strip()


def evaluate(cases: list[dict]) -> dict:
    expected_entities: set[tuple[str, str]] = set(); actual_entities: set[tuple[str, str]] = set()
    numbers_total = numbers_correct = units_total = units_correct = unsupported = 0
    identity_total = identity_correct = 0
    for case in cases:
        truth, prediction = case["ground_truth"], case["prediction"]
        identity_total += 1; identity_correct += int(truth.get("company_name") == prediction.get("company_name"))
        for field in ENTITY_FIELDS:
            expected = {_key(item): item for item in truth.get(field, []) if _key(item)}
            actual = {_key(item): item for item in prediction.get(field, []) if _key(item)}
            expected_entities.update((field, key) for key in expected); actual_entities.update((field, key) for key in actual)
            for key, expected_item in expected.items():
                actual_item = actual.get(key)
                if not actual_item: continue
                for number_field in ("annual_usage", "max_storage", "quantity", "annual_capacity", "capacity"):
                    if expected_item.get(number_field) is not None:
                        numbers_total += 1; numbers_correct += int(_number(expected_item.get(number_field)) == _number(actual_item.get(number_field)))
                for unit_field in ("unit", "annual_usage_unit", "storage_unit"):
                    if expected_item.get(unit_field):
                        units_total += 1; units_correct += int(str(expected_item.get(unit_field)) == str(actual_item.get(unit_field)))
            unsupported += len(set(actual) - set(expected))
    true_positive = len(expected_entities & actual_entities)
    precision = true_positive / len(actual_entities) if actual_entities else 1.0
    recall = true_positive / len(expected_entities) if expected_entities else 1.0
    return {"cases": len(cases), "entity_precision": precision, "entity_recall": recall, "entity_f1": f1(precision, recall),
            "company_identity_accuracy": identity_correct / identity_total if identity_total else 1.0,
            "numeric_exact_match": numbers_correct / numbers_total if numbers_total else 1.0,
            "unit_accuracy": units_correct / units_total if units_total else 1.0,
            "unsupported_extracted_fact_count": unsupported}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("input"); parser.add_argument("--output", required=True)
    args = parser.parse_args(); write_result(args.output, evaluate(load_cases(args.input)))
