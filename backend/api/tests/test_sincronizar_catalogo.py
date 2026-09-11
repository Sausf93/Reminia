"""Idempotencia de sincronizar_catalogo ante nombres DUPLICADOS en el JSON.

No hay UNIQUE en EjercicioCatalogo.nombre y el emparejamiento es por nombre: si el
JSON trae dos actividades con el mismo nombre, la 2ª debe ACTUALIZAR la 1ª, no
insertar otra fila (si no, se duplicaría en cada arranque).
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models import EjercicioCatalogo
from app.services import seed


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_nombre_duplicado_no_crea_dos_filas(db, monkeypatch):
    dup = [
        {"nombre": "Dup", "bloque": "praxias", "plantilla_tipo": "trazo",
         "parametros_json": {}, "estado": "validada"},
        {"nombre": "Dup", "bloque": "praxias", "plantilla_tipo": "trazo",
         "parametros_json": {"x": 2}, "estado": "validada"},
    ]
    monkeypatch.setattr(seed, "_ejercicios_semilla", lambda: dup)
    await seed.sincronizar_catalogo(db)
    await seed.sincronizar_catalogo(db)  # segundo "arranque": sigue una sola fila
    n = await db.scalar(
        select(func.count()).select_from(EjercicioCatalogo)
        .where(EjercicioCatalogo.nombre == "Dup"))
    assert n == 1
