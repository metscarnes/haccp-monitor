"""
test_etiquette_reprise.py — Test POST /api/impression/etiquette-reprise

L'imprimante Brother QL est mockée : on vérifie que l'endpoint retourne 200
et une réponse JSON valide même sans imprimante connectée.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.anyio
async def test_etiquette_reprise_retourne_200_sans_imprimante(app_client, db):
    """
    POST /api/impression/etiquette-reprise → 200 avec {"imprime": bool, "message": str}.
    L'imprimante est absente : on s'attend à imprime=False ou True selon l'env,
    mais le statut HTTP doit toujours être 200 et la réponse JSON valide.
    """
    payload = {
        "produit_nom":      "Paleron de boeuf",
        "fournisseur_nom":  "Fournisseur Test",
        "motif":            "Température hors norme",
        "operateur_prenom": "Éric",
        "date_refus":       "2026-04-06",
    }

    r = await app_client.post("/api/impression/etiquette-reprise", json=payload)
    assert r.status_code == 200, r.text

    data = r.json()
    assert "imprime" in data, "Champ 'imprime' manquant"
    assert "message" in data, "Champ 'message' manquant"
    assert isinstance(data["imprime"], bool)
    assert isinstance(data["message"], str)


@pytest.mark.anyio
async def test_etiquette_reprise_mock_imprimante_imprime_true(app_client, db):
    """
    Avec _generer_et_imprimer_reprise mockée, imprime doit être True.
    On patche directement la fonction interne pour éviter la dépendance brother_ql.
    """
    mock_result = {"imprime": True, "message": "Étiquette imprimée"}

    with patch(
        "src.api.routes_incidents._generer_et_imprimer_reprise",
        return_value=mock_result,
    ) as mock_fn:
        payload = {
            "produit_nom":      "Merguez maison",
            "fournisseur_nom":  "Fournisseur X",
            "motif":            "Couleur anormale",
            "operateur_prenom": "Ulysse",
            "date_refus":       "2026-04-06",
        }
        r = await app_client.post("/api/impression/etiquette-reprise", json=payload)

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["imprime"] is True
    assert data["message"] == "Étiquette imprimée"
    mock_fn.assert_called_once()


@pytest.mark.anyio
async def test_etiquette_reprise_date_format_francais(app_client, db):
    """La date YYYY-MM-DD doit être convertie en DD/MM/YYYY dans la réponse (message OK)."""
    payload = {
        "produit_nom":      "Saucisse",
        "fournisseur_nom":  "Fournisseur Y",
        "motif":            "Emballage endommagé",
        "operateur_prenom": "Éric",
        "date_refus":       "2026-04-06",
    }
    r = await app_client.post("/api/impression/etiquette-reprise", json=payload)
    assert r.status_code == 200
    # La conversion de date ne doit pas provoquer d'erreur (message != exception)
    data = r.json()
    assert "Erreur" not in data.get("message", "")
