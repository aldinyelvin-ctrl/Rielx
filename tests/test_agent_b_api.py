from decimal import Decimal
import unittest

from agent_b_api import PAYMENT_HEADER, create_agent_b_app
from payment_models import (
    Asset,
    PaymentRequest,
    PaymentVerificationResult,
)


ISSUER = "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn"
DESTINATION = "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn"
SOURCE = "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn"
TX_HASH = "A" * 64


class FakeEngine:
    def __init__(self, verified=True):
        self.verified = verified
        self.requests = []

    def verify_payment(self, request):
        self.requests.append(request)
        return PaymentVerificationResult(
            verified=self.verified,
            tx_hash=request.tx_hash,
            transaction_result="tesSUCCESS" if self.verified else "tecPATH_DRY",
            ledger_index=123 if self.verified else None,
            delivered_amount=request.amount if self.verified else None,
            reason=None if self.verified else "El pago no fue aceptado",
        )


class AgentBApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = FakeEngine()
        self.payment = PaymentRequest(
            amount=Decimal("2.5"),
            asset=Asset("RLUSD", issuer=ISSUER),
            destination=DESTINATION,
        )
        self.client = create_agent_b_app(
            self.engine,
            self.payment,
            expected_source=SOURCE,
        ).test_client()

    def test_missing_payment_returns_machine_readable_402_terms(self):
        response = self.client.get("/resource")
        self.assertEqual(response.status_code, 402)
        body = response.get_json()
        self.assertEqual(body["error"], "payment_required")
        self.assertEqual(body["payment"]["asset"]["currency"], "RLUSD")
        self.assertEqual(body["payment"]["network"], "XRPL Testnet")

    def test_verified_payment_grants_the_resource_once(self):
        response = self.client.get(
            "/resource", headers={PAYMENT_HEADER: TX_HASH.lower()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "payment_verified")
        self.assertEqual(self.engine.requests[0].source, SOURCE)

        replay = self.client.get(
            "/resource", headers={PAYMENT_HEADER: TX_HASH}
        )
        self.assertEqual(replay.status_code, 409)

    def test_unverified_payment_returns_402(self):
        client = create_agent_b_app(
            FakeEngine(verified=False), self.payment
        ).test_client()
        response = client.get("/resource", headers={PAYMENT_HEADER: TX_HASH})
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.get_json()["error"], "payment_required")


if __name__ == "__main__":
    unittest.main()
