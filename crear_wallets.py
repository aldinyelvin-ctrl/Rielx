from pathlib import Path
from xrpl.wallet import Wallet

ENV_FILE = Path(".env")


def entorno_ya_configurado():
    if not ENV_FILE.exists():
        return False

    contenido = ENV_FILE.read_text(encoding="utf-8")

    return (
        "AGENT_A_SEED=" in contenido
        and "AGENT_B_SEED=" in contenido
        and "AGENT_A_ADDRESS=" in contenido
        and "AGENT_B_ADDRESS=" in contenido
    )


if entorno_ya_configurado():
    print("ERROR: .env ya contiene wallets.")
    print("No se crearon nuevas wallets.")
    raise SystemExit(1)


def crear_wallet(nombre):
    wallet = Wallet.create()

    print(f"{nombre} creada")
    print(f"Address: {wallet.classic_address}")

    return wallet


agent_a = crear_wallet("Agent A")
agent_b = crear_wallet("Agent B")

env_content = f"""XRPL_NETWORK=testnet
AGENT_A_SEED={agent_a.seed}
AGENT_A_ADDRESS={agent_a.classic_address}
AGENT_B_SEED={agent_b.seed}
AGENT_B_ADDRESS={agent_b.classic_address}
"""

ENV_FILE.write_text(env_content, encoding="utf-8")

print("Wallets guardadas en .env")
