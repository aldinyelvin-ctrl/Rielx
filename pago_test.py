import os

from dotenv import load_dotenv
from xrpl.clients import JsonRpcClient
from xrpl.models import Payment
from xrpl.transaction import submit_and_wait
from xrpl.wallet import Wallet

load_dotenv()

NETWORK = os.getenv("XRPL_NETWORK")
AGENT_A_SEED = os.getenv("AGENT_A_SEED")
AGENT_A_ADDRESS = os.getenv("AGENT_A_ADDRESS")
AGENT_B_ADDRESS = os.getenv("AGENT_B_ADDRESS")

if NETWORK != "testnet":
    raise RuntimeError("Por seguridad, este script solo permite XRPL Testnet")

if not AGENT_A_SEED:
    raise RuntimeError("Falta AGENT_A_SEED")

if not AGENT_A_ADDRESS:
    raise RuntimeError("Falta AGENT_A_ADDRESS")

if not AGENT_B_ADDRESS:
    raise RuntimeError("Falta AGENT_B_ADDRESS")

client = JsonRpcClient("https://s.altnet.rippletest.net:51234")

wallet_a = Wallet.from_seed(AGENT_A_SEED)

if wallet_a.classic_address != AGENT_A_ADDRESS:
    raise RuntimeError("La seed de Agent A no coincide con su address")

payment = Payment(
    account=AGENT_A_ADDRESS,
    destination=AGENT_B_ADDRESS,
    amount="1000",
)

print("Pago preparado")
print("Red: XRPL Testnet")
print(f"Origen: {AGENT_A_ADDRESS}")
print(f"Destino: {AGENT_B_ADDRESS}")
print("Cantidad: 0.001 XRP")