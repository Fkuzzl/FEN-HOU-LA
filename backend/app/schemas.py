from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import EventStatus, RequestStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: EmailStr


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
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


class GroupOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    members: list[GroupMemberOut]


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
    participant_ids: list[str]
    shares: dict[str, Decimal]
    split_method: str
    allocations: dict[str, Decimal | None] | None


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
    recipient_id: str
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
