from decimal import Decimal
import os
from unittest.mock import patch
import unittest

from payment_models import Asset, BalanceRequest, PaymentVerificationRequest
from xrpl_adapter import XRPLAdapter


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
        with patch.dict(os.environ, {"XRPL_NETWORK": "testnet"}):
            return XRPLAdapter(
                require_signer=False,
                client=FakeClient(*responses),
            )

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
        with patch.dict(os.environ, {"XRPL_NETWORK": "testnet"}):
            with self.assertRaises(ValueError):
                XRPLAdapter(require_signer=False, signer_account="other")

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
                    "TransactionType": "Payment",
                    "Account": ADDRESS,
                    "Destination": ADDRESS,
                    "Amount": issued_amount,
                    "Flags": 0,
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

    def test_partial_payment_is_rejected_even_if_transaction_succeeds(self):
        asset = Asset("XRP")
        adapter = self.make_adapter(
            FakeResponse(
                {
                    "validated": True,
                    "hash": TX_HASH,
                    "TransactionType": "Payment",
                    "Account": ADDRESS,
                    "Destination": ADDRESS,
                    "Amount": "1000",
                    "Flags": 0x00020000,
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
