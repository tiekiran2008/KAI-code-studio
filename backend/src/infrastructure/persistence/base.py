"""
Shared SQLAlchemy Declarative Base
===================================
All ORM models must import Base from here so they share the same metadata object,
enabling create_all() to provision every table in a single call.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
