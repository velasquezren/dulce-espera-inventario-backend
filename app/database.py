from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings
import logging
import re

logger = logging.getLogger("uvicorn")
masked_url = re.sub(r":([^@]+)@", ":*****@", settings.database_url)
logger.info(f"Conectando a base de datos: {masked_url}")

# pool_pre_ping=True tests the connection before sending queries,
# preventing "MySQL server has gone away" errors.
# pool_recycle=3600 recycles connections after an hour.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
