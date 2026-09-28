from payment_adapter import PaymentAdapter
from payment_models import (
    BalanceRequest,
    BalanceResult,
    PaymentRequest,
    PaymentResult,
)

class PaymentEngine:
    def __init__(self, adapter: PaymentAdapter):
        self.adapter = adapter

        print("Rielx Payment Engine iniciado")

    def get_balance(self, request: BalanceRequest) -> BalanceResult:
        return BalanceResult(
            amount=self.adapter.get_balance(request),
            asset=request.asset,
        )

    def pay(self, request: PaymentRequest) -> PaymentResult:
        if request.amount <= 0:
            raise ValueError("El monto debe ser mayor que cero")

        self.adapter.validate_asset(request.asset)

        self.adapter.validate_destination(request.destination)

        return self.adapter.pay(request)