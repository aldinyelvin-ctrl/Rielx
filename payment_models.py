from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Asset:
    currency: str
    issuer: str | None = None


@dataclass
class PaymentRequest:
    amount: Decimal
    asset: Asset
    destination: str


@dataclass
class BalanceRequest:
    address: str
    asset: Asset


@dataclass
class BalanceResult:
    amount: Decimal
    asset: Asset

@dataclass
class PaymentResult:
    success: bool
    amount: Decimal
    asset: Asset
    destination: str
    tx_hash: str
    ledger_index: int
    delivered_amount: str