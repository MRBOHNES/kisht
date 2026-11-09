import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY, Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Role(enum.StrEnum):
    field_officer = "field_officer"
    branch_manager = "branch_manager"


class LoanStatus(enum.StrEnum):
    active = "active"
    paused_dispute = "paused_dispute"
    cured = "cured"


class PromiseStatus(enum.StrEnum):
    open = "open"
    kept = "kept"
    broken = "broken"


class OutcomeKind(enum.StrEnum):
    paid = "paid"
    promise = "promise"
    not_reachable = "not_reachable"
    dispute = "dispute"


class ContactType(enum.StrEnum):
    call = "call"
    visit = "visit"


class NoteKind(enum.StrEnum):
    note = "note"
    instruction = "instruction"


class MessageDirection(enum.StrEnum):
    out = "out"
    in_ = "in"


class MessageStatus(enum.StrEnum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    blocked = "blocked"


class CallResult(enum.StrEnum):
    connected = "connected"
    no_answer = "no_answer"
    switched_off = "switched_off"


def pg_enum(cls):
    return Enum(cls, name=cls.__name__.lower(), values_callable=lambda e: [m.value for m in e])


def now_col():
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    pincodes: Mapped[list[str]] = mapped_column(ARRAY(String(6)))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(pg_enum(Role))
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Borrower(Base):
    __tablename__ = "borrowers"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(120))
    business_type: Mapped[str] = mapped_column(String(40))
    phone: Mapped[str] = mapped_column(String(15))
    pincode: Mapped[str] = mapped_column(String(6))
    # assumption: address is not in the brief CSV
    address: Mapped[str] = mapped_column(Text)


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (Index("ix_loans_officer_status", "officer_id", "status"),)

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("borrowers.id"))
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    outstanding: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    emi: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    dpd: Mapped[int] = mapped_column(Integer)
    last_payment_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[LoanStatus] = mapped_column(pg_enum(LoanStatus), default=LoanStatus.active)
    imported_at: Mapped[datetime] = now_col()


class Promise(Base):
    __tablename__ = "promises"

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    promised_date: Mapped[date] = mapped_column(Date)
    status: Mapped[PromiseStatus] = mapped_column(pg_enum(PromiseStatus), default=PromiseStatus.open)
    broken_reason: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = now_col()


class Outcome(Base):
    __tablename__ = "outcomes"

    # generated on the phone; doubles as the idempotency key for /sync
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[OutcomeKind] = mapped_column(pg_enum(OutcomeKind))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    promise_date: Mapped[date | None] = mapped_column(Date)
    promise_id: Mapped[int | None] = mapped_column(ForeignKey("promises.id"))
    reason_tag: Mapped[str | None] = mapped_column(String(40))
    client_said: Mapped[str | None] = mapped_column(Text)
    next_followup_date: Mapped[date | None] = mapped_column(Date)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    logged_at_device: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = now_col()
    out_of_window_flag: Mapped[bool] = mapped_column(Boolean, default=False)


class ContactAttempt(Base):
    __tablename__ = "contact_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[ContactType] = mapped_column(pg_enum(ContactType))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    allowed: Mapped[bool] = mapped_column(Boolean)
    blocked_reason: Mapped[str | None] = mapped_column(String(120))


class LoanNote(Base):
    __tablename__ = "loan_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author_role: Mapped[Role] = mapped_column(pg_enum(Role))
    kind: Mapped[NoteKind] = mapped_column(pg_enum(NoteKind))
    text: Mapped[str] = mapped_column(Text)
    outcome_tag: Mapped[str | None] = mapped_column(String(40))
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_reason: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = now_col()


class Message(Base):
    """Mock channel: nothing is actually sent."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    template_key: Mapped[str | None] = mapped_column(String(40))
    rendered_text: Mapped[str] = mapped_column(Text)
    direction: Mapped[MessageDirection] = mapped_column(pg_enum(MessageDirection))
    status: Mapped[MessageStatus] = mapped_column(pg_enum(MessageStatus))
    blocked_reason: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = now_col()


class CallLog(Base):
    """recording_url points at a sample audio file."""
    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[int] = mapped_column(Integer)
    result: Mapped[CallResult] = mapped_column(pg_enum(CallResult))
    recording_url: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)


class DpdSnapshot(Base):
    __tablename__ = "dpd_snapshots"

    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"), primary_key=True)
    month: Mapped[date] = mapped_column(Date, primary_key=True)
    dpd: Mapped[int] = mapped_column(Integer)


class PriorityOverride(Base):
    __tablename__ = "priority_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = now_col()
