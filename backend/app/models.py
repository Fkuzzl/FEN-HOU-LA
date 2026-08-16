from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Table, Column, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


event_members = Table(
    "event_members", Base.metadata,
    Column("event_id", ForeignKey("expense_events.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class EventStatus(str, Enum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True, default=lambda: f"user_{uuid4().hex[:10]}")
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    memberships: Mapped[list["GroupMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def is_contact(self) -> bool:
        return self.email.endswith("@contact.local") or self.email.endswith("@contacts.example.com")


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    members: Mapped[list["GroupMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    events: Mapped[list["ExpenseEvent"]] = relationship(back_populates="group")
    participants: Mapped[list["Participant"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    group: Mapped[Group] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    group: Mapped[Group] = relationship(back_populates="participants")
    user: Mapped[User | None] = relationship()


class GroupInvite(Base):
    __tablename__ = "group_invites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExpenseEvent(Base):
    __tablename__ = "expense_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id"), index=True)
    payer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(160), default="未命名消費")
    status: Mapped[EventStatus] = mapped_column(SqlEnum(EventStatus), default=EventStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    group: Mapped[Group] = relationship(back_populates="events")
    bills: Mapped[list["Bill"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    members: Mapped[list[User]] = relationship(secondary=event_members)


class Bill(Base):
    __tablename__ = "bills"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("expense_events.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(160))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    receipt_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    receipt_size: Mapped[int | None] = mapped_column(nullable=True)
    split_method: Mapped[str] = mapped_column(String(20), default="EQUAL")
    split_allocations: Mapped[str | None] = mapped_column(Text, nullable=True)
    event: Mapped[ExpenseEvent] = relationship(back_populates="bills")
    participants: Mapped[list[User]] = relationship(secondary="bill_participants")
    participant_roles: Mapped[list["Participant"]] = relationship(secondary="bill_participant_roles")
    share_confirmations: Mapped[list["BillShareConfirmation"]] = relationship(back_populates="bill", cascade="all, delete-orphan")


class BillShareConfirmation(Base):
    __tablename__ = "bill_share_confirmations"
    bill_id: Mapped[str] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), primary_key=True)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), primary_key=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    bill: Mapped[Bill] = relationship(back_populates="share_confirmations")


class RequestStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BillingRequest(Base):
    __tablename__ = "billing_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    participant_id: Mapped[str | None] = mapped_column(ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("expense_events.id", ondelete="SET NULL"), nullable=True)
    bill_id: Mapped[str | None] = mapped_column(ForeignKey("bills.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    note: Mapped[str] = mapped_column(String(160))
    status: Mapped[RequestStatus] = mapped_column(SqlEnum(RequestStatus), default=RequestStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


bill_participants = Table(
    "bill_participants", Base.metadata,
    Column("bill_id", ForeignKey("bills.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

bill_participant_roles = Table(
    "bill_participant_roles", Base.metadata,
    Column("bill_id", ForeignKey("bills.id", ondelete="CASCADE"), primary_key=True),
    Column("participant_id", ForeignKey("participants.id", ondelete="CASCADE"), primary_key=True),
)
