"""
report_generator.py — Génération des rapports PDF HACCP

Utilise WeasyPrint pour convertir un template Jinja2 en PDF.
Stub minimal — implémentation complète après le frontend.
"""

import hashlib
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.database import (
    get_enceintes, get_stats_releves, get_duree_depassements,
    get_alertes_enceinte, create_rapport, get_boutique,
)

logger = logging.getLogger(__name__)

BASE_DIR      = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "src" / "templates"
RAPPORTS_DIR  = BASE_DIR / "data" / "rapports"

jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


async def generer(db, boutique_id: int, type_rapport: str, debut: date, fin: date) -> int:
    """
    Génère le PDF du rapport et enregistre l'entrée en base.
    Retourne l'id du rapport créé.
    """
    boutique  = await get_boutique(db, boutique_id)
    enceintes = await get_enceintes(db, boutique_id)

    depuis   = datetime(debut.year, debut.month, debut.day, tzinfo=timezone.utc)
    jusqu_a  = datetime(fin.year,  fin.month,   fin.day, 23, 59, 59, tzinfo=timezone.utc)

    # Collecter les données par enceinte
    donnees_enceintes = []
    conforme_global   = True

    for enc in enceintes:
        eid   = enc["id"]
        stats = await get_stats_releves(db, eid, depuis, jusqu_a)
        alertes = await get_alertes_enceinte(db, eid, depuis)
        duree_depassement_s = await get_duree_depassements(db, eid, depuis, jusqu_a)

        non_conformites = [
            a for a in alertes
            if a["type"] in ("temperature_haute", "temperature_basse")
        ]
        conforme_enceinte = len(non_conformites) == 0
        if not conforme_enceinte:
            conforme_global = False

        donnees_enceintes.append({
            **enc,
            "stats": stats,
            "alertes": alertes,
            "non_conformites": non_conformites,
            "duree_depassement_minutes": duree_depassement_s // 60,
            "conforme": conforme_enceinte,
        })

    # Contexte template
    contexte = {
        "boutique": boutique,
        "enceintes": donnees_enceintes,
        "date_debut": debut,
        "date_fin": fin,
        "conforme": conforme_global,
        "genere_le": datetime.now(timezone.utc),
        "type_rapport": type_rapport,
    }

    # Rendu HTML → PDF
    template_name = f"rapport_{type_rapport}.html"
    try:
        template = jinja_env.get_template(template_name)
        html     = template.render(**contexte)
    except Exception as exc:
        logger.error("Erreur rendu template %s : %s", template_name, exc)
        html = f"<h1>Rapport {type_rapport}</h1><p>Erreur de rendu : {exc}</p>"

    RAPPORTS_DIR.mkdir(parents=True, exist_ok=True)
    nom_fichier = f"rapport_{type_rapport}_{boutique_id}_{debut}_{fin}.pdf"
    pdf_path    = RAPPORTS_DIR / nom_fichier
    sha256      = None
    html_path   = pdf_path.with_suffix(".html")

    # Sauvegarder le HTML d'abord (fallback)
    html_path.write_text(html, encoding="utf-8")

    # Essayer de générer un PDF avec WeasyPrint
    try:
        from weasyprint import HTML as WP_HTML
        WP_HTML(string=html).write_pdf(str(pdf_path))
        sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        logger.info("PDF généré avec WeasyPrint : %s", pdf_path)
    except ImportError:
        logger.info("WeasyPrint non disponible, tentative avec pdfkit")
    except Exception as exc:
        logger.warning("Erreur WeasyPrint : %s, tentative avec pdfkit", type(exc).__name__)

    # Essayer pdfkit comme fallback
    try:
        import pdfkit
        pdfkit.from_string(html, str(pdf_path))
        sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        logger.info("PDF généré avec pdfkit : %s", pdf_path)
    except ImportError:
        logger.info("pdfkit non disponible — utilisation du HTML")
        pdf_path = html_path
    except Exception as exc:
        logger.warning("Erreur pdfkit : %s — utilisation du HTML", type(exc).__name__)
        pdf_path = html_path

    rapport_id = await create_rapport(db, {
        "boutique_id":  boutique_id,
        "type":         type_rapport,
        "date_debut":   str(debut),
        "date_fin":     str(fin),
        "conforme":     conforme_global,
        "fichier_path": str(pdf_path),
        "sha256":       sha256,
    })

    return rapport_id
