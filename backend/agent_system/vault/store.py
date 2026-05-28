"""PII vault write path (task 1.2.7).

store_pii() is the only function that may INSERT/UPDATE pii_vault.
It is called exclusively by the database seeder (db/seed.py) — never
by any agent.

The connection passed in must have INSERT / ON CONFLICT UPDATE privileges
on pii_vault (i.e. a seeder/superuser connection, not a app-role connection).
Caller commits.
"""
from __future__ import annotations

import uuid

import psycopg

from agent_system.vault.crypto import (
    ARGON_PROD,
    ArgonParams,
    encrypt_field,
    hash_secret,
)
from agent_system.vault.kms import get_argon_params, get_field_key, get_pepper


def store_pii(
    conn: psycopg.Connection,
    *,
    customer_id: uuid.UUID,
    ssn: str,
    drivers_license: str | None = None,
    bank_routing: str | None = None,
    bank_account: str | None = None,
    security_answer: str | None = None,
    # Allow test callers to inject fast params or custom keys
    pepper: bytes | None = None,
    argon_params: ArgonParams | None = None,
) -> None:
    """Encrypt/hash PII and upsert into pii_vault.

    SSN and security_answer are Argon2id-hashed (one-way).
    drivers_license, bank_routing, bank_account are AES-256-GCM encrypted
    (recoverable for payout use).
    """
    _pepper = pepper if pepper is not None else get_pepper()
    _params = argon_params if argon_params is not None else get_argon_params()

    ssn_clean = "".join(c for c in ssn if c.isdigit())
    ssn_last4 = ssn_clean[-4:]
    ssn_hash = hash_secret(ssn_clean, _pepper, _params)

    sec_hash: bytes | None = None
    if security_answer is not None:
        # Security answers use Argon2id without a pepper (short-answer
        # keyspace is large enough; the salt provides per-row uniqueness).
        sec_hash = hash_secret(security_answer.strip().casefold(), b"", _params)

    dl_enc: bytes | None = None
    dl_iv: bytes | None = None
    if drivers_license is not None:
        dl_enc, dl_iv = encrypt_field(drivers_license, get_field_key("drivers_license"))

    br_enc: bytes | None = None
    br_iv: bytes | None = None
    if bank_routing is not None:
        br_enc, br_iv = encrypt_field(bank_routing, get_field_key("bank_routing"))

    ba_enc: bytes | None = None
    ba_iv: bytes | None = None
    if bank_account is not None:
        ba_enc, ba_iv = encrypt_field(bank_account, get_field_key("bank_account"))

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pii_vault (
                customer_id,
                ssn_hash, ssn_last4,
                drivers_license_enc, dl_iv,
                bank_routing_enc, br_iv,
                bank_account_enc, ba_iv,
                security_answer_hash
            ) VALUES (
                %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s
            )
            ON CONFLICT (customer_id) DO UPDATE SET
                ssn_hash             = EXCLUDED.ssn_hash,
                ssn_last4            = EXCLUDED.ssn_last4,
                drivers_license_enc  = EXCLUDED.drivers_license_enc,
                dl_iv                = EXCLUDED.dl_iv,
                bank_routing_enc     = EXCLUDED.bank_routing_enc,
                br_iv                = EXCLUDED.br_iv,
                bank_account_enc     = EXCLUDED.bank_account_enc,
                ba_iv                = EXCLUDED.ba_iv,
                security_answer_hash = EXCLUDED.security_answer_hash
            """,
            (
                customer_id,
                ssn_hash,
                ssn_last4,
                dl_enc,
                dl_iv,
                br_enc,
                br_iv,
                ba_enc,
                ba_iv,
                sec_hash,
            ),
        )
