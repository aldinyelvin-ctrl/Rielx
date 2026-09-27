from payment_adapter import PaymentAdapter
from payment_models import PaymentRequest, PaymentResult

class PaymentEngine:
    def __init__(self, adapter: PaymentAdapter):
        self.adapter = adapter

        print("Rielx Payment Engine iniciado")

    def get_balance(self, address):
        return self.adapter.get_balance(address)

    def pay(self, request: PaymentRequest) -> PaymentResult:
        if request.amount <= 0:
            raise ValueError("El monto debe ser mayor que cero")

        if request.asset != "XRP":
            raise ValueError("Asset no soportado por el Payment Engine")

        self.adapter.validate_destination(request.destination)

        result = self.adapter.pay(
            amount=request.amount,
            asset=request.asset,
            destination=request.destination,
        )

        return PaymentResult(
            success=result.success,
            amount=result.amount,
            asset=result.asset,
            destination=result.destination,
            tx_hash=result.tx_hash,
            ledger_index=result.ledger_index,
            delivered_amount=result.delivered_amount,
        )