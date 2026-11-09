"""Small fixed data set for tests that must not depend on the 300-loan seed."""
from sqlalchemy import text

from app.db import SessionLocal
from app.models import Branch, Role, User
from app.security import hash_password

PASSWORD = "correct-horse"
PINCODE_A, PINCODE_B = "452010", "452001"

_hash = hash_password(PASSWORD)


async def reset_world() -> dict:
    async with SessionLocal() as s:
        await s.execute(text(
            "TRUNCATE branches, users, borrowers, loans, promises, outcomes, contact_attempts, "
            "loan_notes, messages, call_logs, dpd_snapshots, priority_overrides RESTART IDENTITY CASCADE"
        ))
        a = Branch(name="Branch A", pincodes=[PINCODE_A])
        b = Branch(name="Branch B", pincodes=[PINCODE_B])
        s.add_all([a, b])
        await s.flush()

        def user(name, email, role, branch):
            return User(name=name, email=email, password_hash=_hash, role=role, branch_id=branch.id)

        users = {
            "asha": user("Asha", "asha@t.in", Role.field_officer, a),
            "bala": user("Bala", "bala@t.in", Role.field_officer, a),
            "chitra": user("Chitra", "chitra@t.in", Role.field_officer, b),
            "manager": user("Manager", "manager@t.in", Role.branch_manager, a),
        }
        s.add_all(users.values())
        await s.commit()
        return {k: u.id for k, u in users.items()}

