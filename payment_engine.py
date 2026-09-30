from decimal import Decimal

from payment_adapter import PaymentAdapter
from payment_models import (
    Asset,
    BalanceRequest,
    BalanceResult,
    PaymentRequest,
    PaymentResult,
    PaymentVerificationRequest,
    PaymentVerificationResult,
    TrustLineRequest,
    TrustLineResult,
)


class PaymentEngine:
    """Reglas de dominio comunes antes de delegar en un ledger adapter."""

    def __init__(self, adapter: PaymentAdapter):
        self.adapter = adapter

    @staticmethod
    def _validate_positive_amount(amount: Decimal, label: str) -> None:
        if not isinstance(amount, Decimal):
            raise TypeError(f"{label} debe ser Decimal para evitar redondeos")
        if not amount.is_finite() or amount <= 0:
            raise ValueError(f"{label} debe ser un Decimal positivo y finito")

    def get_balance(self, request: BalanceRequest) -> BalanceResult:
        self.adapter.validate_asset(request.asset)
        self.adapter.validate_destination(request.address)
        return BalanceResult(
            amount=self.adapter.get_balance(request),
            asset=request.asset,
        )

    def has_trust_line(self, address: str, asset: Asset) -> bool:
        self.adapter.validate_asset(asset)
        self.adapter.validate_destination(address)
        if asset.is_xrp:
            return False
        return self.adapter.has_trust_line(address, asset)

    def open_trust_line(
        self, request: TrustLineRequest, *, confirm: bool = False
    ) -> TrustLineResult:
        if request.asset.is_xrp:
            raise ValueError("XRP no utiliza trust lines")
        self._validate_positive_amount(request.limit, "El límite de trust line")
        self.adapter.validate_asset(request.asset)
        if not confirm:
            raise PermissionError(
                "Abrir una trust line requiere confirm=True explícito"
            )
        return self.adapter.open_trust_line(request, confirm=confirm)

    def pay(
        self, request: PaymentRequest, *, confirm: bool = False
    ) -> PaymentResult:
        self._validate_positive_amount(request.amount, "El monto")
        self.adapter.validate_asset(request.asset)
        self.adapter.validate_destination(request.destination)
        if not confirm:
            raise PermissionError(
                "Enviar un pago requiere confirm=True explícito"
            )
        return self.adapter.pay(request, confirm=confirm)

    def verify_payment(
        self, request: PaymentVerificationRequest
    ) -> PaymentVerificationResult:
        self._validate_positive_amount(request.amount, "El monto esperado")
        self.adapter.validate_asset(request.asset)
        self.adapter.validate_destination(request.destination)
        if request.source is not None:
            self.adapter.validate_destination(request.source)
        return self.adapter.verify_payment(request)
