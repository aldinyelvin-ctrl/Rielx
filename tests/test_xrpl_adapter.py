from decimal import Decimal
import os
from unittest.mock import MagicMock, patch
import unittest

from payment_models import (
    Asset,
    BalanceRequest,
    DefaultRippleRequest,
    PaymentVerificationRequest,
)
from xrpl_adapter import AccountSet, AccountSetAsfFlag, XRPLAdapter


ISSUER = "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn"
ADDRESS = "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn"
TX_HASH = "C" * 64


class FakeResponse:
    def __init__(self, result, successful=True):
        self.result = result
        self.successful = successful

    def is_successful(self):
        return self.successful


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


class XRPLAdapterTests(unittest.TestCase):
    def make_adapter(self, *responses):
        with (
            patch.dict(os.environ, {"XRPL_NETWORK": "testnet"}),
            patch("xrpl_adapter.load_dotenv"),
        ):
            return XRPLAdapter(require_signer=False, client=FakeClient(*responses))

    def test_issued_asset_balance_and_trust_line_are_read_from_account_lines(self):
        asset = Asset("RLUSD", issuer=ISSUER)
        response = FakeResponse(
            {
                "lines": [
                    {
                        "account": ISSUER,
                        "currency": asset.ledger_currency,
                        "balance": "12.34",
                        "limit": "100",
                    }
                ]
            }
        )
        adapter = self.make_adapter(response, response)

        self.assertEqual(
            adapter.get_balance(BalanceRequest(ADDRESS, asset)), Decimal("12.34")
        )
        self.assertTrue(adapter.has_trust_line(ADDRESS, asset))

    def test_xrp_amount_must_be_whole_drops(self):
        adapter = self.make_adapter()
        self.assertEqual(adapter._to_xrpl_amount(Decimal("0.001"), Asset("XRP")), "1000")
        with self.assertRaises(ValueError):
            adapter._to_xrpl_amount(Decimal("0.0000001"), Asset("XRP"))

    def test_signer_must_be_agent_a_or_agent_b(self):
        with (
            patch.dict(os.environ, {"XRPL_NETWORK": "testnet"}),
            patch("xrpl_adapter.load_dotenv"),
        ):
            with self.assertRaises(ValueError):
                XRPLAdapter(require_signer=False, signer_account="other")

    @patch("xrpl_adapter.submit_and_wait")
    @patch("xrpl_adapter.autofill_and_sign")
    @patch("xrpl_adapter.Wallet.from_seed")
    @patch("xrpl_adapter.load_dotenv")
    def test_default_ripple_uses_an_issuer_account_set(
        self, load_dotenv, wallet_from_seed, autofill, submit
    ):
        wallet = MagicMock()
        wallet.classic_address = ISSUER
        wallet_from_seed.return_value = wallet
        signed = object()
        autofill.return_value = signed
        submit.return_value = FakeResponse(
            {
                "hash": TX_HASH,
                "ledger_index": 123,
                "meta": {"TransactionResult": "tesSUCCESS"},
            }
        )

        with patch.dict(
            os.environ,
            {
                "XRPL_NETWORK": "testnet",
                "ISSUER_SEED": "test-only-seed",
                "ISSUER_ADDRESS": ISSUER,
            },
            clear=True,
        ):
            adapter = XRPLAdapter(signer_account="issuer", client=FakeClient())
            result = adapter.configure_default_ripple(
                DefaultRippleRequest(), confirm=True
            )

        self.assertTrue(result.success)
        self.assertTrue(result.enabled)
        self.assertEqual(result.tx_hash, TX_HASH)
        transaction = autofill.call_args.args[0]
        self.assertIsInstance(transaction, AccountSet)
        self.assertEqual(transaction.account, ISSUER)
        self.assertEqual(
            transaction.set_flag, AccountSetAsfFlag.ASF_DEFAULT_RIPPLE
        )
        self.assertIsNone(transaction.clear_flag)
        submit.assert_called_once_with(signed, adapter.client)

    def test_default_ripple_rejects_a_non_issuer_signer(self):
        adapter = self.make_adapter()
        with self.assertRaises(PermissionError):
            adapter.configure_default_ripple(DefaultRippleRequest(), confirm=False)

        adapter.wallet = object()
        adapter.signer_address = ADDRESS
        with self.assertRaisesRegex(RuntimeError, "signer_account='issuer'"):
            adapter.configure_default_ripple(DefaultRippleRequest(), confirm=True)

    def test_verification_requires_the_exact_validated_issued_payment(self):
        asset = Asset("RLUSD", issuer=ISSUER)
        amount = Decimal("2.5")
        issued_amount = {
            "currency": asset.ledger_currency,
            "issuer": ISSUER,
            "value": "2.5",
        }
        adapter = self.make_adapter(
            FakeResponse(
                {
                    "validated": True,
                    "hash": TX_HASH,
                    "tx_json": {
                        "TransactionType": "Payment",
                        "Account": ADDRESS,
                        "Destination": ADDRESS,
                        "Amount": issued_amount,
                        "Flags": 0,
                    },
                    "ledger_index": 123,
                    "meta": {
                        "TransactionResult": "tesSUCCESS",
                        "delivered_amount": issued_amount,
                    },
                }
            )
        )

        result = adapter.verify_payment(
            PaymentVerificationRequest(
                tx_hash=TX_HASH,
                amount=amount,
                asset=asset,
                destination=ADDRESS,
                source=ADDRESS,
            )
        )

        self.assertTrue(result.verified)
        self.assertEqual(result.delivered_amount, amount)

    def test_verification_uses_deliver_max_when_amount_is_absent(self):
        asset = Asset("XRP")
        adapter = self.make_adapter(
            FakeResponse(
                {
                    "validated": True,
                    "hash": TX_HASH,
                    "tx_json": {
                        "TransactionType": "Payment",
                        "Account": ADDRESS,
                        "Destination": ADDRESS,
                        "DeliverMax": "1000",
                        "Flags": 0,
                    },
                    "ledger_index": 123,
                    "meta": {
                        "TransactionResult": "tesSUCCESS",
                        "delivered_amount": "1000",
                    },
                }
            )
        )

        result = adapter.verify_payment(
            PaymentVerificationRequest(
                tx_hash=TX_HASH,
                amount=Decimal("0.001"),
                asset=asset,
                destination=ADDRESS,
                source=ADDRESS,
            )
        )

        self.assertTrue(result.verified)
        self.assertEqual(result.delivered_amount, Decimal("0.001"))

    def test_partial_payment_is_rejected_even_if_transaction_succeeds(self):
        asset = Asset("XRP")
        adapter = self.make_adapter(
            FakeResponse(
                {
                    "validated": True,
                    "hash": TX_HASH,
                    "tx_json": {
                        "TransactionType": "Payment",
                        "Account": ADDRESS,
                        "Destination": ADDRESS,
                        "Amount": "1000",
                        "Flags": 0x00020000,
                    },
                    "ledger_index": 123,
                    "meta": {
                        "TransactionResult": "tesSUCCESS",
                        "delivered_amount": "1000",
                    },
                }
            )
        )

        result = adapter.verify_payment(
            PaymentVerificationRequest(
                tx_hash=TX_HASH,
                amount=Decimal("0.001"),
                asset=asset,
                destination=ADDRESS,
            )
        )

        self.assertFalse(result.verified)
        self.assertEqual(result.reason, "No se aceptan pagos parciales")


if __name__ == "__main__":
    unittest.main()
