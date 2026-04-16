"""
app/base.py
===========
Declares the SQLAlchemy ORM DeclarativeBase shared by ALL models.

WHY this file exists (not just declared inside database.py):
  importing app.database creates the async engine immediately at module level,
  which requires asyncpg to be installed.  Alembic's env.py uses a synchronous
  psycopg2 connection and shouldn't need asyncpg at import time.

  By keeping Base here, both the application (app.database) and Alembic
  (alembic/env.py) can import it without triggering engine creation.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
