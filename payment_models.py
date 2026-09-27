from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentRequest:
    amount: Decimal
    asset: str
    destination: str

@dataclass
class BalanceRequest:
    address: str
    asset: str

@dataclass
class BalanceResult:
    amount: Decimal
    asset: str

@dataclass
class PaymentResult:
    success: bool
    amount: Decimal
    asset: str
    destination: str
    tx_hash: str
    ledger_index: int
    delivered_amount: str

@dataclass
class PaymentResult:
    success: bool
    amount: Decimal
    asset: str
    destination: str
    tx_hash: str
    ledger_index: int
    delivered_amount: str