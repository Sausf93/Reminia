"""Documentos legales: subir, listar, descargar y borrar; y aislamiento por centro."""
from __future__ import annotations

import base64

import pytest

INTEGRADORA = ("integradora@trazo.local", "trazo1234")
ADMIN = ("admin@trazo.local", "trazo1234")


async def _login(client, cred=INTEGRADORA):
    r = await client.post("/auth/login", data={"username": cred[0], "password": cred[1]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_subir_listar_descargar_borrar(client):
    headers = await _login(client)
    # Persona para asociar el consentimiento.
    uid = (await client.post("/usuarios", headers=headers, json={"alias_interno": "Doc Test"})).json()["id"]

    contenido = base64.b64encode(b"%PDF-1.4 consentimiento firmado").decode()
    r = await client.post("/documentos", headers=headers, json={
        "tipo": "consentimiento_uso", "usuario_final_id": uid,
        "version": "v1", "nombre_archivo": "consent.pdf",
        "mime": "application/pdf", "contenido_b64": contenido,
    })
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["tamano"] > 0 and "contenido_b64" not in doc  # metadatos, sin contenido

    # Lista por persona.
    lst = (await client.get(f"/documentos?usuario_final_id={uid}", headers=headers)).json()
    assert len(lst) == 1 and lst[0]["id"] == doc["id"]

    # Descarga el contenido.
    cont = (await client.get(f"/documentos/{doc['id']}/contenido", headers=headers)).json()
    assert cont["contenido_b64"] == contenido

    # Borrado: SOLO admin_centro (destruir prueba legal es acción controlada).
    admin = await _login(client, ADMIN)
    assert (await client.delete(f"/documentos/{doc['id']}", headers=admin)).status_code == 204
    assert (await client.get(f"/documentos/{doc['id']}/contenido", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_borrar_documento_requiere_admin(client):
    """Una integradora NO puede borrar un documento legal (DPA/consentimiento con
    DNI): destruirlo es irreversible y solo lo hace admin_centro (ronda 19)."""
    integradora = await _login(client, INTEGRADORA)
    c = base64.b64encode(b"%PDF-1.4 dpa").decode()
    doc = (await client.post("/documentos", headers=integradora, json={
        "tipo": "dpa", "nombre_archivo": "dpa.pdf", "mime": "application/pdf",
        "contenido_b64": c,
    })).json()

    # Integradora -> 403 (no puede borrar).
    r = await client.delete(f"/documentos/{doc['id']}", headers=integradora)
    assert r.status_code == 403, r.text
    # El documento sigue ahí.
    assert (await client.get(f"/documentos/{doc['id']}/contenido",
                             headers=integradora)).status_code == 200
    # Admin sí puede.
    admin = await _login(client, ADMIN)
    assert (await client.delete(f"/documentos/{doc['id']}", headers=admin)).status_code == 204


@pytest.mark.asyncio
async def test_tipo_invalido_y_documento_centro(client):
    headers = await _login(client)
    c = base64.b64encode(b"x").decode()
    # Tipo inválido -> 422.
    assert (await client.post("/documentos", headers=headers, json={
        "tipo": "inventado", "nombre_archivo": "x.pdf", "mime": "application/pdf", "contenido_b64": c,
    })).status_code == 422
    # Documento a nivel de centro (sin persona): DPA.
    r = await client.post("/documentos", headers=headers, json={
        "tipo": "dpa", "nombre_archivo": "dpa.pdf", "mime": "application/pdf", "contenido_b64": c,
    })
    assert r.status_code == 201, r.text
    solo_centro = (await client.get("/documentos?solo_centro=true", headers=headers)).json()
    assert any(d["tipo"] == "dpa" for d in solo_centro)
