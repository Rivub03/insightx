# app/db/base.py
#
# PURPOSE:
#   Declares the SQLAlchemy ORM base class.
#   All ORM models (datasource.py and any future models) inherit from Base.
#   Kept in its own file to avoid circular imports when models import from each other.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 declarative base.
    Using the class-based style (not the legacy declarative_base() function).
    """
    pass