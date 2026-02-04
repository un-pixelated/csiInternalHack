import json
import random
import time
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Auth libs
from jose import jwt, JWTError
from passlib.context import CryptContext

# Setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "CSI"
ALGORITHM = "HS256"

# Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./game_data.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

class GameSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer)
    difficulty_mode = Column(String)
    timestamp = Column(Float)

Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
WORDS_DATA = []

# Load Data
try:
    with open("game_words.json", "r") as f:
        WORDS_DATA = json.load(f)
    print(f"Loaded {len(WORDS_DATA)} words.")
except:
    print("WARNING: game_words.json not found. Run trainer.py first!")
    WORDS_DATA = [{"word": "test", "difficulty": 0.1}, {"word": "example", "difficulty": 0.5}]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AuthModel(BaseModel):
    username: str
    password: str

class SubmitScore(BaseModel):
    score: int
    mode: str

#ENDPOINTS

@app.post("/auth/register")
def register(user_data: AuthModel, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username taken")
    
    hashed = pwd_context.hash(user_data.password)
    new_user = User(username=user_data.username, password_hash=hashed)
    db.add(new_user)
    db.commit()
    return {"msg": "User created"}

@app.post("/auth/login")
def login(user_data: AuthModel, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if not db_user or not pwd_context.verify(user_data.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token_data = {"sub": db_user.username}
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

# In main.py, replace the get_next_word function with this:

@app.get("/game/next_word")
def get_next_word(mode: str = "medium", seen_ids: Optional[str] = Query(None)):
    # 1. Define Difficulty Ranges
    ranges = {"easy": (0.0, 0.4), "medium": (0.3, 0.7), "hard": (0.6, 1.0)}
    min_d, max_d = ranges.get(mode, (0.3, 0.7))
    
    # 2. Filter Candidates based on difficulty
    candidates = [w for w in WORDS_DATA if min_d <= w['difficulty'] <= max_d]
    
    # Fallback: if no words match difficulty, use all words
    if not candidates: 
        candidates = WORDS_DATA
    
    # Fallback: if WORDS_DATA was empty to begin with
    if not candidates:
        return {"word": "Error: No Data", "difficulty": 0, "time_limit": 5, "is_memory_test": False}

    # 3. Process Seen List (Handle empty strings safely)
    seen_list = []
    if seen_ids and len(seen_ids.strip()) > 0:
        seen_list = seen_ids.split(",")
    
    # 4. Decide if this is a memory test
    # 30% chance to test memory, ONLY if we have seen at least 3 words
    should_test_memory = (random.random() < 0.3) if len(seen_list) > 3 else False
        
    word_obj = None
    is_seen = False
    
    if should_test_memory:
        target_str = random.choice(seen_list)
        matches = [w for w in WORDS_DATA if w['word'] == target_str]
        if matches:
            word_obj = matches[0]
            is_seen = True
    
    # 5. If not testing memory (or word not found), pick a new word
    if not word_obj:
        word_obj = random.choice(candidates)
        is_seen = False

    # 6. Calculate Time Limit
    base_time = 3.0
    extra_time = word_obj['difficulty'] * 2.5 
    total_time = round(base_time + extra_time, 1)

    return {
        "word": word_obj['word'],
        "difficulty": word_obj['difficulty'],
        "time_limit": total_time,
        "is_memory_test": is_seen 
    }

@app.get("/leaderboard")
def get_leaderboard_data(db: Session = Depends(get_db)):
    # Query returns a tuple: (GameSession Object, Username String)
    results = db.query(GameSession, User.username)\
        .join(User)\
        .order_by(GameSession.score.desc())\
        .limit(10)\
        .all()
    
    # FIXED: 'u_name' is just a string, it doesn't have a .username attribute
    return [
        {"username": u_name, "score": session.score, "mode": session.difficulty_mode} 
        for session, u_name in results
    ]

@app.post("/game/save")
def save_score(score_data: SubmitScore, token: str = Header(None), db: Session = Depends(get_db)):
    if not token: return {"msg": "Not logged in"}
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if user:
            new_score = GameSession(
                user_id=user.id, score=score_data.score, 
                difficulty_mode=score_data.mode, timestamp=time.time()
            )
            db.add(new_score)
            db.commit()
            return {"status": "success"}
    except JWTError:
        pass
    return {"status": "error", "msg": "Invalid token"}

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_homepage():
    return FileResponse('static/homepage.html')

@app.get("/game")
async def serve_game():
    return FileResponse('static/gamepage.html')

@app.get("/difficulty.html")
async def serve_difficulty():
    return FileResponse('static/difficulty.html')

#route name to match the link in gamepage.html
@app.get("/leaderboard.html")
async def serve_leaderboard():
    return FileResponse('static/leaderboard.html')
