import logging
from sqlalchemy import text
from src.db.session import engine
from src.db.models import Base

logger = logging.getLogger(__name__)

def init_db():
    """Initializes PostgreSQL database tables if they do not exist."""
    try:
        with engine.connect() as conn:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto";'))
            conn.commit()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # Attempt to create metadata directly if pgcrypto extension failed
        Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
