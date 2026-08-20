from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
import secrets


@dataclass(frozen=True)
class PaymentResult:
    status: str
    external_payment_id: str
    error_code: str | None = None
    error_message: str | None = None


class PaymentProvider(ABC):
    """Provider boundary. Real gateways can be added without changing orders."""

    @abstractmethod
    def create_payment(self, *, order_number: str, amount: Decimal, currency: str, request_id: str) -> PaymentResult: ...

    @abstractmethod
    def query_payment(self, external_payment_id: str) -> PaymentResult: ...

    @abstractmethod
    def cancel_payment(self, external_payment_id: str) -> PaymentResult: ...

    def handle_webhook(self, payload: dict) -> PaymentResult:
        raise NotImplementedError("该 Provider 未实现公网 webhook")


class MockPaymentProvider(PaymentProvider):
    def __init__(self, *, succeed: bool = True) -> None:
        self.succeed = succeed

    def create_payment(self, *, order_number: str, amount: Decimal, currency: str, request_id: str) -> PaymentResult:
        if self.succeed:
            return PaymentResult("succeeded", f"mock_{secrets.token_hex(8)}")
        return PaymentResult("failed", f"mock_{secrets.token_hex(8)}", "MOCK_FAILED", "模拟支付失败")

    def query_payment(self, external_payment_id: str) -> PaymentResult:
        return PaymentResult("succeeded", external_payment_id)

    def cancel_payment(self, external_payment_id: str) -> PaymentResult:
        return PaymentResult("cancelled", external_payment_id)

