#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


RUNNERS = {
    "extraction": "evaluate_extraction.py",
    "retrieval": "evaluate_retrieval.py",
    "generation": "evaluate_generation.py",
    "review": "evaluate_review.py",
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--dataset", default="evaluation/acceptance/rc1"); parser.add_argument("--output", default="evaluation/results/rc1")
    args = parser.parse_args(); dataset, output = Path(args.dataset), Path(args.output); output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).parent
    for name, runner in RUNNERS.items():
        source = dataset / f"{name}_cases.synthetic.json"
        subprocess.run([sys.executable, str(root / runner), str(source), "--output", str(output / f"{name}.json")], check=True)
    print(f"RC1 evaluation results written to {output}")
