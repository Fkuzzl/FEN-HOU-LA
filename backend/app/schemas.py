from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import EventStatus, RequestStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    name: str
    email: EmailStr
    is_admin: bool = False
    is_disabled: bool = False


class AdminSummaryOut(BaseModel):
    users: int
    groups: int
    active_groups: int
    events: int
    billing_requests: int
    audit_entries: int


class AdminUserOut(UserOut):
    created_at: datetime


class AdminGroupOut(BaseModel):
    id: str
    name: str
    owner_id: str
    owner_name: str
    created_at: datetime
    archived_at: datetime | None
    event_count: int


class AdminAuditOut(BaseModel):
    id: str
    admin_id: str
    admin_name: str
    action: str
    target_type: str
    target_id: str | None
    detail: str
    created_at: datetime


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class GroupMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str


class ParticipantOut(BaseModel):
    id: str
    name: str
    user_id: str | None = None
    email: str | None = None


class GroupOut(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: datetime
    members: list[GroupMemberOut]
    participants: list[ParticipantOut] = []


class GroupInviteOut(BaseModel):
    token: str
    group_id: str
    expires_at: datetime
    url: str


class SettlementTransfer(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: Decimal


class SettlementOut(BaseModel):
    group_id: str
    event_ids: list[str]
    transfers: list[SettlementTransfer]


class BillIn(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=160)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    occurred_at: datetime | None = None
    receipt_name: str | None = Field(default=None, max_length=255)
    participant_ids: list[str] = Field(min_length=1)
    split_method: str = Field(default="EQUAL", pattern="^(EQUAL|PERCENTAGE|FIXED)$")
    allocations: dict[str, Decimal | None] | None = None

    @field_validator("allocations", mode="before")
    @classmethod
    def normalize_blank_allocations(cls, value):
        if isinstance(value, dict):
            return {key: (None if item is None or (isinstance(item, str) and not item.strip()) else item) for key, item in value.items()}
        return value

    @field_validator("amount")
    @classmethod
    def cents_only(cls, value: Decimal) -> Decimal:
        if value.as_tuple().exponent < -2:
            raise ValueError("金額最多兩位小數")
        return value


class EventCreate(BaseModel):
    title: str = Field(default="未命名消費", max_length=160)
    bills: list[BillIn] = Field(min_length=1)


class BillOut(BaseModel):
    id: str
    category: str
    description: str
    amount: Decimal
    occurred_at: datetime
    receipt_name: str | None
    receipt_content_type: str | None = None
    receipt_size: int | None = None
    participant_ids: list[str]
    shares: dict[str, Decimal]
    split_method: str
    allocations: dict[str, Decimal | None] | None
    confirmed_participant_ids: list[str] = []


class EventOut(BaseModel):
    id: str
    group_id: str
    payer_id: str
    title: str
    status: EventStatus
    created_at: datetime
    completed_at: datetime | None
    total: Decimal
    bills: list[BillOut]


class BillingRequestCreate(BaseModel):
    recipient_id: str | None = None
    participant_id: str | None = None
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    note: str = Field(min_length=1, max_length=160)
    event_id: str | None = None
    bill_id: str | None = None


class BillingRequestOut(BaseModel):
    id: str
    group_id: str
    requester_id: str
    recipient_id: str
    amount: Decimal
    note: str
    status: RequestStatus
    created_at: datetime
    event_id: str | None
    bill_id: str | None
    participant_id: str | None = None
    completed_by: str | None = None
    completed_at: datetime | None = None


class BillingRequestStatusUpdate(BaseModel):
    status: RequestStatus


class SettlementMessageOut(BaseModel):
    text: str


class RecipientMessageOut(BaseModel):
    recipient_id: str
    recipient_name: str
    total: Decimal
    text: str


class RecipientMessagesOut(BaseModel):
    messages: list[RecipientMessageOut]
