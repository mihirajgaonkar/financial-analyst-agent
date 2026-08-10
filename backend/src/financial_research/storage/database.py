from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from financial_research.config.settings import Settings, get_settings
from financial_research.storage.models import Base


def create_database_engine(database_url: str | None = None):
    settings = get_settings()
    return create_engine(database_url or settings.database_url, pool_pre_ping=True)


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=create_database_engine(database_url), autoflush=False, expire_on_commit=False)


def create_all_tables(database_url: str | None = None) -> None:
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)


def get_session(settings: Settings | None = None) -> Iterator[Session]:
    settings = settings or get_settings()
    factory = create_session_factory(settings.database_url)
    with factory() as session:
        yield session
