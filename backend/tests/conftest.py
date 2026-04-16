"""
tests/conftest.py
==================
Global pytest configuration for the backend test suite.
Sets asyncio_mode=auto so all async tests run without @pytest.mark.asyncio.
"""
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from pgvector.sqlalchemy import Vector

@compiles(ARRAY, "sqlite")
def compile_array(element, compiler, **kw):
    return "TEXT"

@compiles(Vector, "sqlite")
def compile_vector(element, compiler, **kw):
    return "TEXT"

@compiles(UUID, "sqlite")
def compile_uuid(element, compiler, **kw):
    return "TEXT"

def pytest_configure(config):
    """Register custom asyncio mode."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
