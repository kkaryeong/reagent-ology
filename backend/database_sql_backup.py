"""Database setup for the reagent-ology backend."""
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'reagentology.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create database tables if they do not exist yet."""
    from . import models  # Import inside to avoid circular dependency

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        columns = {
            row["name"]
            for row in conn.execute(text("PRAGMA table_info(reagents)"))
        }
        if "density" not in columns:
            conn.execute(text("ALTER TABLE reagents ADD COLUMN density FLOAT"))
        if "volume_ml" not in columns:
            conn.execute(text("ALTER TABLE reagents ADD COLUMN volume_ml FLOAT"))
        if "nfc_tag_uid" not in columns:
            conn.execute(text("ALTER TABLE reagents ADD COLUMN nfc_tag_uid VARCHAR(128)"))
        if "scale_device" not in columns:
            conn.execute(text("ALTER TABLE reagents ADD COLUMN scale_device VARCHAR(128)"))

        index_names = {
            row["name"]
            for row in conn.execute(text("PRAGMA index_list('reagents')"))
        }
        if "idx_reagents_nfc_tag_uid" not in index_names:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_reagents_nfc_tag_uid "
                    "ON reagents(nfc_tag_uid) WHERE nfc_tag_uid IS NOT NULL"
                )
            )
