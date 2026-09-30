"""Modelos de dominio para pagos de Rielx sobre XRPL Testnet."""

from dataclasses import dataclass
from decimal import Decimal
import re

from xrpl.core.addresscodec import is_valid_classic_address
from xrpl.models import IssuedCurrency
from xrpl.models.exceptions import XRPLModelException


_HEX_CURRENCY = re.compile(r"^[A-F0-9]{40}$")
_ASSET_ALIAS = re.compile(r"^[A-Z0-9]{4,20}$")


@dataclass(frozen=True)
class Asset:
    """Un activo de XRPL con su representación canónica para el ledger.

    ``currency`` admite XRP, un código XRPL de tres caracteres, un código
    hexadecimal XRPL de 160 bits o un alias alfanumérico de 4 a 20 caracteres.
    Los alias largos, como ``RLUSD``, se codifican al formato hexadecimal que
    exige XRPL antes de enviar o verificar una transacción.
    """

    currency: str
    issuer: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.currency, str):
            raise ValueError("La moneda debe ser texto")

        currency = self.currency.strip().upper()
        if not currency:
            raise ValueError("La moneda no puede estar vacía")
        object.__setattr__(self, "currency", currency)

        if currency == "XRP":
            if self.issuer is not None:
                raise ValueError("XRP no debe tener issuer")
            return

        if not self.issuer or not is_valid_classic_address(self.issuer):
            raise ValueError("Un activo emitido requiere un issuer XRPL válido")

        if not (
            len(currency) == 3
            or _HEX_CURRENCY.fullmatch(currency)
            or _ASSET_ALIAS.fullmatch(currency)
        ):
            raise ValueError(
                "La moneda emitida debe ser un código XRPL válido o un alias "
                "alfanumérico de 4 a 20 caracteres"
            )

        try:
            IssuedCurrency(currency=self.ledger_currency, issuer=self.issuer)
        except XRPLModelException as exc:
            raise ValueError(f"Moneda emitida inválida: {exc}") from exc

    @property
    def is_xrp(self) -> bool:
        return self.currency == "XRP"

    @property
    def ledger_currency(self) -> str:
        """Devuelve el código de moneda canónico que entiende XRPL."""
        if self.is_xrp or len(self.currency) == 3:
            return self.currency
        if _HEX_CURRENCY.fullmatch(self.currency):
            return self.currency
        return self.currency.encode("ascii").hex().upper().ljust(40, "0")


@dataclass(frozen=True)
class PaymentRequest:
    amount: Decimal
    asset: Asset
    destination: str


@dataclass(frozen=True)
class BalanceRequest:
    address: str
    asset: Asset


@dataclass(frozen=True)
class BalanceResult:
    amount: Decimal
    asset: Asset


@dataclass(frozen=True)
class TrustLineRequest:
    asset: Asset
    limit: Decimal


@dataclass(frozen=True)
class TrustLineResult:
    success: bool
    asset: Asset
    limit: Decimal
    tx_hash: str
    ledger_index: int | None
    transaction_result: str


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    amount: Decimal
    asset: Asset
    destination: str
    tx_hash: str
    ledger_index: int | None
    delivered_amount: Decimal | None
    transaction_result: str


@dataclass(frozen=True)
class PaymentVerificationRequest:
    tx_hash: str
    amount: Decimal
    asset: Asset
    destination: str
    source: str | None = None


@dataclass(frozen=True)
class PaymentVerificationResult:
    verified: bool
    tx_hash: str
    transaction_result: str | None
    ledger_index: int | None
    delivered_amount: Decimal | None
    reason: str | None = None
