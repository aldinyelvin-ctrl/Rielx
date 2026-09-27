import os
from decimal import Decimal

from dotenv import load_dotenv
from payment_adapter import PaymentAdapter
from payment_models import PaymentResult
from xrpl.models import Payment
from xrpl.transaction import submit_and_wait, autofill_and_sign
from xrpl.wallet import Wallet
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import ServerInfo
from xrpl.models.requests import AccountInfo

class XRPLAdapter(PaymentAdapter):
    def __init__(self):
        load_dotenv()

        self.agent_a_seed = os.getenv("AGENT_A_SEED")
        self.agent_a_address = os.getenv("AGENT_A_ADDRESS")

        if not self.agent_a_seed:
            raise RuntimeError("AGENT_A_SEED no configurada")

        if not self.agent_a_address:
            raise RuntimeError("AGENT_A_ADDRESS no configurada")

        wallet = Wallet.from_seed(self.agent_a_seed)

        if wallet.classic_address != self.agent_a_address:
            raise RuntimeError(
                "La seed de Agent A no corresponde a AGENT_A_ADDRESS"
            )

        self.wallet = wallet

        self.client = JsonRpcClient(
            "https://s.altnet.rippletest.net:51234"
        )

        print("XRPL Adapter iniciado")

    def test_connection(self):
        response = self.client.request(ServerInfo())

        if response.is_successful():
            print("Conexion XRPL Testnet OK")
            return True

        print("Error de conexion XRPL")
        print(response.result)
        return False

    def get_balance(self, address):
        request = AccountInfo(
            account=address,
            ledger_index="validated",
        )

        response = self.client.request(request)

        if not response.is_successful():
            raise RuntimeError(
                f"Error consultando saldo: {response.result}"
            )

        balance_drops = int(
            response.result["account_data"]["Balance"]
        )

        return balance_drops / 1_000_000

    def pay(self, amount, asset, destination):
        if asset != "XRP":
            raise ValueError(
                "El XRPL Adapter actualmente solo soporta XRP"
            )

        amount_drops = int(Decimal(str(amount)) * 1_000_000)

        payment = Payment(
            account=self.agent_a_address,
            destination=destination,
            amount=str(amount_drops),
        )

        signed = autofill_and_sign(
            payment,
            self.client,
            self.wallet,
        )

        print("Payment XRPL firmado localmente")

        result = submit_and_wait(
            signed,
            self.client,
        )

        print("Transaccion enviada y confirmada")

        return PaymentResult(
            success=result.is_successful(),
            amount=amount,
            asset=asset,
            destination=destination,
            tx_hash=result.result["hash"],
            ledger_index=result.result["ledger_index"],
            delivered_amount=result.result["meta"]["delivered_amount"],
        )


if __name__ == "__main__":
    adapter = XRPLAdapter()
    adapter.test_connection()
