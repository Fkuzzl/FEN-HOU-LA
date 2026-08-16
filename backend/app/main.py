from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4
from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .config import settings
from .db import Base, engine, get_db
from .models import BillingRequest, Bill, EventStatus, ExpenseEvent, Group, GroupInvite, GroupMember, Participant, RequestStatus, User
from .schemas import BillingRequestCreate, BillingRequestOut, BillingRequestStatusUpdate, BillOut, EventCreate, EventOut, GroupCreate, GroupInviteOut, GroupMemberOut, GroupOut, LoginIn, ParticipantOut, PersonCreate, RecipientMessagesOut, RegisterIn, SettlementMessageOut, SettlementOut, SettlementTransfer, UserOut
from .security import current_user, hash_password, make_token, verify_password
from .split_engine import calculate_split, parse_allocations
import json
from time import monotonic

app = FastAPI(title="家庭朋友分帳 API", version="0.1.0")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-CSRF-Token"])
_rate_windows: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_limited_paths = {"/api/auth/login", "/api/auth/register", "/api/groups"}


@app.middleware("http")
async def security_headers(request, call_next):
    is_group_abuse_path = request.url.path.startswith("/api/groups/") and (request.url.path.endswith("/invites") or request.url.path.endswith("/billing-requests"))
    if request.method == "POST" and (request.url.path in _limited_paths or is_group_abuse_path):
        limit = 10 if request.url.path.startswith("/api/auth/") else 30
        key = (request.url.path, request.client.host if request.client else "unknown")
        now = monotonic()
        window = _rate_windows[key]
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= limit:
            return JSONResponse(status_code=429, content={"detail": "請稍後一分鐘再試"}, headers={"Retry-After": "60"})
        window.append(now)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


def money_text(value: Decimal) -> str:
    return f"HK${value:,.2f}"


@app.on_event("startup")
def startup() -> None:
    Path(settings.receipt_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def cookie(response: Response, user_id: str) -> None:
    response.set_cookie("session", make_token(user_id), httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=settings.jwt_expire_minutes * 60)


def member_group(db: Session, group_id: str, user: User) -> Group:
    group = db.scalar(select(Group).join(GroupMember).where(Group.id == group_id, GroupMember.user_id == user.id))
    if not group:
        raise HTTPException(status_code=403, detail="你不是此群組成員")
    return group


def owner_group(db: Session, group_id: str, user: User) -> Group:
    group = member_group(db, group_id, user)
    if group.owner_id != user.id:
        raise HTTPException(status_code=403, detail="只有群組擁有人可以進行此操作")
    return group


def settle_events(events: list[ExpenseEvent]) -> list[SettlementTransfer]:
    balances: dict[str, Decimal] = {}
    for event in events:
        for bill in event.bills:
            participant_roles = list(bill.participant_roles)
            participants = [person.id for person in participant_roles] or [person.id for person in bill.participants]
            if not participants:
                continue
            shares = calculate_split(bill.amount, participants, bill.split_method, parse_allocations(bill.split_allocations))
            if participant_roles:
                for participant in participant_roles:
                    share = shares[participant.id]
                    if participant.user_id == event.payer_id:
                        continue
                    balances[event.payer_id] = balances.get(event.payer_id, Decimal("0.00")) + share
                    balances[participant.id] = balances.get(participant.id, Decimal("0.00")) - share
            else:
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
        participants = [person.id for person in bill.participant_roles] or [user.id for user in bill.participants]
        allocations = parse_allocations(bill.split_allocations)
        shares = calculate_split(bill.amount, participants, bill.split_method, allocations) if participants else {}
        bills.append(BillOut(id=bill.id, category=bill.category, description=bill.description, amount=bill.amount, occurred_at=bill.occurred_at, receipt_name=bill.receipt_name, receipt_content_type=bill.receipt_content_type, receipt_size=bill.receipt_size, participant_ids=participants, shares=shares, split_method=bill.split_method, allocations=allocations))
        total += bill.amount
    return EventOut(id=event.id, group_id=event.group_id, payer_id=event.payer_id, title=event.title, status=event.status, created_at=event.created_at, completed_at=event.completed_at, total=total, bills=bills)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where((User.email == data.email.lower()) | (User.username == data.username.lower()))):
        raise HTTPException(status_code=409, detail="此電郵已註冊")
    user = User(username=data.username.lower(), name=data.name.strip(), email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user); cookie(response, user.id)
    return user


@app.post("/api/auth/login", response_model=UserOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳戶名稱或密碼不正確")
    cookie(response, user.id)
    return user


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie("session")


@app.delete("/api/account", status_code=204)
def delete_account(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owns_group = db.scalar(select(Group.id).where(Group.owner_id == user.id))
    paid_event = db.scalar(select(ExpenseEvent.id).where(ExpenseEvent.payer_id == user.id))
    if owns_group or paid_event:
        raise HTTPException(status_code=409, detail="帳戶仍擁有群組或付款記錄；請先處理擁有權及歷史開支")
    for participant in db.scalars(select(Participant).where(Participant.user_id == user.id)).all():
        participant.user_id = None
    db.delete(user); db.commit()
    response.delete_cookie("session")


@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/groups", response_model=list[GroupOut])
def list_groups(user: User = Depends(current_user), db: Session = Depends(get_db)):
    groups = db.scalars(select(Group).join(GroupMember).where(GroupMember.user_id == user.id).options(joinedload(Group.members).joinedload(GroupMember.user))).unique().all()
    return [{"id": g.id, "name": g.name, "owner_id": g.owner_id, "created_at": g.created_at, "members": [{"id": p.id, "name": p.name, "email": p.user.email if p.user else "", "username": p.user.username if p.user else ""} for p in g.participants], "participants": [{"id": p.id, "name": p.name, "user_id": p.user_id, "email": p.user.email if p.user else None} for p in g.participants]} for g in groups]


@app.post("/api/groups", response_model=GroupOut, status_code=201)
def create_group(data: GroupCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    group = Group(name=data.name.strip(), owner_id=user.id)
    db.add(group); db.flush(); db.add(GroupMember(group_id=group.id, user_id=user.id)); db.commit(); db.refresh(group)
    participant = Participant(group_id=group.id, name=user.name, user_id=user.id)
    db.add(participant); db.commit()
    return {"id": group.id, "name": group.name, "owner_id": group.owner_id, "created_at": group.created_at, "members": [user], "participants": [participant]}


@app.post("/api/groups/{group_id}/leave", status_code=204)
def leave_group(group_id: str, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    group = member_group(db, group_id, user)
    if group.owner_id == user.id:
        raise HTTPException(status_code=409, detail="群組擁有人不能離開；請先轉移或刪除群組")
    membership = db.get(GroupMember, {"group_id": group_id, "user_id": user.id})
    if membership:
        db.delete(membership)
    for participant in db.scalars(select(Participant).where(Participant.group_id == group_id, Participant.user_id == user.id)).all():
        participant.user_id = None
    db.commit()


@app.post("/api/groups/{group_id}/invites", response_model=GroupInviteOut, status_code=201)
def create_invite(group_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owner_group(db, group_id, user)
    invite = GroupInvite(group_id=group_id, created_by=user.id, token=token_urlsafe(32), expires_at=datetime.now(timezone.utc) + timedelta(days=7))
    db.add(invite); db.commit(); db.refresh(invite)
    return {"token": invite.token, "group_id": group_id, "expires_at": invite.expires_at, "url": f"/?invite={invite.token}"}


@app.post("/api/invites/{token}/accept", response_model=GroupOut)
def accept_invite(token: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    invite = db.scalar(select(GroupInvite).where(GroupInvite.token == token))
    expires_at = invite.expires_at.replace(tzinfo=timezone.utc) if invite and invite.expires_at.tzinfo is None else (invite.expires_at if invite else None)
    if not invite or invite.used_at or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="邀請連結已失效")
    if not db.scalar(select(GroupMember).where(GroupMember.group_id == invite.group_id, GroupMember.user_id == user.id)):
        db.add(GroupMember(group_id=invite.group_id, user_id=user.id))
        db.add(Participant(group_id=invite.group_id, name=user.name, user_id=user.id))
    invite.used_at = datetime.now(timezone.utc); db.commit()
    group = db.scalars(select(Group).where(Group.id == invite.group_id).options(joinedload(Group.members).joinedload(GroupMember.user))).unique().one()
    return {"id": group.id, "name": group.name, "owner_id": group.owner_id, "created_at": group.created_at, "members": [{"id": p.id, "name": p.name, "email": p.user.email if p.user else "", "username": p.user.username if p.user else ""} for p in group.participants], "participants": [{"id": p.id, "name": p.name, "user_id": p.user_id, "email": p.user.email if p.user else None} for p in group.participants]}


@app.post("/api/groups/{group_id}/people", response_model=ParticipantOut, status_code=201)
def create_person(group_id: str, data: PersonCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owner_group(db, group_id, user)
    participant = Participant(group_id=group_id, name=data.name.strip())
    db.add(participant); db.commit(); db.refresh(participant)
    return {"id": participant.id, "name": participant.name, "user_id": None, "email": None}


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


@app.get("/api/groups/{group_id}/settlement/message", response_model=SettlementMessageOut)
def group_settlement_message(group_id: str, event_ids: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member_group(db, group_id, user)
    requested = [item for item in (event_ids or "").split(",") if item]
    query = select(ExpenseEvent).where(ExpenseEvent.group_id == group_id, ExpenseEvent.status == EventStatus.COMPLETED).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants))
    if requested:
        query = query.where(ExpenseEvent.id.in_(requested))
    events = db.scalars(query).unique().all()
    if requested and len(events) != len(set(requested)):
        raise HTTPException(status_code=400, detail="部分開支不存在或不屬於此群組")
    transfers = settle_events(events)
    names = {participant.id: participant.name for participant in db.scalars(select(Participant).where(Participant.group_id == group_id)).all()}
    names.update({member.user_id: member.user.name for member in db.scalars(select(GroupMember).where(GroupMember.group_id == group_id).options(joinedload(GroupMember.user))).all()})
    lines = ["【分好啦｜合併結算】", f"已合併 {len(events)} 次開支", "", "開支明細："]
    for event in events:
        view = event_view(event)
        bills = "；".join(f"{bill.description} {money_text(bill.amount)}" for bill in view.bills)
        lines.append(f"• {view.title}｜{money_text(view.total)}")
        lines.append(f"  {bills}")
    lines.append("最終結算：")
    if transfers:
        lines.append("請按以下金額轉帳：")
        lines.extend(f"{names.get(transfer.from_user_id, '群組成員')} → {names.get(transfer.to_user_id, '群組成員')}：{money_text(transfer.amount)}" for transfer in transfers)
    else:
        lines.append("已經結清，沒有需要轉帳的金額。")
    lines.extend(["", "謝謝！"])
    return {"text": "\n".join(lines)}


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
    members = db.scalars(select(Participant).where(Participant.group_id == event.group_id)).all()
    names = {participant.id: participant.name for participant in members}
    names.update({participant.user_id: participant.name for participant in members if participant.user_id})
    lines = [f"【分好啦｜{view.title}】", f"總額：{money_text(view.total)}", f"付款人：{names.get(view.payer_id, '群組成員')}", ""]
    for bill in view.bills:
        lines.append(f"{bill.description}｜{money_text(bill.amount)}")
        for participant_id, share in bill.shares.items():
            lines.append(f"  {names.get(participant_id, '群組成員')}：{money_text(share)}")
    lines.extend(["", "請按以上金額分帳，謝謝！"])
    return {"text": "\n".join(lines)}


@app.post("/api/bills/{bill_id}/receipt", response_model=BillOut)
async def upload_receipt(bill_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    bill = db.scalar(select(Bill).join(ExpenseEvent).where(Bill.id == bill_id))
    if not bill:
        raise HTTPException(status_code=404, detail="找不到此單據")
    event = db.get(ExpenseEvent, bill.event_id)
    member_group(db, event.group_id, user)
    if event.payer_id != user.id:
        raise HTTPException(status_code=403, detail="只有付款人可以上載收據")
    allowed = {"image/jpeg": ".jpg", "image/png": ".png"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="只支援 JPG 或 PNG 收據圖片")
    receipt_dir = Path(settings.receipt_dir)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    key = f"{uuid4()}{allowed[file.content_type]}"
    target = receipt_dir / key
    size = 0
    header = b""
    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                if not header:
                    header = chunk[:8]
                    signatures = {
                        "image/jpeg": header.startswith(b"\xff\xd8\xff"),
                        "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
                    }
                    if not signatures[file.content_type]:
                        raise HTTPException(status_code=400, detail="收據檔案內容與副檔名不一致")
                size += len(chunk)
                if size > 10 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="收據圖片不可超過 10 MB")
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if bill.receipt_key:
        (receipt_dir / bill.receipt_key).unlink(missing_ok=True)
    bill.receipt_key = key
    bill.receipt_name = file.filename or key
    bill.receipt_content_type = file.content_type
    bill.receipt_size = size
    db.commit(); db.refresh(bill)
    event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == bill.event_id).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participant_roles)))
    return event_view(event).bills[[item.id for item in event.bills].index(bill.id)]


@app.get("/api/bills/{bill_id}/receipt")
def download_receipt(bill_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    bill = db.scalar(select(Bill).join(ExpenseEvent).where(Bill.id == bill_id))
    if not bill or not bill.receipt_key:
        raise HTTPException(status_code=404, detail="找不到此收據")
    event = db.get(ExpenseEvent, bill.event_id)
    member_group(db, event.group_id, user)
    path = Path(settings.receipt_dir) / bill.receipt_key
    if not path.is_file():
        raise HTTPException(status_code=404, detail="收據檔案不存在")
    return FileResponse(path, media_type=bill.receipt_content_type or "application/octet-stream", filename=bill.receipt_name or bill.receipt_key)


@app.get("/api/expenses/{event_id}/messages", response_model=RecipientMessagesOut)
def expense_recipient_messages(event_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == event_id).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants)))
    if not event:
        raise HTTPException(status_code=404, detail="找不到此開支")
    member_group(db, event.group_id, user)
    view = event_view(event)
    members = db.scalars(select(Participant).where(Participant.group_id == event.group_id)).all()
    names = {member.id: member.name for member in members}
    names.update({member.user_id: member.name for member in members if member.user_id})
    participant_users = {member.id: member.user_id for member in members}
    totals: dict[str, Decimal] = {}
    details: dict[str, list[str]] = {}
    for bill in view.bills:
        for participant_id, share in bill.shares.items():
            if participant_users.get(participant_id) == view.payer_id:
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
    group = owner_group(db, group_id, user)
    participant = None
    if data.participant_id:
        participant = db.scalar(select(Participant).where(Participant.id == data.participant_id, Participant.group_id == group_id))
    elif data.recipient_id:
        participant = db.scalar(select(Participant).where(Participant.group_id == group_id, Participant.user_id == data.recipient_id))
    recipient = db.get(User, participant.user_id) if participant and participant.user_id else (db.get(User, data.recipient_id) if data.recipient_id else None)
    if not participant or (recipient and recipient.id == user.id):
        raise HTTPException(status_code=400, detail="收款人必須是群組內另一位成員")
    if data.event_id:
        event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == data.event_id, ExpenseEvent.group_id == group_id))
        if not event:
            raise HTTPException(status_code=400, detail="開支不屬於此群組")
    if data.bill_id:
        bill = db.scalar(select(Bill).join(ExpenseEvent).where(Bill.id == data.bill_id, ExpenseEvent.group_id == group_id))
        if not bill or (data.event_id and bill.event_id != data.event_id):
            raise HTTPException(status_code=400, detail="單據不屬於此群組或事件")
    request = BillingRequest(group_id=group_id, requester_id=user.id, recipient_id=recipient.id if recipient else user.id, participant_id=participant.id, amount=data.amount, note=data.note.strip(), event_id=data.event_id, bill_id=data.bill_id)
    db.add(request); db.commit(); db.refresh(request)
    return request


@app.patch("/api/groups/{group_id}/billing-requests/{request_id}", response_model=BillingRequestOut)
def update_billing_request(group_id: str, request_id: str, data: BillingRequestStatusUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owner_group(db, group_id, user)
    request = db.scalar(select(BillingRequest).where(BillingRequest.id == request_id, BillingRequest.group_id == group_id))
    if not request or user.id not in {request.requester_id, request.recipient_id}:
        raise HTTPException(status_code=404, detail="找不到此分帳請求")
    if request.status != RequestStatus.PENDING or data.status not in {RequestStatus.COMPLETED, RequestStatus.CANCELLED}:
        raise HTTPException(status_code=409, detail="此請求已不可再變更")
    request.status = data.status
    if data.status == RequestStatus.COMPLETED:
        request.completed_by = user.id
        request.completed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(request)
    return request


@app.post("/api/groups/{group_id}/expenses", response_model=EventOut, status_code=201)
def create_expense(group_id: str, data: EventCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owner_group(db, group_id, user)
    group_participants = db.scalars(select(Participant).where(Participant.group_id == group_id)).all()
    participant_by_id = {participant.id: participant for participant in group_participants}
    participant_by_user_id = {participant.user_id: participant for participant in group_participants if participant.user_id}
    event = ExpenseEvent(group_id=group_id, payer_id=user.id, title=data.title.strip() or "未命名消費")
    db.add(event); db.flush()
    for item in data.bills:
        resolved_roles = [participant_by_id.get(participant_id) or participant_by_user_id.get(participant_id) for participant_id in item.participant_ids]
        if not all(resolved_roles) or len({role.id for role in resolved_roles}) != len(resolved_roles):
            raise HTTPException(status_code=400, detail="參與者必須是群組成員，且不能重複")
        resolved_ids = [role.id for role in resolved_roles]
        source_allocations = item.allocations or {}
        allocations = {role.id: source_allocations.get(source_id, source_allocations.get(role.id)) for source_id, role in zip(item.participant_ids, resolved_roles)}
        try:
            calculate_split(item.amount, resolved_ids, item.split_method, allocations)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        bill = Bill(event_id=event.id, category=item.category, description=item.description, amount=item.amount, occurred_at=item.occurred_at or datetime.now(timezone.utc), receipt_name=item.receipt_name, split_method=item.split_method, split_allocations=json.dumps({key: (str(value) if value is not None else None) for key, value in (allocations or {}).items()}))
        bill.participant_roles = resolved_roles
        db.add(bill)
    event.status = EventStatus.COMPLETED; event.completed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(event)
    event = db.scalar(select(ExpenseEvent).where(ExpenseEvent.id == event.id).options(joinedload(ExpenseEvent.bills).joinedload(Bill.participants)))
    return event_view(event)
