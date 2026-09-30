from decimal import Decimal
import unittest

from payment_adapter import PaymentAdapter
from payment_engine import PaymentEngine
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


ISSUER = "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn"
ADDRESS = "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn"


class RecordingAdapter(PaymentAdapter):
    def __init__(self):
        self.pay_calls = []
        self.trust_line_calls = []
        self.default_ripple_calls = []

    def get_balance(self, request):
        return Decimal("7.5")

    def has_trust_line(self, address, asset):
        return True

    def validate_destination(self, destination):
        if destination != ADDRESS:
            raise ValueError("invalid address")

    def validate_asset(self, asset):
        if not isinstance(asset, Asset):
            raise TypeError("invalid asset")

    def open_trust_line(self, request, *, confirm):
        self.trust_line_calls.append((request, confirm))
        return TrustLineResult(
            success=True,
            asset=request.asset,
            limit=request.limit,
            tx_hash="A" * 64,
            ledger_index=12,
            transaction_result="tesSUCCESS",
        )

    def configure_default_ripple(self, request, *, confirm):
        self.default_ripple_calls.append((request, confirm))
        return DefaultRippleResult(
            success=True,
            enabled=request.enabled,
            tx_hash="D" * 64,
            ledger_index=12,
            transaction_result="tesSUCCESS",
        )

    def pay(self, request, *, confirm):
        self.pay_calls.append((request, confirm))
        return PaymentResult(
            success=True,
            amount=request.amount,
            asset=request.asset,
            destination=request.destination,
            tx_hash="A" * 64,
            ledger_index=12,
            delivered_amount=request.amount,
            transaction_result="tesSUCCESS",
        )

    def verify_payment(self, request):
        return PaymentVerificationResult(
            verified=True,
            tx_hash=request.tx_hash,
            transaction_result="tesSUCCESS",
            ledger_index=12,
            delivered_amount=request.amount,
        )


class AssetTests(unittest.TestCase):
    def test_rlusd_alias_uses_xrpl_hex_currency(self):
        asset = Asset("rlusd", issuer=ISSUER)
        self.assertEqual(asset.currency, "RLUSD")
        self.assertEqual(
            asset.ledger_currency,
            "524C555344000000000000000000000000000000",
        )

    def test_xrp_cannot_have_an_issuer(self):
        with self.assertRaises(ValueError):
            Asset("XRP", issuer=ISSUER)

    def test_issued_asset_requires_a_valid_issuer(self):
        with self.assertRaises(ValueError):
            Asset("RLUSD")


class PaymentEngineTests(unittest.TestCase):
    def setUp(self):
        self.adapter = RecordingAdapter()
        self.engine = PaymentEngine(self.adapter)
        self.xrp = Asset("XRP")
        self.rlusd = Asset("RLUSD", issuer=ISSUER)

    def test_balance_is_returned_with_its_asset(self):
        result = self.engine.get_balance(BalanceRequest(ADDRESS, self.xrp))
        self.assertEqual(result.amount, Decimal("7.5"))
        self.assertEqual(result.asset, self.xrp)

    def test_payment_requires_explicit_confirmation(self):
        request = PaymentRequest(Decimal("1"), self.xrp, ADDRESS)
        with self.assertRaises(PermissionError):
            self.engine.pay(request)
        self.assertEqual(self.adapter.pay_calls, [])

    def test_confirmed_payment_is_delegated(self):
        request = PaymentRequest(Decimal("1"), self.xrp, ADDRESS)
        result = self.engine.pay(request, confirm=True)
        self.assertTrue(result.success)
        self.assertEqual(self.adapter.pay_calls, [(request, True)])

    def test_trust_line_rejects_xrp_and_requires_confirmation(self):
        with self.assertRaises(ValueError):
            self.engine.open_trust_line(
                TrustLineRequest(self.xrp, Decimal("1")), confirm=True
            )
        with self.assertRaises(PermissionError):
            self.engine.open_trust_line(
                TrustLineRequest(self.rlusd, Decimal("1"))
            )
        self.assertEqual(self.adapter.trust_line_calls, [])

    def test_default_ripple_requires_explicit_confirmation(self):
        request = DefaultRippleRequest()
        with self.assertRaises(PermissionError):
            self.engine.configure_default_ripple(request)
        self.assertEqual(self.adapter.default_ripple_calls, [])

    def test_confirmed_default_ripple_is_delegated(self):
        request = DefaultRippleRequest(enabled=False)
        result = self.engine.configure_default_ripple(request, confirm=True)
        self.assertTrue(result.success)
        self.assertFalse(result.enabled)
        self.assertEqual(self.adapter.default_ripple_calls, [(request, True)])

    def test_verification_is_delegated_without_a_signing_action(self):
        request = PaymentVerificationRequest(
            tx_hash="B" * 64,
            amount=Decimal("1"),
            asset=self.xrp,
            destination=ADDRESS,
        )
        self.assertTrue(self.engine.verify_payment(request).verified)


if __name__ == "__main__":
    unittest.main()
