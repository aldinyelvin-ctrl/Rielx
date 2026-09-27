import os

from dotenv import load_dotenv
from xrpl.wallet import Wallet

load_dotenv()

agent_a_seed = os.getenv("AGENT_A_SEED")
agent_a_address = os.getenv("AGENT_A_ADDRESS")

agent_b_seed = os.getenv("AGENT_B_SEED")
agent_b_address = os.getenv("AGENT_B_ADDRESS")

if not agent_a_seed or not agent_a_address:
    raise RuntimeError("Faltan las credenciales de Agent A")

if not agent_b_seed or not agent_b_address:
    raise RuntimeError("Faltan las credenciales de Agent B")

agent_a = Wallet.from_seed(agent_a_seed)
agent_b = Wallet.from_seed(agent_b_seed)

print("Agent A OK")
print(f"Address: {agent_a.classic_address}")

print("Agent B OK")
print(f"Address: {agent_b.classic_address}")

if agent_a.classic_address != agent_a_address:
    raise RuntimeError("La Address de Agent A no coincide con su seed")

if agent_b.classic_address != agent_b_address:
    raise RuntimeError("La Address de Agent B no coincide con su seed")

print("Wallets verificadas correctamente")