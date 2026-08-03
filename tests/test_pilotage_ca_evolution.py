"""
test_pilotage_ca_evolution.py — Comparaison CA par période (mois/semaine),
à périmètre égal quand la période courante est en cours.

Bug corrigé : un mois en cours (ex. 3 jours écoulés en août) ne doit pas être
comparé au total du mois précédent ENTIER (31 jours en juillet), mais
seulement aux N mêmes premiers jours de la période précédente.
"""
from datetime import date, timedelta

import pytest


async def _saisir_ca(client, iso, montant):
    r = await client.post("/api/achats/pilotage/ca", json={
        "date_ca": iso,
        "montant_ttc_matin": montant,
        "nb_tickets_matin": 10,
        "montant_ttc_soir": 0,
        "nb_tickets_soir": None,
    })
    assert r.status_code in (200, 201), r.text


@pytest.mark.anyio
async def test_evolution_mois_en_cours_perimetre_egal(app_client, db):
    """Mois courant partiel : l'évolution doit comparer contre les mêmes N
    premiers jours du mois précédent, pas le mois précédent entier."""
    today = date.today()
    debut_mois = today.replace(day=1)
    nb_jours_ecoules = (today - debut_mois).days + 1  # inclusif

    # Mois précédent : 1er jour à 100€, tous les autres jours (y compris au-delà
    # de nb_jours_ecoules) à 1000€ pour vérifier qu'ils sont bien EXCLUS.
    mois_prec_fin = debut_mois - timedelta(days=1)
    mois_prec_debut = mois_prec_fin.replace(day=1)

    total_attendu_tronque = 0.0
    d = mois_prec_debut
    while d <= mois_prec_fin:
        offset = (d - mois_prec_debut).days
        montant = 100.0 if offset < nb_jours_ecoules else 1000.0
        await _saisir_ca(app_client, d.isoformat(), montant)
        if offset < nb_jours_ecoules:
            total_attendu_tronque += montant
        d += timedelta(days=1)

    # Mois courant : jours écoulés jusqu'à aujourd'hui, 50€/jour.
    total_courant = 0.0
    d = debut_mois
    while d <= today:
        await _saisir_ca(app_client, d.isoformat(), 50.0)
        total_courant += 50.0
        d += timedelta(days=1)

    r = await app_client.get("/api/achats/pilotage/ca/stats/par-periode?granularite=mois&limit=5")
    assert r.status_code == 200, r.text
    lignes = r.json()["lignes"]

    courant = next(l for l in lignes if l["periode"] == debut_mois.strftime("%Y-%m"))
    assert courant["total_ttc"] == pytest.approx(total_courant, abs=0.01)

    # L'évolution doit être calculée contre le total tronqué (périmètre égal),
    # pas contre le total complet du mois précédent (qui inclurait les 1000€).
    attendu_delta = round(total_courant - total_attendu_tronque, 2)
    assert courant["evolution"]["delta"] == pytest.approx(attendu_delta, abs=0.01)
