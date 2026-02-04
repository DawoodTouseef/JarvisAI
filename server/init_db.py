"""
Database initialization script - creates all tables with the latest schema
Uses synchronous SQLite for simplicity
"""
from sqlalchemy import create_engine
from database.models import Base
import os
from pathlib import Path

# Get project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = os.path.join(BASE_DIR, "db")
os.makedirs(DB_DIR, exist_ok=True)

# Synchronous SQLite URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'jarvis.db')}"

def init_db():
    """Initialize database with all tables"""
    print("Initializing database...")
    print(f"Database location: {os.path.join(DB_DIR, 'jarvis.db')}")
    
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # Drop all tables first (WARNING: This deletes all data!)
    Base.metadata.drop_all(engine)
    print("✓ Dropped all existing tables")
    
    # Create all tables with new schema
    Base.metadata.create_all(engine)
    print("✓ Created all tables with new schema including metadata_json columns")
    
    print("\nDatabase initialization complete!")
    print("\nNew columns added:")
    print("  - tasks.metadata_json")
    print("  - calendar_events.metadata_json")
    print("  - notes.metadata_json")

if __name__ == "__main__":
    init_db()
