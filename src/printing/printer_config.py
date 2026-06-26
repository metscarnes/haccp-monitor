"""
printer_config.py — Configuration dynamique de l'imprimante Brother QL.

Priorité de lecture : printer_config.json > variables d'environnement > défauts.
Le fichier JSON est écrit par l'API lorsque l'utilisateur modifie l'IP depuis l'UI.
"""

import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "printer_config.json"

_DEFAULTS = {
    "model":      "QL-820NWB",
    "backend":    "network",
    "identifier": "tcp://192.168.1.56",
}


def get_printer_config() -> dict:
    """Retourne la config imprimante active (model, backend, identifier)."""
    cfg = dict(_DEFAULTS)
    # Variables d'environnement surchargent les défauts
    if v := os.getenv("BROTHER_QL_MODEL"):   cfg["model"] = v
    if v := os.getenv("BROTHER_QL_BACKEND"): cfg["backend"] = v
    if v := os.getenv("BROTHER_QL_PRINTER"): cfg["identifier"] = v
    # Fichier JSON surcharge tout (modifié depuis l'UI)
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update({k: v for k, v in saved.items() if k in _DEFAULTS})
        except Exception:
            pass
    return cfg


def save_printer_config(identifier: str, model: str | None = None, backend: str | None = None) -> dict:
    """Sauvegarde la configuration et retourne la config complète."""
    cfg = get_printer_config()
    cfg["identifier"] = identifier.strip()
    if model:   cfg["model"] = model.strip()
    if backend: cfg["backend"] = backend.strip()
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg
