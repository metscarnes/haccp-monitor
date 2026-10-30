"""
test_ocr_facture.py — OCR des factures : lignes à la pièce de Saveurs d'Antoine.

Banc du 30/10/2026 sur 12 vraies factures Saveurs : sans consigne, les articles
facturés à la pièce (UF = BQT, SCHT…) ressortaient en « colis », et toute
quantité lue sur la mauvaise base (poids ↔ nombre de pièces) faussait la ligne,
puisque l'app recalcule montant = quantité × prix. Couvre, sans appel réseau :
- la consigne Saveurs ajoutée quand le fournisseur est reconnu (et pas sinon) ;
- le contrôle quantité × prix = montant imprimé, qui corrige la base ou signale.
"""
import json
import sys
import types

import pytest

import src.ocr_facture as ocr_facture


def _ligne(q, poids, pu, unite, mt):
    ligne = {"quantite": q, "poids_kg": poids, "prix_unitaire": pu,
             "unite_prix": unite, "montant_ht": mt}
    ocr_facture._controler_base_ligne(ligne)
    return ligne


def test_ligne_coherente_inchangee():
    # Cordon bleu : 2 pièces × 14,95 = 29,90 (poids 1,8 kg ignoré)
    l = _ligne(2, 1.8, 14.95, "piece", 29.90)
    assert (l["quantite"], l["unite_prix"], l["prix_suspect"], l["alerte_prix"]) == (2, "piece", False, None)
    # Au kilo : 2,760 kg × 21,50 = 59,34
    l = _ligne(2.76, 2.76, 21.5, "kg", 59.34)
    assert (l["quantite"], l["unite_prix"], l["prix_suspect"]) == (2.76, "kg", False)


def test_poids_pris_pour_des_pieces_corrige_en_pieces():
    # Le cas signalé : article à la pièce lu avec le poids comme quantité, unité kg
    l = _ligne(1.8, 1.8, 14.95, "kg", 29.90)
    assert (l["quantite"], l["unite_prix"], l["prix_suspect"]) == (2.0, "piece", False)
    assert "pièce" in l["alerte_prix"]


def test_pieces_prises_pour_le_poids_corrige_en_kg():
    # Article au kilo lu avec le nombre de pièces (3) au lieu du poids (5,998 kg)
    l = _ligne(3, 5.998, 10.95, "piece", 65.68)
    assert (l["quantite"], l["unite_prix"], l["prix_suspect"]) == (5.998, "kg", False)
    assert "kg" in l["alerte_prix"]
    # Même erreur mais unité déjà kg : seule la quantité est recalée, sans alerte
    l = _ligne(3, 5.998, 10.95, "kg", 65.68)
    assert (l["quantite"], l["unite_prix"], l["alerte_prix"]) == (5.998, "kg", None)


def test_incoherent_signale_sans_rien_inventer():
    l = _ligne(2.3, None, 14.95, "kg", 41.17)
    assert l["prix_suspect"] is True
    assert l["quantite"] == 2.3 and l["unite_prix"] == "kg"


def test_gratuit_ou_sans_prix_pas_d_alerte():
    assert _ligne(1, 2.6, 0.0, "kg", 0.0)["prix_suspect"] is False
    assert _ligne(1, None, None, "kg", 12.0)["prix_suspect"] is False


# ── Appel complet avec client Anthropic simulé ──────────────────────────────

_REPONSE = {
    "fournisseur": "SAVEURS D'ANTOINE - YVAS", "numero_facture": "0770580",
    "date_facture_brut": "30/10/2026", "type_document": "facture",
    "lignes": [
        {"designation": "Cordon bleu comte", "reference": "009300", "quantite": 1.8,
         "poids_kg": 1.8, "prix_unitaire": 14.95, "unite_prix": "kg", "montant_ht": 29.90,
         "tva_pct": 5.5, "confiance": "haute"},
        {"designation": "Comte 10/18M", "reference": "022262", "quantite": 2.76,
         "poids_kg": 2.76, "prix_unitaire": 21.5, "unite_prix": "kg", "montant_ht": 59.34,
         "tva_pct": 5.5, "confiance": "haute"},
    ],
    "annexes": [], "recap_tva": [{"taux": 5.5, "base_ht": 89.24, "tva": 4.91}],
    "total_ht": 89.24, "total_tva": 4.91, "total_ttc": 94.15,
}


@pytest.fixture
def appels(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    vus = []

    class _Flux:
        def __init__(self, kwargs):
            vus.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_final_message(self):
            bloc = types.SimpleNamespace(type="text", text=json.dumps(_REPONSE))
            return types.SimpleNamespace(content=[bloc], stop_reason="end_turn",
                                         usage=types.SimpleNamespace(input_tokens=1000, output_tokens=500))

    class Anthropic:
        def __init__(self, **kw):
            self.messages = types.SimpleNamespace(stream=lambda **kwargs: _Flux(kwargs))

    monkeypatch.setitem(sys.modules, "anthropic",
                        types.SimpleNamespace(Anthropic=Anthropic, APIError=Exception))
    return vus


def _texte(appel):
    return appel["messages"][0]["content"][-1]["text"]


def test_consigne_saveurs_et_correction(appels):
    data = ocr_facture.extraire_facture([b"jpeg"], "Saveurs d'Antoine")
    assert "SAVEURS D'ANTOINE" in _texte(appels[0])
    assert "LA COLONNE UF DÉCIDE" in _texte(appels[0])
    assert appels[0]["output_config"]["effort"] == ocr_facture.EFFORT
    assert data["_meta"]["consigne_fournisseur"] == "saveurs"
    cordon, comte = data["lignes"]
    assert (cordon["quantite"], cordon["unite_prix"]) == (2.0, "piece")
    assert (comte["quantite"], comte["unite_prix"], comte["alerte_prix"]) == (2.76, "kg", None)
    assert data["total_ht"] == 89.24


def test_sans_fournisseur_connu_pas_de_consigne(appels):
    data = ocr_facture.extraire_facture([b"jpeg"], "Bourdicaud")
    assert "SAVEURS D'ANTOINE" not in _texte(appels[0])
    assert data["_meta"]["consigne_fournisseur"] is None
    ocr_facture.extraire_facture([b"jpeg"])
    assert "SAVEURS D'ANTOINE" not in _texte(appels[1])
