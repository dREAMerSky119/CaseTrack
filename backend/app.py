"""CaseTrack 360 prototype API: Flask + SQLite, session auth, case history and explainable rules."""
from __future__ import annotations
import os, re, secrets
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, instance_path=str(BASE_DIR / "instance"), instance_relative_config=True)
Path(app.instance_path).mkdir(parents=True, exist_ok=True)
app.config.update(
    SECRET_KEY=os.environ.get("CASETRACK_SECRET_KEY") or "development-only-change-this-secret",
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL") or f"sqlite:///{Path(app.instance_path) / 'casetrack.db'}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
)
CORS(app, origins=os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","), supports_credentials=True)
db = SQLAlchemy(app)

PRIORITIES = {"Low", "Medium", "High", "Critical"}
STATUSES = {"Open", "In Progress", "Pending", "Resolved", "Closed"}
FREQUENCIES = {"First Reported", "Recurring", "Repeated Pattern", "Under Review"}
CATEGORIES = {"Infrastructure", "Faculty", "Examination", "Student Grievance", "Institutional Compliance", "Other"}
ACTIVE_STATUSES = {"Open", "In Progress", "Pending"}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="Administrator")
    # This prototype's demo login is intentionally not a production identity provider.
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Institution(db.Model):
    id = db.Column(db.String(40), primary_key=True)
    name = db.Column(db.String(220), nullable=False, index=True)
    type = db.Column(db.String(80), default="Other")
    state = db.Column(db.String(100), default="")
    city = db.Column(db.String(100), default="")
    status = db.Column(db.String(30), default="Active")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Complaint(db.Model):
    id = db.Column(db.String(30), primary_key=True)
    institution_id = db.Column(db.String(40), db.ForeignKey("institution.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False, default="Other")
    bureau = db.Column(db.String(100), nullable=False, default="Unassigned")
    official = db.Column(db.String(120), default="Unassigned")
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    frequency = db.Column(db.String(30), nullable=False, default="First Reported")
    frequency_signal = db.Column(db.String(30), nullable=False, default="First Reported")
    status = db.Column(db.String(30), nullable=False, default="Open")
    received = db.Column(db.String(10), nullable=False)
    due = db.Column(db.String(10), default="")
    updated = db.Column(db.String(10), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=35)
    related = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    institution = db.relationship("Institution", backref=db.backref("complaints", lazy=True))

class CaseHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.String(30), db.ForeignKey("complaint.id"), nullable=False, index=True)
    actor = db.Column(db.String(180), nullable=False)
    action = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(180), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(50), nullable=False)
    detail = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class RelatedCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_a = db.Column(db.String(30), db.ForeignKey("complaint.id"), nullable=False)
    complaint_b = db.Column(db.String(30), db.ForeignKey("complaint.id"), nullable=False)
    reason = db.Column(db.String(250), nullable=False)
    confidence = db.Column(db.Integer, nullable=False, default=50)
    reviewed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Handover(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.String(30), db.ForeignKey("complaint.id"), nullable=False)
    from_bureau = db.Column(db.String(100), nullable=False)
    to_bureau = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Pending")
    created_by = db.Column(db.String(180), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None

def user_json(user):
    name = user.name or "Workspace user"
    initials = "".join(part[0].upper() for part in name.split()[:2]) or "U"
    return {"id": user.id, "name": name, "email": user.email, "role": user.role, "initials": initials, "demo": True}

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user(): return jsonify(message="Please sign in to access this workspace."), 401
        return fn(*args, **kwargs)
    return wrapped

def actor_name():
    user = current_user()
    return user.name if user else "system"

def iso_today(): return date.today().isoformat()
def parse_date(value):
    if not value: return None
    try: return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError): return None

def complaint_json(c):
    return {"id": c.id, "institutionId": c.institution_id, "institution": c.institution.name if c.institution else "Unknown institution",
            "title": c.title, "description": c.description, "category": c.category, "bureau": c.bureau, "official": c.official or "Unassigned",
            "priority": c.priority, "frequency": c.frequency, "frequencySignal": c.frequency_signal, "status": c.status, "received": c.received, "due": c.due or "",
            "updated": c.updated, "score": c.score, "related": bool(c.related), "notes": c.notes or ""}

def institution_json(i):
    return {"id": i.id, "name": i.name, "type": i.type, "state": i.state, "city": i.city, "status": i.status,
            "complaints": Complaint.query.filter_by(institution_id=i.id).count()}

def record_history(c, action, detail):
    db.session.add(CaseHistory(complaint_id=c.id, actor=actor_name(), action=action, detail=detail))
    db.session.add(AuditLog(actor=actor_name(), action=action, entity_type="complaint", entity_id=c.id, detail=detail))

def related_reason(a, b):
    reasons=[]; score=0
    if a.institution_id == b.institution_id: reasons.append("same institution"); score += 35
    if a.category == b.category: reasons.append("same category"); score += 25
    ta=set(re.findall(r"[a-z]{4,}", (a.title+" "+a.description).lower()))
    tb=set(re.findall(r"[a-z]{4,}", (b.title+" "+b.description).lower()))
    common=ta & tb
    if common: reasons.append("shared keywords: " + ", ".join(sorted(common)[:4])); score += min(40, len(common)*10)
    date_a=parse_date(a.received) or date.today()
    date_b=parse_date(b.received) or date.today()
    if abs((date_a-date_b).days) <= 90: score += 5
    return "; ".join(reasons), min(score, 100)

def refresh_case_intelligence(c):
    """Transparent heuristic; attention score is not an official AICTE decision."""
    today=date.today(); score=0
    due=parse_date(c.due); updated=parse_date(c.updated); received=parse_date(c.received)
    if c.status in ACTIVE_STATUSES: score += 15
    if c.priority == "Low": score += 0
    elif c.priority == "Medium": score += 8
    elif c.priority == "High": score += 18
    elif c.priority == "Critical": score += 25
    if due and due < today and c.status in ACTIVE_STATUSES: score += min(25, 10 + (today-due).days)
    elif due and due <= today + timedelta(days=3) and c.status in ACTIVE_STATUSES: score += 10
    if updated and (today-updated).days >= 7 and c.status in ACTIVE_STATUSES: score += 15
    if received and (today-received).days >= 21 and c.status in ACTIVE_STATUSES: score += 10
    sibling_count=Complaint.query.filter(Complaint.institution_id==c.institution_id, Complaint.category==c.category, Complaint.id!=c.id, Complaint.received >= (today-timedelta(days=90)).isoformat()).count()
    # Keep the official/user-entered classification separate from the calculated record signal.
    c.frequency_signal = "Repeated Pattern" if sibling_count >= 2 else ("Recurring" if sibling_count == 1 else "First Reported")
    c.score=min(100, score)
    c.related = sibling_count > 0
    # Generate reviewable related-case candidates; never merge/delete cases automatically.
    others=Complaint.query.filter(Complaint.id != c.id).all()
    for other in others:
        reason, confidence=related_reason(c, other)
        if reason and confidence >= 45:
            pair=sorted([c.id, other.id])
            existing=RelatedCase.query.filter_by(complaint_a=pair[0], complaint_b=pair[1]).first()
            if not existing:
                db.session.add(RelatedCase(complaint_a=pair[0], complaint_b=pair[1], reason=reason, confidence=confidence))

def seed_database():
    if Institution.query.count(): return
    institutions=[
      ("INST-1001","Western Valley Institute of Technology","Engineering","Maharashtra","Mumbai","Active"),
      ("INST-1002","Saraswati College of Management","Management","Maharashtra","Pune","Active"),
      ("INST-1003","Northstar Polytechnic","Polytechnic","Gujarat","Ahmedabad","Active"),
      ("INST-1004","Riverbend School of Engineering","Engineering","Karnataka","Bengaluru","Inactive"),
      ("INST-1005","Crescent Institute of Applied Sciences","University","Telangana","Hyderabad","Active")]
    for row in institutions: db.session.add(Institution(id=row[0],name=row[1],type=row[2],state=row[3],city=row[4],status=row[5]))
    db.session.flush()
    days=lambda n:(date.today()-timedelta(days=n)).isoformat()
    cases=[
      ("CT-26041","INST-1001","Repeated laboratory equipment downtime","Multiple reports describe laboratory equipment being unavailable during scheduled practical sessions.","Infrastructure","Infrastructure Cell","A. Mehta","High","Repeated Pattern","In Progress",days(4),days(-3),days(1),"Awaiting institution response and maintenance schedule."),
      ("CT-26040","INST-1002","Examination result correction request","A student has requested a review of a result entry.","Examination","Academic Cell","R. Shah","Medium","First Reported","Open",days(2),days(-8),days(2),""),
      ("CT-26039","INST-1003","Faculty vacancy disclosure concern","The submitted staffing details appear inconsistent with a previous report.","Faculty","Compliance Bureau","P. Iyer","Critical","Recurring","In Progress",days(12),days(-2),days(6),"Escalated for authorised review."),
      ("CT-26038","INST-1001","Hostel water supply interruptions","Reports indicate recurring water supply interruptions in student accommodation.","Infrastructure","Student Grievance Cell","S. Kulkarni","High","Recurring","Pending",days(18),days(-1),days(9),"Institution has been asked to submit an action plan."),
      ("CT-26037","INST-1004","Clarification on affiliation documents","A request for clarification regarding submitted affiliation documents.","Institutional Compliance","Compliance Bureau","N. Rao","Low","First Reported","Resolved",days(28),days(14),days(5),"Clarification received and reviewed."),
      ("CT-26036","INST-1005","Student grievance response delay","A student grievance appears to have remained without a documented response.","Student Grievance","Student Grievance Cell","M. Das","Medium","Recurring","Open",days(8),days(0),days(8),""),
      ("CT-26035","INST-1002","Library access hours","Request to review library opening hours during examination periods.","Infrastructure","Infrastructure Cell","A. Mehta","Low","First Reported","Closed",days(41),days(27),days(20),"Closed after the institution provided its schedule."),
      ("CT-26034","INST-1001","Workshop safety equipment availability","Safety equipment availability was raised in more than one report.","Infrastructure","Infrastructure Cell","A. Mehta","Medium","Repeated Pattern","In Progress",days(34),days(4),days(11),"Follow-up inspection details requested."),
      ("CT-26033","INST-1003","Faculty attendance record mismatch","A discrepancy was reported in the faculty attendance record.","Faculty","Academic Cell","R. Shah","High","Recurring","Open",days(5),days(-5),days(5),""),
      ("CT-26032","INST-1005","Grievance committee meeting records","Request for confirmation of grievance committee meeting records.","Student Grievance","Student Grievance Cell","M. Das","Medium","First Reported","Resolved",days(22),days(8),days(2),"Records reviewed.")]
    for row in cases:
        db.session.add(Complaint(id=row[0],institution_id=row[1],title=row[2],description=row[3],category=row[4],bureau=row[5],official=row[6],priority=row[7],frequency=row[8],status=row[9],received=row[10],due=row[11],updated=row[12],notes=row[13],score=35,related=False))
    db.session.commit()
    # The demo administrator is only a prototype identity. Login accepts any non-empty password.
    admin=User.query.filter_by(email="admin@demo.casetrack").first()
    if not admin: db.session.add(User(email="admin@demo.casetrack",name="CaseTrack Administrator",role="Administrator")); db.session.commit()
    for c in Complaint.query.all(): refresh_case_intelligence(c)
    db.session.commit()

@app.get("/api/health")
def health(): return jsonify(status="ok", service="CaseTrack 360 API", database="sqlite")

@app.post("/api/auth/login")
def login():
    payload=request.get_json(silent=True) or {}; email=str(payload.get("email", "")).strip().lower(); password=str(payload.get("password", ""))
    display_name=str(payload.get("displayName", "")).strip()
    if not email or "@" not in email or not password: return jsonify(message="Enter a valid email address and a non-empty password."), 400
    user=User.query.filter_by(email=email).first()
    if not user:
        user=User(email=email, name=display_name or re.sub(r"[._-]+", " ", email.split("@")[0]).title(), role="Administrator")
        db.session.add(user); db.session.commit()
    elif display_name and user.email == "admin@demo.casetrack":
        user.name=display_name; db.session.commit()
    session.clear(); session["user_id"]=user.id; session["csrf_token"]=secrets.token_urlsafe(16)
    db.session.add(AuditLog(actor=user.name,action="login",entity_type="user",entity_id=str(user.id),detail="Prototype session started")); db.session.commit()
    return jsonify(user_json(user))

@app.get("/api/auth/me")
def me():
    user=current_user()
    if not user: return jsonify(message="Please sign in."), 401
    return jsonify(user_json(user))

@app.post("/api/auth/logout")
def logout():
    user=current_user()
    if user: db.session.add(AuditLog(actor=user.name,action="logout",entity_type="user",entity_id=str(user.id),detail="Prototype session ended")); db.session.commit()
    session.clear(); return "", 204

@app.get("/api/complaints")
@login_required
def list_complaints():
    q=Complaint.query.join(Institution)
    search=request.args.get("q", "").strip()
    if search:
        like=f"%{search}%"; q=q.filter(or_(Complaint.id.ilike(like),Complaint.title.ilike(like),Complaint.description.ilike(like),Complaint.category.ilike(like),Complaint.bureau.ilike(like),Institution.name.ilike(like),Institution.id.ilike(like)))
    for arg,field in [("status",Complaint.status),("priority",Complaint.priority),("frequency",Complaint.frequency),("bureau",Complaint.bureau),("category",Complaint.category),("institutionId",Complaint.institution_id)]:
        val=request.args.get(arg)
        if val: q=q.filter(field==val)
    records=q.order_by(Complaint.received.desc(),Complaint.created_at.desc()).all()
    return jsonify([complaint_json(c) for c in records])

@app.get("/api/complaints/<string:complaint_id>")
@login_required
def get_complaint(complaint_id):
    c=db.session.get(Complaint,complaint_id)
    if not c: return jsonify(message="Complaint not found."),404
    return jsonify(complaint_json(c))

@app.post("/api/complaints")
@login_required
def create_complaint():
    p=request.get_json(silent=True) or {}
    required=["institutionId","title","description","received"]
    missing=[field for field in required if not str(p.get(field," ")).strip()]
    if missing: return jsonify(message="Required fields missing: "+", ".join(missing)),400
    inst=db.session.get(Institution,str(p["institutionId"]))
    if not inst: return jsonify(message="Select an institution that exists in the directory."),400
    if p.get("priority","Medium") not in PRIORITIES: return jsonify(message="Invalid priority."),400
    if p.get("status","Open") not in STATUSES: return jsonify(message="Invalid status."),400
    received=parse_date(p.get("received"))
    if not received: return jsonify(message="Date received must be a valid YYYY-MM-DD date."),400
    today=date.today(); suffix=Complaint.query.count()+1
    while True:
        cid=f"CT-{today.strftime('%y%m')}{suffix:03d}"
        if not db.session.get(Complaint,cid): break
        suffix+=1
    c=Complaint(id=cid,institution_id=inst.id,title=str(p["title"]).strip(),description=str(p["description"]).strip(),category=p.get("category","Other") if p.get("category") in CATEGORIES else "Other",bureau=str(p.get("bureau","Unassigned")),official=str(p.get("official","Unassigned")),priority=p.get("priority","Medium"),frequency=p.get("frequency","First Reported") if p.get("frequency") in FREQUENCIES else "First Reported",status=p.get("status","Open"),received=received.isoformat(),due=(parse_date(p.get("due")).isoformat() if parse_date(p.get("due")) else ""),updated=iso_today(),notes=str(p.get("notes","")))
    db.session.add(c); db.session.flush(); refresh_case_intelligence(c); record_history(c,"created","Complaint registered"); db.session.commit()
    return jsonify(complaint_json(c)),201

@app.patch("/api/complaints/<string:complaint_id>")
@login_required
def update_complaint(complaint_id):
    c=db.session.get(Complaint,complaint_id)
    if not c: return jsonify(message="Complaint not found."),404
    p=request.get_json(silent=True) or {}; changes=[]
    allowed={"title","description","category","bureau","official","priority","frequency","status","received","due","notes"}
    for key in allowed:
        if key not in p: continue
        value=p[key]
        if key=="priority" and value not in PRIORITIES: return jsonify(message="Invalid priority."),400
        if key=="status" and value not in STATUSES: return jsonify(message="Invalid status."),400
        if key=="frequency" and value not in FREQUENCIES: return jsonify(message="Invalid frequency classification."),400
        if key in {"received","due"}:
            parsed=parse_date(value)
            if value and not parsed: return jsonify(message=f"{key} must be a valid YYYY-MM-DD date."),400
            value=parsed.isoformat() if parsed else ""
        old=getattr(c,key)
        if old != value: changes.append(f"{key}: {old!s} → {value!s}"); setattr(c,key,value)
    c.updated=iso_today(); refresh_case_intelligence(c)
    record_history(c,"updated", "; ".join(changes) if changes else "Complaint reviewed; no field changes")
    db.session.commit(); return jsonify(complaint_json(c))

@app.get("/api/complaints/<string:complaint_id>/history")
@login_required
def complaint_history(complaint_id):
    if not db.session.get(Complaint,complaint_id): return jsonify(message="Complaint not found."),404
    rows=CaseHistory.query.filter_by(complaint_id=complaint_id).order_by(CaseHistory.created_at.desc()).all()
    return jsonify([{"id":x.id,"actor":x.actor,"action":x.action,"detail":x.detail,"createdAt":x.created_at.isoformat()} for x in rows])

@app.get("/api/institutions")
@login_required
def list_institutions():
    return jsonify([institution_json(i) for i in Institution.query.order_by(Institution.name).all()])

@app.post("/api/institutions")
@login_required
def create_institution():
    p=request.get_json(silent=True) or {}; iid=str(p.get("id", "")).strip(); name=str(p.get("name", "")).strip()
    if not iid or not name: return jsonify(message="Institution ID and name are required."),400
    if db.session.get(Institution,iid): return jsonify(message="That institution ID already exists."),409
    i=Institution(id=iid,name=name,type=str(p.get("type","Other")),state=str(p.get("state","")),city=str(p.get("city","")),status=str(p.get("status","Active")))
    db.session.add(i); db.session.add(AuditLog(actor=actor_name(),action="created",entity_type="institution",entity_id=iid,detail=f"Institution {name} added")); db.session.commit()
    return jsonify(institution_json(i)),201

@app.get("/api/related-cases")
@login_required
def list_related_cases():
    rows=RelatedCase.query.order_by(RelatedCase.confidence.desc()).all(); out=[]
    for r in rows:
        a=db.session.get(Complaint,r.complaint_a); b=db.session.get(Complaint,r.complaint_b)
        if a and b: out.append({"id":r.id,"complaintA":complaint_json(a),"complaintB":complaint_json(b),"reason":r.reason,"confidence":r.confidence,"reviewed":r.reviewed})
    return jsonify(out)

@app.post("/api/related-cases/<int:related_id>/review")
@login_required
def review_related_case(related_id):
    r=db.session.get(RelatedCase,related_id)
    if not r: return jsonify(message="Related-case suggestion not found."),404
    r.reviewed=True; db.session.add(AuditLog(actor=actor_name(),action="reviewed",entity_type="related_case",entity_id=str(r.id),detail="Potential relationship reviewed; records remain separate")); db.session.commit()
    return jsonify(id=r.id,reviewed=True)

@app.get("/api/analytics")
@login_required
def analytics():
    cases=Complaint.query.all(); today=date.today(); active=[c for c in cases if c.status in ACTIVE_STATUSES]
    return jsonify({"total":len(cases),"open":sum(c.status=="Open" for c in cases),"inProgress":sum(c.status=="In Progress" for c in cases),"pending":sum(c.status=="Pending" for c in cases),"resolved":sum(c.status=="Resolved" for c in cases),"closed":sum(c.status=="Closed" for c in cases),"overdue":sum(bool(parse_date(c.due) and parse_date(c.due)<today and c.status in ACTIVE_STATUSES) for c in cases),"highPriority":sum(c.priority in {"High","Critical"} and c.status in ACTIVE_STATUSES for c in cases),"averageAttentionScore":round(sum(c.score for c in cases)/len(cases)) if cases else 0})

@app.post("/api/complaints/<string:complaint_id>/handovers")
@login_required
def create_handover(complaint_id):
    c=db.session.get(Complaint,complaint_id)
    if not c: return jsonify(message="Complaint not found."),404
    p=request.get_json(silent=True) or {}; target=str(p.get("toBureau", "")).strip(); reason=str(p.get("reason", "")).strip()
    if not target or not reason: return jsonify(message="Destination bureau and handover reason are required."),400
    h=Handover(complaint_id=c.id,from_bureau=c.bureau,to_bureau=target,reason=reason,created_by=actor_name())
    db.session.add(h); record_history(c,"handover_requested",f"Handover requested from {c.bureau} to {target}: {reason}"); db.session.commit()
    return jsonify(id=h.id,complaintId=h.complaint_id,fromBureau=h.from_bureau,toBureau=h.to_bureau,reason=h.reason,status=h.status,createdBy=h.created_by,createdAt=h.created_at.isoformat()),201

@app.get("/api/audit-logs")
@login_required
def audit_logs():
    rows=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify([{"id":x.id,"actor":x.actor,"action":x.action,"entityType":x.entity_type,"entityId":x.entity_id,"detail":x.detail,"createdAt":x.created_at.isoformat()} for x in rows])

@app.errorhandler(404)
def not_found(_): return jsonify(message="Endpoint or record not found."),404
@app.errorhandler(500)
def internal_error(_): db.session.rollback(); return jsonify(message="Unexpected server error. Check the Flask terminal for details."),500


from routes.extra_features import register_extra_routes

register_extra_routes(
    app,
    db,
    {
        "Complaint": Complaint,
        "Institution": Institution,
        "CaseHistory": CaseHistory,
        "AuditLog": AuditLog,
        "RelatedCase": RelatedCase,
        "Handover": Handover,
    },
    {
        "login_required": login_required,
        "actor_name": actor_name,
        "record_history": record_history,
        "refresh_case_intelligence": refresh_case_intelligence,
        "related_reason": related_reason,
        "iso_today": iso_today,
    },
)


with app.app_context():
    db.create_all()
    seed_database()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG", "false").lower()=="true")
