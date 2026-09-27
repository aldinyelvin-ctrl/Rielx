from dataclasses import dataclass


@dataclass
class PaymentRequest:
    amount: float
    asset: str
    destination: str


@dataclass
class PaymentResult:
    success: bool
    amount: float
    asset: str
    destination: str
    tx_hash: str
    ledger_index: int
    delivered_amount: str