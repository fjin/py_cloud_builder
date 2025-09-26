from sqlalchemy import Column, Integer, String, JSON, DateTime
from database import Base
from datetime import datetime

class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    application_name = Column(String, nullable=False)
    task_name = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)
    uuid = Column(String, index=True, nullable=False)


class Step(Base):
    __tablename__ = "steps"
    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String, nullable=False)
    step_name = Column(String, nullable=False)
    status = Column(JSON, nullable=False)  # Stores the full result dictionary as JSON
    uuid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)  # New timestamp column


class Application(Base):
    __tablename__ = "applications"
    uuid = Column(String, primary_key=True, index=True)
    application_name = Column(String, nullable=False)
    action = Column(String, nullable=False)  # e.g., "build" or "unbuild"
    status = Column(String, nullable=False)  # e.g., "started", "failed", "success"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    tasks_built = Column(JSON, nullable=True)  # New field: list of tasks (resource names)
