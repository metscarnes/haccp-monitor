---
name: pi-deploiement-oom-reception
description: Le Pi de prod (512 Mo, Debian trixie) tuait le backend par OOM pendant les réceptions ("Failed to fetch") — causes et correctifs appliqués le 2026-07-30.
metadata:
  type: project
---

Déploiement prod : Raspberry Pi `ulysserasp` (512 Mo RAM, Debian **trixie** arm64), IP locale `192.168.1.83`, backend servi par systemd `haccp-backend.service` (venv `/home/campiglia/haccp-monitor/venv`, `uvicorn src.main:app`, 1 worker), reverse-proxy **Caddy** devant, remote git `metscarnes/haccp-monitor`. La tablette accède en direct par IP locale (pas de tunnel), le `.env` n'a ni `APP_URL` ni CORS.

**Symptôme :** erreurs « Failed to fetch » (≠ HTTP 502) pendant les réceptions. Diagnostic via `dmesg -T | grep -i oom` : `uvicorn` tué en boucle par l'OOM-killer, systemd le relançant → connexion coupée en plein POST → « Failed to fetch ». Détail clé : `total-vm` de 1,4–2,2 Go pour un `anon-rss` de seulement ~170 Mo = arènes malloc glibc gonflées par les threads (aggravé par `asyncio.to_thread` ajouté récemment).

**Correctifs appliqués (2026-07-30), qui ont marché :**
1. Drop-in systemd `/etc/systemd/system/haccp-backend.service.d/override.conf` → `Environment=MALLOC_ARENA_MAX=2`. Effet mesuré : VSZ tombé de ~2 Go à ~240 Mo. **Le plus gros levier.**
2. Swap zram actif (~416 Mo). Sur trixie, zram est déjà géré nativement par `zram-generator` → le paquet `zram-tools`/`zramswap.service` entre en collision (state "failed") mais le swap fonctionne quand même. Ne pas viser PERCENT>100 sur 512 Mo (contre-productif).
3. WiFi power-save OFF (`iw dev wlan0 set power_save off` + service oneshot au boot) — 2ᵉ cause de « Failed to fetch », indépendante de l'OOM.
4. Code : `_fichier_bl_vers_jpegs` borne désormais le zoom de rendu PDF à BL_MAX_SIDE px (au lieu d'un zoom fixe ×2) → évite un pixmap de 100+ Mo sur les PDF à grande mediabox. Cf. [[reception-ocr-bl-perf]].

**Why:** contrainte matérielle durable (512 Mo) non déductible du code ; ces réglages système vivent sur le Pi, pas dans le dépôt.
**How to apply:** si les « Failed to fetch » / OOM reviennent, vérifier d'abord `ps -C uvicorn -o rss,vsz,nlwp` (VSZ doit rester ~qq centaines de Mo), `swapon --show`, `iwconfig wlan0 | grep -i power`, et `dmesg -T | tail`. Prochain levier si besoin : baisser `BL_MAX_SIDE` 1920→1600 dans `src/api/routes_reception.py`.
