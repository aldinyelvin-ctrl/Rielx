import os

from dotenv import load_dotenv
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo

load_dotenv()

NETWORK = os.getenv("XRPL_NETWORK")
AGENT_A_ADDRESS = os.getenv("AGENT_A_ADDRESS")
AGENT_B_ADDRESS = os.getenv("AGENT_B_ADDRESS")

if NETWORK != "testnet":
    raise RuntimeError("Por seguridad, este script solo permite XRPL Testnet")

if not AGENT_A_ADDRESS:
    raise RuntimeError("Falta AGENT_A_ADDRESS")

if not AGENT_B_ADDRESS:
    raise RuntimeError("Falta AGENT_B_ADDRESS")

client = JsonRpcClient("https://s.altnet.rippletest.net:51234")


def consultar_saldo(nombre, address):
    request = AccountInfo(
        account=address,
        ledger_index="validated",
    )

    response = client.request(request)

    if "account_data" not in response.result:
        raise RuntimeError(
            f"No se pudo consultar {nombre}: {response.result}"
        )

    saldo_drops = int(response.result["account_data"]["Balance"])
    saldo_xrp = saldo_drops / 1_000_000

    print(f"{nombre}")
    print(f"Address: {address}")
    print(f"Saldo: {saldo_xrp} XRP")
    print()


consultar_saldo("Agent A", AGENT_A_ADDRESS)
consultar_saldo("Agent B", AGENT_B_ADDRESS)

print("Saldos consultados correctamente")