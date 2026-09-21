import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DB = os.getenv("MYSQL_DB", "vtuva")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

# Helper function to create engine with fallback if MySQL is not accessible
def init_engine():
    try:
        # Try connecting to MySQL
        server_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
        server_engine = create_engine(server_url, pool_pre_ping=True, echo=False)
        with server_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}`"))
            conn.commit()
        
        main_engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
        # Test connection
        with main_engine.connect() as conn:
            pass
        print(f"[Database] Successfully connected to MySQL database `{MYSQL_DB}` on {MYSQL_HOST}:{MYSQL_PORT}")
        return main_engine
    except Exception as e:
        print(f"[Database Warning] MySQL connection failed ({e}). Falling back to SQLite for development.")
        sqlite_db_path = ROOT_DIR / "vtuva.db"
        sqlite_url = f"sqlite:///{sqlite_db_path}"
        return create_engine(sqlite_url, connect_args={"check_same_thread": False}, echo=False)

engine = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
