import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import engine, Base
from app.database.models import Customer, Product, Order, OrderItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")


def init_db():
    logger.info("Initializing database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")


if __name__ == "__main__":
    init_db()
