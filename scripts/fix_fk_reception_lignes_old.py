"""
fix_fk_reception_lignes_old.py
Répare les clés étrangères « fantômes » qui pointent vers des tables « *_old »
disparues (ex. reception_lignes_old), laissées par d'anciennes migrations
ALTER TABLE … RENAME TO …_old.

Symptôme corrigé :
    HTTP 422 — {"detail":"no such table: main.reception_lignes_old"}
    (module Fabrication : INSERT dans fabrication_lots avec foreign_keys=ON)

À lancer UNE SEULE FOIS sur le serveur, backend ARRÊTÉ :
    sudo systemctl stop haccp-backend
    cd ~/haccp-monitor && python3 scripts/fix_fk_reception_lignes_old.py
    sudo systemctl start haccp-backend

Méthode : réécriture directe du schéma (PRAGMA writable_schema) — aucune donnée
n'est déplacée, seules les définitions de FK erronées sont corrigées. Idempotent.
"""
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "haccp.db"


def main() -> None:
    print(f"Base : {DB_PATH}")
    if not DB_PATH.exists():
        print("ERREUR : base introuvable")
        return

    con = sqlite3.connect(DB_PATH)
    try:
        existing = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}

        rows = con.execute(
            r"SELECT name, sql FROM sqlite_master "
            r"WHERE type='table' AND sql LIKE '%\_old%' ESCAPE '\'"
        ).fetchall()

        to_fix = []
        for name, sql in rows:
            if not sql:
                continue
            dangling = {
                ref for ref in re.findall(r'REFERENCES\s+"?([A-Za-z0-9_]+_old)"?', sql)
                if ref not in existing
            }
            if dangling:
                to_fix.append((name, sql, dangling))

        if not to_fix:
            print("[OK] Aucune FK fantome '*_old' detectee - rien a faire.")
            _verify(con)
            return

        print(f"{len(to_fix)} table(s) a corriger :")
        con.execute("PRAGMA foreign_keys = OFF")
        con.execute("PRAGMA writable_schema = ON")
        for name, sql, dangling in to_fix:
            new_sql = sql
            for ref in sorted(dangling):
                new_sql = new_sql.replace(ref, ref[:-4])  # retire le suffixe « _old »
            con.execute(
                "UPDATE sqlite_master SET sql = ? WHERE type='table' AND name = ?",
                (new_sql, name),
            )
            print(f"  - {name} : {', '.join(sorted(dangling))} -> corrige")
        con.execute("PRAGMA writable_schema = OFF")
        con.commit()
        con.close()

        # Reouverture pour recharger le schema corrige et verifier.
        con = sqlite3.connect(DB_PATH)
        print("[OK] Reecriture terminee.")
        _verify(con)
    finally:
        con.close()


def _verify(con: sqlite3.Connection) -> None:
    print("--- integrity_check ---")
    for r in con.execute("PRAGMA integrity_check"):
        print(" ", r[0])
    print("--- foreign_key_check ---")
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        for r in fk:
            print(" ", r)
    else:
        print("  OK (aucune violation)")
    restant = con.execute(
        r"SELECT count(*) FROM sqlite_master WHERE sql LIKE '%reception_lignes_old%'"
    ).fetchone()[0]
    print(f"--- références reception_lignes_old restantes : {restant} ---")


if __name__ == "__main__":
    main()
