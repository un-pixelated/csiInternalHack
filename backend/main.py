import json
import random
import os
import time
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session

#Auth libs
from jose import jwt, JWTError
from passlib.context import CryptContext

#Setup
app = FastAPI()

#Enable CORS for local testing with React/Vue
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
   allow_methods=["*"],
    allow_headers=["*"],
)

#KEYS (hardcoded for now, move to environment later)
SECRET_KEY = "CSI"
ALGORITHM = "HS256"

#Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./game_data.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

#Models
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

#Load the data on startup
try:
    with open("game_words.json", "r") as f:
        WORDS_DATA = json.load(f)
    print(f"Loaded {len(WORDS_DATA)} words.")
except:
    print("WARNING: text file (game_words.json) not found. Generating dummy data.")
    WORDS_DATA = [{"word": "test", "difficulty": 0.1}, {"word": "example", "difficulty": 0.5}]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#To interact with frontend
class RegisterModel(BaseModel):
    username: str
    password: str

class SubmitScore(BaseModel):
    score: int
    mode: str

#Endpoints

@app.post("/auth/register")
def register(user: RegisterModel, db: Session = Depends(get_db)):
    # Check if user exists
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username taken")
    
    hashed = pwd_context.hash(user.password)
    new_user = User(username=user.username, password_hash=hashed)
    db.add(new_user)
    db.commit()
    return {"msg": "User created"}

@app.post("/auth/login")
def login(user: RegisterModel, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create Token
    token_data = {"sub": db_user.username}
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/game/next_word")
def get_next_word(
    mode: str = "medium", 
    seen_ids: Optional[str] = Query(None) #Comma separated list of words seen
):
    """
    Returns a word based on difficulty mode.
    Mode 'hard' uses ML score > 0.7
    """
    #Logic for difficulty ranges
    ranges = {
        "easy": (0.0, 0.4),
        "medium": (0.3, 0.7),
        "hard": (0.6, 1.0)
    }
    
    min_d, max_d = ranges.get(mode, (0.3, 0.7))
    
    #Filter words suitable for this mode
    candidates = [w for w in WORDS_DATA if min_d <= w['difficulty'] <= max_d]
    
    #Fallback if filter is too strict
    if not candidates:
        candidates = WORDS_DATA
        
    #Logic: 30% chance to show a word the user has already seen (Memory Check)
    #The frontend sends 'seen_ids' as "apple,dog,cat"
    seen_list = seen_ids.split(",") if seen_ids else []
    
    should_test_memory = False
    if len(seen_list) > 3:
        #random chance
        should_test_memory = (random.random() < 0.3)
        
    word_obj = None
    is_seen = False
    
    if should_test_memory:
        #Pick a word from the seen list, but we need to find its full object
        target_word_str = random.choice(seen_list)
        #Find it in the word dataset (inefficient search but fine for small lists)
        for w in WORDS_DATA:
            if w['word'] == target_word_str:
                word_obj = w
                is_seen = True
                break
    
    #If we didn't pick a seen word or couldn't find it, pick a new one
    if not word_obj:
        word_obj = random.choice(candidates)
        is_seen = False

    #Dynamic timer based on ML difficulty
    #Harder words might take user slightly more time to process
    base_time = 3.0 #default is seconds
    extra_time = word_obj['difficulty'] * 2.5 
    total_time = round(base_time + extra_time, 1)

    #Debug print-it wasn't working
    #print(f"Selected {word_obj['word']} (Diff: {word_obj['difficulty']}) -> {total_time}s")

    return {
        "word": word_obj['word'],
        "difficulty": word_obj['difficulty'],
        "time_limit": total_time,
        "is_memory_test": is_seen 
    }

@app.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    #Return top 10 scores
    #This query is a bit messy, assumes one score per session
    results = db.query(GameSession, User.username)\
        .join(User)\
        .order_by(GameSession.score.desc())\
        .limit(10)\
        .all()
    
    return [
        {"user": r.username, "score": s.score, "mode": s.difficulty_mode} 
        for s, r in results
    ]

@app.post("/game/save")
def save_score(
    score_data: SubmitScore, 
    token: str = Header(None), 
    db: Session = Depends(get_db)
):
    if not token:
        return {"msg": "Not logged in, score not saved"}
        
    try:
        #Decode token manually
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        
        if user:
            new_score = GameSession(
                user_id=user.id, 
                score=score_data.score, 
                difficulty_mode=score_data.mode,
                timestamp=time.time()
            )
            db.add(new_score)
            db.commit()
            return {"status": "success"}
    except JWTError:
        pass
        
    return {"status": "error", "msg": "Invalid token"}