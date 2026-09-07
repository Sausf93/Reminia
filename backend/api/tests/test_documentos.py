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

    # Lista por persona (metadatos): accesible a la integradora.
    lst = (await client.get(f"/documentos?usuario_final_id={uid}", headers=headers)).json()
    assert len(lst) == 1 and lst[0]["id"] == doc["id"]

    # Descarga del contenido (PII): SOLO admin_centro.
    admin = await _login(client, ADMIN)
    cont = (await client.get(f"/documentos/{doc['id']}/contenido", headers=admin)).json()
    assert cont["contenido_b64"] == contenido

    # Borrado: SOLO admin_centro (destruir prueba legal es acción controlada).
    assert (await client.delete(f"/documentos/{doc['id']}", headers=admin)).status_code == 204
    assert (await client.get(f"/documentos/{doc['id']}/contenido", headers=admin)).status_code == 404


@pytest.mark.asyncio
async def test_descargar_y_borrar_documento_requieren_admin(client):
    """Una integradora sube y ve el listado, pero NO descarga ni borra: la salida
    de PII (DNI en consentimientos/DPA) y su destrucción son de admin_centro
    (ronda 19). Blinda además una tablet perdida (solo acuña sesión de integradora)."""
    integradora = await _login(client, INTEGRADORA)
    admin = await _login(client, ADMIN)
    c = base64.b64encode(b"%PDF-1.4 dpa").decode()

    # La integradora NO puede subir un DPA (documento legal del centro) -> 403.
    assert (await client.post("/documentos", headers=integradora, json={
        "tipo": "dpa", "nombre_archivo": "dpa.pdf", "mime": "application/pdf",
        "contenido_b64": c,
    })).status_code == 403
    # Lo sube el admin.
    doc = (await client.post("/documentos", headers=admin, json={
        "tipo": "dpa", "nombre_archivo": "dpa.pdf", "mime": "application/pdf",
        "contenido_b64": c,
    })).json()

    # Integradora: puede ver el listado (metadatos)...
    assert any(d["id"] == doc["id"]
               for d in (await client.get("/documentos?solo_centro=true",
                                           headers=integradora)).json())
    # ...pero NO descargar el contenido ni borrar.
    assert (await client.get(f"/documentos/{doc['id']}/contenido",
                             headers=integradora)).status_code == 403
    assert (await client.delete(f"/documentos/{doc['id']}",
                                headers=integradora)).status_code == 403

    # Admin sí: descarga y borra.
    admin = await _login(client, ADMIN)
    assert (await client.get(f"/documentos/{doc['id']}/contenido",
                             headers=admin)).status_code == 200
    assert (await client.delete(f"/documentos/{doc['id']}", headers=admin)).status_code == 204


@pytest.mark.asyncio
async def test_tipo_invalido_y_documento_centro(client):
    headers = await _login(client, ADMIN)  # el DPA lo sube admin_centro
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
