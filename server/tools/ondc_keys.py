"""Generate ONDC key pairs for Santosh's buyer app and print them as .env lines.

    python tools/ondc_keys.py >> .env

Register BAZAR_ONDC_SIGNING_PUBLIC_KEY and BAZAR_ONDC_ENCRYPTION_PUBLIC_KEY on the ONDC portal. Keep the private keys
only in the server's .env.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.bazar.commerce.ondc.crypto import generate_keys  # noqa: E402

k = generate_keys()
print(f"BAZAR_ONDC_SIGNING_PRIVATE_KEY={k.signing_private}")
print(f"BAZAR_ONDC_SIGNING_PUBLIC_KEY={k.signing_public}")
print(f"BAZAR_ONDC_ENCRYPTION_PRIVATE_KEY={k.encryption_private}")
print(f"BAZAR_ONDC_ENCRYPTION_PUBLIC_KEY={k.encryption_public}")
