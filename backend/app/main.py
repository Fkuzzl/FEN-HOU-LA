from datetime import datetime, timedelta, timezone
from decimal import Decimal
from secrets import token_urlsafe
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .config import settings
from .db import Base, engine, get_db
from .models import BillingRequest, Bill, EventStatus, ExpenseEvent, Group, GroupInvite, GroupMember, RequestStatus, User
from .schemas import BillingRequestCreate, BillingRequestOut, BillingRequestStatusUpdate, BillOut, EventCreate, EventOut, GroupCreate, GroupInviteOut, GroupMemberOut, GroupOut, LoginIn, PersonCreate, RecipientMessagesOut, RegisterIn, SettlementMessageOut, SettlementOut, SettlementTransfer, UserOut
from .security import current_user, hash_password, make_token, verify_password
from .split_engine import calculate_split, parse_allocations
import json
from sqlalchemy import text

app = FastAPI(title="家庭朋友分帳 API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def money_text(value: Decimal) -> str:
    return f"HK${value:,.2f}"


@app.on_event("startup")
def startup() -> None:
    with engine.begin() as connection:
        for statement in ("ALTER TABLE bills ADD COLUMN split_method VARCHAR(20) DEFAULT 'EQUAL'", "ALTER TABLE bills ADD COLUMN split_allocations TEXT", "ALTER TABLE billing_requests ADD COLUMN event_id VARCHAR(36)", "ALTER TABLE billing_requests ADD COLUMN bill_id VARCHAR(36)"):
            try:
                connection.execute(text(statement))
            except Exception:
                pass
    Base.metadata.create_all(bind=engine)


def cookie(response: Response, user_id: str) -> None:
    response.set_cookie("session", make_token(user_id), httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=settings.jwt_expire_minutes * 60)


def member_group(db: Session, group_id: str, user: User) -> Group:
    group = db.scalar(select(Group).join(GroupMember).where(Group.id == group_id, GroupMember.user_id == user.id))
    if not group:
        raise HTTPException(status_code=403, detail="你不是此群組成員")
    return group


def settle_events(events: list[ExpenseEvent]) -> list[SettlementTransfer]:
    balances: dict[str, Decimal] = {}
    for event in events:
        for bill in event.bills:
            participants = [person.id for person in bill.participants]
            if not participants:
                continue
            shares = calculate_split(bill.amount, participants, bill.split_method, parse_allocations(bill.split_allocations))
            for participant_id, share in shares.items():
                if participant_id == event.payer_id:
                    continue
                balances[event.payer_id] = balances.get(event.payer_id, Decimal("0.00")) + share
                balances[participant_id] = balances.get(participant_id, Decimal("0.00")) - share
    creditors = [[user_id, amount] for user_id, amount in balances.items() if amount > 0]
    debtors = [[user_id, -amount] for user_id, amount in balances.items() if amount < 0]
    transfers: list[SettlementTransfer] = []
    for debtor in debtors:
        for creditor in creditors:
            amount = min(debtor[1], creditor[1]).quantize(Decimal("0.01"))
            if amount <= 0:
                continue
            transfers.append(SettlementTransfer(from_user_id=debtor[0], to_user_id=creditor[0], amount=amount))
            debtor[1] -= amount
            creditor[1] -= amount
            if debtor[1] <= 0:
                break
    return transfers


def event_view(event: ExpenseEvent) -> EventOut:
    bills = []
    total = Decimal("0")
    for bill in event.bills:
        participants = [user.id for user in bill.participants]
        allocations = parse_allocations(bill.split_allocations)
        shares = calculate_split(bill.amount, participants, bill.split_method, allocations) if participants else {}
        bills.append(BillOut(id=bill.id, category=bill.category, description=bill.description, amount=bill.amount, occurred_at=bill.occurred_at, receipt_name=bill.receipt_name, participant_ids=participants, shares=shares, split_method=bill.split_method, allocations=allocations))
        total += bill.amount
    return EventOut(id=event.id, group_id=event.group_id, payer_id=event.payer_id, title=event.title, status=event.status, created_at=event.created_at, completed_at=event.completed_at, total=total, bills=bills)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(status_code=409, detail="此電郵已註冊")
    user = User(name=data.name.strip(), email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user); cookie(response, user.id)
    return user


@app.post("/api/auth/login", response_model=UserOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="電郵或密碼不正確")
    cookie(response, user.id)
    return user


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie("session")


@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/groups", response_model=list[GroupOut])
def list_groups(user: User = Depends(current_user), db: Session = Depends(get_db)):
    groups = db.scalars(select(Group).join(GroupMember).where(GroupMember.user_id == user.id).options(joinedload(Group.members).joinedload(GroupMember.user))).unique().all()
    return [{"id": g.id, "name": g.name, "created_at": g.created_at, "members": [m.user for m in g.members]} for g in groups]


@app.post("/api/groups", response_model=GroupOut, status_code=201)
def create_group(data: GroupCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    group = Group(name=data.name.strip())
    db.add(group); db.flush(); db.add(GroupMember(group_id=group.id, user_id=user.id)); db.commit(); db.refresh(group)
    return {"id": group.id, "name": group.name, "created_at": group.created_at, "members": [user]}


@app.post("/api/groups/{group_id}/invites", response_model=GroupInviteOut, status_code=201)
def create_invite(group_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    invite = GroupInvite(group_id=group_id, created_by=user.id, token=token_urlsafe(32), expires_at=datetime.now(timezone.utc) + timedelta(days=7))
    db.add(invite); db.commit(); db.refresh(invite)
    return {"token": invite.token, "group_id": group_id, "expires_at": invite.expires_at, "url": f"/?invite={invite.token}"}


@app.post("/api/invites/{token}/accept", response_model=GroupOut)
def accept_invite(token: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    invite = db.scalar(select(GroupInvite).where(GroupInvite.token == token))
    if not invite or invite.used_at or invite.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="邀請連結已失效")
    if not db.scalar(select(GroupMember).where(GroupMember.group_id == invite.group_id, GroupMember.user_id == user.id)):
        db.add(GroupMember(group_id=invite.group_id, user_id=user.id))
    invite.used_at = datetime.now(timezone.utc); db.commit()
    group = db.scalars(select(Group).where(Group.id == invite.group_id).options(joinedload(Group.members).joinedload(GroupMember.user))).unique().one()
    return {"id": group.id, "name": group.name, "created_at": group.created_at, "members": [member.user for member in group.members]}


@app.post("/api/groups/{group_id}/people", response_model=GroupMemberOut, status_code=201)
def create_person(group_id: str, data: PersonCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    person = User(name=data.name.strip(), email=f"contact-{uuid4()}@contacts.example.com", password_hash=hash_password(token_urlsafe(32)))
    db.add(person); db.flush(); db.add(GroupMember(group_id=group_id, user_id=person.id)); db.commit(); db.refresh(person)
    return person


@app.get("/api/groups/{group_id}/expenses", response_model=list[EventOut])
def list_expenses(group_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    events = db.scalars(select(ExpenseEvent).where(ExpenseEvent.group_id == group_id, ExpenseEvent.status == EventStatus.COMPLETED).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants))).unique().all()
    return [event_view(event) for event in events]


@app.get("/api/groups/{group_id}/settlement", response_model=SettlementOut)
def group_settlement(group_id: str, event_ids: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    requested = [item for item in (event_ids or "").split(",") if item]
    query = select(ExpenseEvent).where(ExpenseEvent.group_id == group_id, ExpenseEvent.status == EventStatus.COMPLETED).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants))
    if requested:
        query = query.where(ExpenseEvent.id.in_(requested))
    events = db.scalars(query).unique().all()
    if requested and len(events) != len(set(requested)):
        raise HTTPException(status_code=400, detail="部分開支不存在或不屬於此群組")
    return {"group_id": group_id, "event_ids": [event.id for event in events], "transfers": settle_events(events)}


@app.get("/api/expenses/{event_id}", response_model=EventOut)
def get_expense(event_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == event_id).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants)))
    if not event:
        raise HTTPException(status_code=404, detail="找不到此開支")
    member_group(db, event.group_id, user)
    return event_view(event)


@app.get("/api/expenses/{event_id}/message", response_model=SettlementMessageOut)
def expense_message(event_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == event_id).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants)))
    if not event:
        raise HTTPException(status_code=404, detail="找不到此開支")
    member_group(db, event.group_id, user)
    view = event_view(event)
    names = {member.user_id: member.user.name for member in db.scalars(select(GroupMember).where(GroupMember.group_id == event.group_id).options(joinedload(GroupMember.user))).all()}
    lines = [f"【分好啦｜{view.title}】", f"總額：{money_text(view.total)}", f"付款人：{names.get(view.payer_id, '群組成員')}", ""]
    for bill in view.bills:
        lines.append(f"{bill.description}｜{money_text(bill.amount)}")
        for participant_id, share in bill.shares.items():
            lines.append(f"  {names.get(participant_id, '群組成員')}：{money_text(share)}")
    lines.extend(["", "請按以上金額分帳，謝謝！"])
    return {"text": "\n".join(lines)}


@app.get("/api/expenses/{event_id}/messages", response_model=RecipientMessagesOut)
def expense_recipient_messages(event_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == event_id).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants)))
    if not event:
        raise HTTPException(status_code=404, detail="找不到此開支")
    member_group(db, event.group_id, user)
    view = event_view(event)
    members = db.scalars(select(GroupMember).where(GroupMember.group_id == event.group_id).options(joinedload(GroupMember.user))).all()
    names = {member.user_id: member.user.name for member in members}
    totals: dict[str, Decimal] = {}
    details: dict[str, list[str]] = {}
    for bill in view.bills:
        for participant_id, share in bill.shares.items():
            if participant_id == view.payer_id:
                continue
            totals[participant_id] = totals.get(participant_id, Decimal("0.00")) + share
            details.setdefault(participant_id, []).append(f"- {bill.description}：{money_text(share)}")
    messages = []
    payer_name = names.get(view.payer_id, "群組成員")
    for recipient_id, total in totals.items():
        recipient_name = names.get(recipient_id, "群組成員")
        text = "\n".join([
            f"【分好啦｜{view.title}】",
            f"你好 {recipient_name}，請支付 {money_text(total)}",
            f"付款給：{payer_name}",
            "",
            "明細：",
            *details.get(recipient_id, []),
            "",
            "謝謝！",
        ])
        messages.append({"recipient_id": recipient_id, "recipient_name": recipient_name, "total": total, "text": text})
    return {"messages": messages}


@app.get("/api/groups/{group_id}/billing-requests", response_model=list[BillingRequestOut])
def list_billing_requests(group_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    return db.scalars(select(BillingRequest).where(BillingRequest.group_id == group_id).order_by(BillingRequest.created_at.desc())).all()


@app.post("/api/groups/{group_id}/billing-requests", response_model=BillingRequestOut, status_code=201)
def create_billing_request(group_id: str, data: BillingRequestCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    recipient = db.scalar(select(User).join(GroupMember).where(GroupMember.group_id == group_id, User.id == data.recipient_id))
    if not recipient or recipient.id == user.id:
        raise HTTPException(status_code=400, detail="收款人必須是群組內另一位成員")
    if data.event_id:
        event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == data.event_id, ExpenseEvent.group_id == group_id))
        if not event:
            raise HTTPException(status_code=400, detail="開支不屬於此群組")
    request = BillingRequest(group_id=group_id, requester_id=user.id, recipient_id=recipient.id, amount=data.amount, note=data.note.strip(), event_id=data.event_id, bill_id=data.bill_id)
    db.add(request); db.commit(); db.refresh(request)
    return request


@app.patch("/api/groups/{group_id}/billing-requests/{request_id}", response_model=BillingRequestOut)
def update_billing_request(group_id: str, request_id: str, data: BillingRequestStatusUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    request = db.scalar(select(BillingRequest).where(BillingRequest.id == request_id, BillingRequest.group_id == group_id))
    if not request or user.id not in {request.requester_id, request.recipient_id}:
        raise HTTPException(status_code=404, detail="找不到此分帳請求")
    request.status = data.status; db.commit(); db.refresh(request)
    return request


@app.post("/api/groups/{group_id}/expenses", response_model=EventOut, status_code=201)
def create_expense(group_id: str, data: EventCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    participant_ids = {participant_id for bill in data.bills for participant_id in bill.participant_ids}
    members = {member.user_id for member in db.scalars(select(GroupMember).where(GroupMember.group_id == group_id)).all()}
    if not participant_ids.issubset(members):
        raise HTTPException(status_code=400, detail="參與者必須是群組成員")
    event = ExpenseEvent(group_id=group_id, payer_id=user.id, title=data.title.strip() or "未命名消費")
    db.add(event); db.flush()
    for item in data.bills:
        try:
            allocations = item.allocations
            shares = calculate_split(item.amount, item.participant_ids, item.split_method, allocations)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        bill = Bill(event_id=event.id, category=item.category, description=item.description, amount=item.amount, occurred_at=item.occurred_at or datetime.now(timezone.utc), receipt_name=item.receipt_name, split_method=item.split_method, split_allocations=json.dumps({key: (str(value) if value is not None else None) for key, value in (allocations or {}).items()}))
        bill.participants = [db.get(User, participant_id) for participant_id in item.participant_ids]
        db.add(bill)
    event.status = EventStatus.COMPLETED; event.completed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(event)
    event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == event.id).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants)))
    return event_view(event)
