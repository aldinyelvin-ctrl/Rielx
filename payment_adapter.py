from abc import ABC, abstractmethod

from payment_models import (
    Asset,
    BalanceRequest,
    DefaultRippleRequest,
    DefaultRippleResult,
    PaymentRequest,
    PaymentResult,
    PaymentVerificationRequest,
    PaymentVerificationResult,
    TrustLineRequest,
    TrustLineResult,
)


class PaymentAdapter(ABC):
    @abstractmethod
    def get_balance(self, request: BalanceRequest):
        pass

    @abstractmethod
    def has_trust_line(self, address: str, asset: Asset) -> bool:
        pass

    @abstractmethod
    def validate_destination(self, destination: str) -> None:
        pass

    @abstractmethod
    def validate_asset(self, asset: Asset) -> None:
        pass

    @abstractmethod
    def open_trust_line(
        self, request: TrustLineRequest, *, confirm: bool
    ) -> TrustLineResult:
        pass

    @abstractmethod
    def configure_default_ripple(
        self, request: DefaultRippleRequest, *, confirm: bool
    ) -> DefaultRippleResult:
        pass

    @abstractmethod
    def pay(self, request: PaymentRequest, *, confirm: bool) -> PaymentResult:
        pass

    @abstractmethod
    def verify_payment(
        self, request: PaymentVerificationRequest
    ) -> PaymentVerificationResult:
        pass
