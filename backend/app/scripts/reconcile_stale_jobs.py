"""Operational command: mark abandoned in-process jobs failed, never auto-replay."""
from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.job_reconciliation import JobReconciliationService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale-after-minutes", type=int, default=30)
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps(JobReconciliationService.reconcile(db, stale_after_minutes=args.stale_after_minutes), ensure_ascii=False))


if __name__ == "__main__":
    main()
