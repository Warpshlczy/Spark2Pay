"""
App Setting Model
Runtime-editable configuration overrides (API keys, provider, mode).
Stored locally in the instance database so a self-hosted instance can be
configured from the UI without touching .env.
"""
from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.models import Base


class AppSetting(Base):
    """A single configuration override, e.g. key='OPENAI_API_KEY'."""

    __tablename__ = 'app_settings'

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)

    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {'key': self.key, 'updated_at': self.updated_at.isoformat()
                if self.updated_at else None}

    def __repr__(self):
        return f'<AppSetting {self.key}>'
