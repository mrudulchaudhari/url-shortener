from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean, BigInteger as BI, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class Url(Base):
    """
    Represents a shortened URL mapping.
    Fields:
    -id: DB primary key, therefore BIGINTEGER
    - code: base63 or custom alias (unique)
    - original_url: original URL
    - created_at: creation timestamp
    - expires_at: optional expiry
    - is_active: toggles soft-deletion

    """
    __tablename__ = 'urls'
    id = Column(BI, primary_key=True)
    code = Column(String(32), unique=True, index=True, nullable=False)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)


class URLStats(Base):
    """
    Aggregated click stats for a URL.
    """
    __tablename__ = 'url_stats'
    url_id = Column(BI, ForeignKey('urls.id'), primary_key=True)
    total_clicks = Column(BI, default=0)
    last_flushed = Column(DateTime(timezone=True), nullable = True)
