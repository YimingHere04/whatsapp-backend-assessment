from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os

# 1. 数据库设置 (SQLite)[cite: 2]
DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SessionModel(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    agent = Column(String)
    last_active = Column(String)

class MessageModel(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    role = Column(String) # user or assistant[cite: 2]
    content = Column(Text)
    event_id = Column(String, unique=True, index=True) # 防止重复的唯一约束[cite: 2]

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. Token 验证[cite: 1]
def verify_token(authorization: str = Header(None)):
    expected_token = os.getenv("SECRET_TOKEN", "my_secret_token_123")
    if not authorization or authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="Unauthorized")

# 3. 核心逻辑：代理路由与回复生成[cite: 2]
def route_agent(message: str) -> str:
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in ["buy", "price", "product"]): return "sales"
    if any(kw in msg_lower for kw in ["problem", "issue", "complaint"]): return "support"
    return "general"

def generate_reply(agent: str) -> str:
    replies = {
        "sales": "Thanks for your interest. Can you share what you are looking for?",
        "support": "Sorry you are facing this issue. Can you describe it a bit more?",
        "general": "Happy to help. What would you like to know?"
    }
    return replies.get(agent, replies["general"])

app = FastAPI()

# 4. API 端点[cite: 1, 2, 3]
@app.post("/webhook/whatsapp", dependencies=[Depends(verify_token)])
async def webhook_whatsapp(payload: dict, db: Session = Depends(get_db)):
    event_id, user_id, message = payload.get("event_id"), payload.get("user_id"), payload.get("message")

    # 检查 event_id 是否重复[cite: 2]
    if db.query(MessageModel).filter(MessageModel.event_id == event_id).first():
        return {"status": "skipped", "reason": "duplicate event_id"}

    agent_type = route_agent(message)
    reply_content = generate_reply(agent_type)

    # 保存 Session 数据[cite: 2]
    new_session = SessionModel(user_id=user_id, agent=agent_type, last_active="now")
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # 保存 Messages 数据[cite: 2]
    db.add(MessageModel(session_id=new_session.id, role="user", content=message, event_id=event_id))
    db.add(MessageModel(session_id=new_session.id, role="assistant", content=reply_content, event_id=f"reply_{event_id}"))
    db.commit()

    return {"status": "success", "agent": agent_type, "reply": reply_content}

@app.post("/simulate")
async def simulate(payload: dict, db: Session = Depends(get_db)):
    # 供测试用的模拟端点，复用主逻辑[cite: 2]
    return await webhook_whatsapp(payload, db)

@app.get("/sessions")
def get_sessions(db: Session = Depends(get_db)):
    return db.query(SessionModel).all()

@app.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    return db.query(MessageModel).filter(MessageModel.session_id == session_id).all()