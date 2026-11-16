"""Database setup and session management using SQLAlchemy 2.x."""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Base class for SQLAlchemy ORM models
Base = declarative_base()

# Lazy or configured engine
engine = None
SessionLocal = None


def get_engine(db_url: str = None):
    """Get or create SQLAlchemy Engine."""
    global engine, SessionLocal
    target_url = db_url or settings.effective_database_url
    if engine is None or str(engine.url) != target_url:
        connect_args = {}
        if target_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        engine = create_engine(
            target_url,
            pool_pre_ping=True,
            connect_args=connect_args,
            echo=False,
        )
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
    return engine


def get_session_factory(db_url: str = None) -> sessionmaker:
    """Return configured session factory."""
    global SessionLocal
    if SessionLocal is None:
        get_engine(db_url)
    return SessionLocal


def init_db(target_engine=None) -> None:
    """Initialize database tables using SQLAlchemy metadata."""
    # Ensure all ORM models are registered before create_all
    import app.entities.booking  # noqa: F401
    active_engine = target_engine or get_engine()
    Base.metadata.create_all(bind=active_engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a transactional database session."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
