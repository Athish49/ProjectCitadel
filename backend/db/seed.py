"""
Seed script for SecureClaim AI (task 1.1.5).

Wipes all application data tables and loads 42 deterministic records across
customers, pii_vault, policies, vehicles, claims, evidence, fraud_scores,
and settlements.

Usage:
    uv run python -m db.seed
    make seed

WARNING: TRUNCATES all application data before inserting.
         Do not run against a production database.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal

import psycopg
from faker import Faker

from audit.chain import append_log, verify_chain

ADMIN_DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)

N = 42  # customers / claims

# ── Stage distribution (must sum to N) ──────────────────────────────────────
STAGE_PLAN: list[tuple[str, int]] = [
    ("INTAKE", 5),
    ("IDENTITY_PENDING", 4),
    ("IDENTITY_VERIFIED", 4),
    ("PROCESSING", 7),
    ("DECIDED", 6),
    ("SETTLED", 6),
    ("ESCALATED", 4),
    ("DENIED", 4),
    ("CLOSED", 2),
]
assert sum(n for _, n in STAGE_PLAN) == N, "STAGE_PLAN must sum to N"

STAGES_NEED_FRAUD = frozenset({"DECIDED", "SETTLED", "ESCALATED", "DENIED", "CLOSED"})
STAGES_NEED_SETTLEMENT = frozenset({"SETTLED", "CLOSED"})
STAGES_NEED_EVIDENCE = frozenset({
    "PROCESSING", "DECIDED", "SETTLED", "ESCALATED", "DENIED", "CLOSED"
})

INCIDENT_TYPES = [
    "Collision",
    "Theft",
    "Weather/Natural Disaster",
    "Vandalism",
    "Animal Strike",
    "Fire",
]

MAKES_MODELS = [
    ("Toyota", "Camry"), ("Honda", "Civic"), ("Ford", "F-150"),
    ("Chevrolet", "Silverado"), ("Nissan", "Altima"), ("BMW", "3 Series"),
    ("Mercedes-Benz", "C-Class"), ("Hyundai", "Elantra"), ("Kia", "Optima"),
    ("Subaru", "Outback"), ("Jeep", "Cherokee"), ("Dodge", "Ram 1500"),
    ("Volkswagen", "Jetta"), ("Audi", "A4"), ("Mazda", "CX-5"),
]

POLICY_TYPES = ["COMPREHENSIVE", "COLLISION", "LIABILITY", "FULL_COVERAGE"]
COVERAGE_TYPES = ["BASIC", "STANDARD", "PREMIUM"]


# ── helpers ──────────────────────────────────────────────────────────────────

def _sha256_bytes(text: str) -> bytes:
    return hashlib.sha256(text.encode()).digest()


def _vin(fake: Faker) -> str:
    return fake.lexify(text="?" * 17, letters="ABCDEFGHJKLMNPRSTUVWXYZ0123456789")


def _cents_to_decimal(cents: int) -> Decimal:
    return Decimal(cents) / 100


def _fraud_decision(amount: Decimal) -> str:
    if amount > 40_000:
        return "DENY"
    if amount > 20_000:
        return "FLAG"
    return "CLEAR"


def _risk_score(fake: Faker, decision: str) -> int:
    if decision == "DENY":
        return fake.random_int(min=75, max=100)
    if decision == "FLAG":
        return fake.random_int(min=50, max=74)
    return fake.random_int(min=0, max=49)


# ── core seeding ─────────────────────────────────────────────────────────────

def _truncate_all(cur: psycopg.Cursor) -> None:
    cur.execute(
        """
        TRUNCATE
            complaints, identity_attempts,
            settlements, fraud_scores, evidence,
            claims, vehicles, policies, pii_vault, customers,
            audit_log, security_events, capability_token_log
        RESTART IDENTITY CASCADE
        """
    )


def seed(conn: psycopg.Connection) -> None:
    fake = Faker("en_US")
    Faker.seed(42)

    stages: list[str] = []
    for stage, count in STAGE_PLAN:
        stages.extend([stage] * count)

    customer_ids = [uuid.uuid4() for _ in range(N)]
    policy_ids = [uuid.uuid4() for _ in range(N)]
    vehicle_ids = [uuid.uuid4() for _ in range(N)]
    claim_ids = [uuid.uuid4() for _ in range(N)]

    with conn.cursor() as cur:
        _truncate_all(cur)

        # ── customers + pii_vault ─────────────────────────────────────────
        for i in range(N):
            cid = customer_ids[i]
            pol_num = f"POL-{i + 1:06d}"
            ssn = fake.unique.ssn()
            cur.execute(
                """
                INSERT INTO customers (
                    customer_id, policy_number, first_name, last_name,
                    email, phone, date_of_birth,
                    address_line1, city, state, zip_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cid, pol_num,
                    fake.first_name(), fake.last_name(),
                    fake.unique.email(),
                    fake.numerify(text="+1-###-###-####"),
                    fake.date_of_birth(minimum_age=18, maximum_age=80),
                    fake.street_address()[:200],
                    fake.city()[:100], fake.state_abbr(), fake.zipcode()[:10],
                ),
            )
            security_answer = fake.word() + fake.word()
            cur.execute(
                """
                INSERT INTO pii_vault (
                    customer_id,
                    ssn_hash, ssn_last4,
                    drivers_license_enc, dl_iv,
                    bank_routing_enc, br_iv,
                    bank_account_enc, ba_iv,
                    security_answer_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cid,
                    _sha256_bytes(ssn), ssn[-4:],
                    fake.binary(length=32), fake.binary(length=16),
                    fake.binary(length=32), fake.binary(length=16),
                    fake.binary(length=32), fake.binary(length=16),
                    _sha256_bytes(security_answer),
                ),
            )

        # ── policies ──────────────────────────────────────────────────────
        # Store bind/expiry for date-coherence check when inserting claims.
        policy_window: dict[uuid.UUID, tuple[date, date]] = {}
        for i in range(N):
            pol_num = f"POL-{i + 1:06d}"
            bind_date: date = fake.date_between(start_date="-5y", end_date="-1y")
            expiry_date: date = bind_date + timedelta(days=365)
            policy_window[policy_ids[i]] = (bind_date, expiry_date)
            cur.execute(
                """
                INSERT INTO policies (
                    policy_id, policy_number, customer_id,
                    policy_type, policy_csl, policy_deductible,
                    coverage_type, policy_bind_date, policy_expiry_date,
                    policy_status, auto_approve_limit
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    policy_ids[i], pol_num, customer_ids[i],
                    fake.random_element(POLICY_TYPES),
                    f"{fake.random_int(min=25, max=250)}k/{fake.random_int(min=25, max=500)}k",
                    fake.random_int(min=250, max=2500),
                    fake.random_element(COVERAGE_TYPES),
                    bind_date, expiry_date,
                    "ACTIVE",
                    fake.random_int(min=5000, max=25000),
                ),
            )

        # ── vehicles ──────────────────────────────────────────────────────
        for i in range(N):
            make, model = fake.random_element(MAKES_MODELS)
            cur.execute(
                """
                INSERT INTO vehicles (
                    vehicle_id, customer_id, policy_id,
                    auto_make, auto_model, auto_year, vin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vehicle_ids[i], customer_ids[i], policy_ids[i],
                    make, model,
                    fake.random_int(min=2010, max=2024),
                    _vin(fake),
                ),
            )

        # ── claims + evidence + fraud_scores + settlements ────────────────
        for i in range(N):
            cid = claim_ids[i]
            pid = policy_ids[i]
            stage = stages[i]
            bind_date, expiry_date = policy_window[pid]

            # Date coherence: incident_date strictly within bind–expiry window.
            incident_date: date = fake.date_between(
                start_date=bind_date + timedelta(days=1),
                end_date=expiry_date - timedelta(days=1),
            )
            amount = _cents_to_decimal(fake.random_int(min=50_000, max=4_500_000))

            cur.execute(
                """
                INSERT INTO claims (
                    claim_id, claim_number, customer_id, policy_id,
                    incident_date, incident_type, incident_description,
                    total_claim_amount, claim_stage
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cid, f"CLM-{i + 1:06d}", customer_ids[i], pid,
                    incident_date,
                    fake.random_element(INCIDENT_TYPES),
                    fake.sentence(nb_words=12),
                    amount, stage,
                ),
            )

            # evidence
            if stage in STAGES_NEED_EVIDENCE:
                n_ev = fake.random_int(min=1, max=2)
                for j in range(n_ev):
                    ext = fake.random_element(["jpg", "png", "pdf"])
                    ev_type = "PDF" if ext == "pdf" else "PHOTO"
                    sha_orig = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
                    sha_san = hashlib.sha256((sha_orig + "sanitised").encode()).hexdigest()
                    cur.execute(
                        """
                        INSERT INTO evidence (
                            claim_id, evidence_type, original_filename,
                            sha256_original, sanitised_path, sha256_sanitised,
                            sanitisation_status, extracted_text_label
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            cid, ev_type,
                            f"claim_{i + 1:06d}_doc{j + 1}.{ext}",
                            sha_orig,
                            f"/data/sanitised/{sha_orig[:8]}.{ext}",
                            sha_san,
                            "CLEAN",
                            "UNTRUSTED",
                        ),
                    )

            # fraud_scores
            if stage in STAGES_NEED_FRAUD:
                decision = _fraud_decision(amount)
                score = _risk_score(fake, decision)
                cur.execute(
                    """
                    INSERT INTO fraud_scores (
                        claim_id, risk_score, risk_factors, decision
                    ) VALUES (%s, %s, %s::jsonb, %s)
                    """,
                    (
                        cid, score,
                        json.dumps({
                            "amount_flag": float(amount) > 20_000,
                            "fast_claim": (incident_date - bind_date).days < 30,
                            "repeat_incident": i % 7 == 0,
                        }),
                        decision,
                    ),
                )

            # settlements
            if stage in STAGES_NEED_SETTLEMENT:
                cur.execute(
                    "SELECT policy_deductible, auto_approve_limit FROM policies WHERE policy_id = %s",
                    (pid,),
                )
                row = cur.fetchone()
                deductible = Decimal(str(row[0]))
                auto_limit = row[1]
                offered = max(Decimal("0.00"), amount - deductible)
                approval = "AUTO_APPROVED" if offered <= auto_limit else "HUMAN_APPROVED"
                cur.execute(
                    """
                    INSERT INTO settlements (
                        claim_id, offered_amount, deductible_applied,
                        approval_status, payout_status, payout_reference
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cid, offered, deductible,
                        approval, "PROCESSED",
                        f"PAY-{uuid.uuid4().hex[:12].upper()}",
                    ),
                )

    # Audit chain: one summary entry after all INSERTs, then commit together.
    append_log(
        conn,
        agent_id="seed",
        action="seed_loaded",
        target="all_tables",
        data_label="CONFIDENTIAL",
        details={"n_customers": N, "n_claims": N, "stages": dict(STAGE_PLAN)},
    )
    conn.commit()


def _print_counts(conn: psycopg.Connection) -> None:
    tables = [
        "customers", "pii_vault", "policies", "vehicles",
        "claims", "evidence", "fraud_scores", "settlements",
    ]
    with conn.cursor() as cur:
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")  # noqa: S608 — admin script, not user input
            print(f"  {t:<16}: {cur.fetchone()[0]}")


def main() -> None:
    dsn = ADMIN_DSN
    print(f"db/seed: connecting to {dsn.split('@')[-1]}")
    print("WARNING: truncating all application data tables.")
    with psycopg.connect(dsn, autocommit=False) as conn:
        seed(conn)
        _print_counts(conn)
        broken = verify_chain(conn)
        if broken:
            print(f"db/seed: CHAIN BROKEN after seed — {broken}", file=sys.stderr)
            sys.exit(1)
        print("  audit chain     : OK")
    print("db/seed: done")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"db/seed: fatal — {exc}", file=sys.stderr)
        sys.exit(1)
