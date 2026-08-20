from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commercial import AIModelPricing, UsageCost
from app.models.tenant import UsageEvent


class UsageCostService:
    """Idempotent provider-cost ledger for UsageEvent rows.

    A cost row freezes the pricing version at event time; later price changes
    therefore never rewrite historical estimates.
    """

    @staticmethod
    def calculate(db: Session, event: UsageEvent) -> UsageCost:
        existing = db.scalar(select(UsageCost).where(UsageCost.usage_event_id == event.id))
        if existing:
            return existing
        pricing = None
        if event.provider and event.model:
            pricing = db.scalar(select(AIModelPricing).where(
                AIModelPricing.provider == event.provider, AIModelPricing.model == event.model,
                AIModelPricing.effective_from <= event.created_at,
                (AIModelPricing.effective_to.is_(None) | (AIModelPricing.effective_to > event.created_at)),
            ).order_by(AIModelPricing.effective_from.desc()))
        quantity = Decimal(event.quantity or 0)
        if pricing:
            if event.usage_type in {"llm_input_tokens", "embedding_tokens"}:
                price = pricing.input_price_per_million_tokens
            elif event.usage_type == "llm_output_tokens":
                price = pricing.output_price_per_million_tokens
            else:
                price = Decimal("0")
            amount = (quantity * Decimal(price or 0) / Decimal(1_000_000)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
            currency = pricing.currency
        else:
            amount, currency = Decimal("0"), "CNY"
        cost = UsageCost(usage_event_id=event.id, pricing_id=pricing.id if pricing else None, estimated_cost=amount,
                         cost_currency=currency, is_estimated=True)
        db.add(cost); db.flush()
        return cost

