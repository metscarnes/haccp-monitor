"""
test_ocr_bl.py — OCR des BL : réglages issus du banc chronométré (15/10/2026).

Couvre, sans appel réseau (client Anthropic simulé) :
- reconnaissance du fournisseur par son nom → consigne de mise en page ;
- une page = un appel, en parallèle, puis fusion (« (suite) » rattachée à
  l'article de la page précédente) ;
- sortie compacte remise au format complet attendu par le front ;
- redressement des BL Elivia (toujours reçus à l'horizontale) ;
- effort bas + modèle Sonnet 5.5 par défaut, post-traitement des dates conservé.
"""
import io
import json
import re
import sys
import threading
import types

import pytest
from PIL import Image

import src.ocr_bl as ocr_bl


def _jpeg(w=40, h=20):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="JPEG")
    return buf.getvalue()


class _FauxAnthropic:
    """Remplace le module anthropic : chaque appel renvoie les lignes de sa page."""

    def __init__(self, pages):
        self.pages = pages          # {numéro de page (1-based): réponse compacte}
        self.appels = []
        self._verrou = threading.Lock()
        faux = self

        class APIError(Exception):
            pass

        class _Flux:
            def __init__(self, kwargs):
                self.kwargs = kwargs

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get_final_message(self):
                contenu = self.kwargs["messages"][0]["content"]
                texte = contenu[-1]["text"]
                m = re.search(r"PAGE (\d+)/\d+", texte)
                page = int(m.group(1)) if m else 1
                images = [c for c in contenu if c["type"] == "image"]
                with faux._verrou:
                    faux.appels.append({"page": page, "texte": texte, "images": images, **self.kwargs})
                bloc = types.SimpleNamespace(type="text", text=json.dumps(faux.pages[page]))
                return types.SimpleNamespace(
                    content=[bloc], stop_reason="end_turn",
                    usage=types.SimpleNamespace(input_tokens=1000, output_tokens=500),
                )

        class _Messages:
            def stream(self, **kwargs):
                return _Flux(kwargs)

        class Anthropic:
            def __init__(self, **kwargs):
                self.messages = _Messages()

        self.module = types.SimpleNamespace(Anthropic=Anthropic, APIError=APIError)


def _ligne(d, dlc, kg, l=None, pu=10.0, mt=None):
    return {"d": d, "r": None, "l": l, "dlc": dlc, "dluo": None, "kg": kg, "q": 1,
            "pu": pu, "u": "kg", "mt": mt, "c": "h"}


@pytest.fixture
def faux(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    def installer(pages):
        f = _FauxAnthropic(pages)
        monkeypatch.setitem(sys.modules, "anthropic", f.module)
        return f
    return installer


@pytest.mark.parametrize("nom, cle", [
    ("Saveurs d'Antoine", "saveurs"),
    ("SAVEURS D'ANTOINE - YVAS", "saveurs"),
    ("Ets Bourdicaud", "bourdicaud"),
    ("DIPSA", "dipsa"),
    ("Elivia Selvi", "elivia"),
    ("Cooperl (Harang)", None),
    (None, None),
])
def test_cle_fournisseur(nom, cle):
    assert ocr_bl.cle_fournisseur(nom) == cle


def test_saveurs_multipage_parallele_et_fusion(faux):
    f = faux({
        1: {"f": "Saveurs d'Antoine", "bl": "0745721", "date": "11/06/26", "L": [
            _ligne("001295 Merguez veritable", "18/06/26", 4.56, mt=238.0),
        ]},
        2: {"f": None, "bl": None, "date": None, "L": [
            _ligne("(suite)", "25/06/26", 13.47),
            _ligne("001296 Saucisse cocktail", "02/07/26", 2.78, mt=40.31),
        ]},
    })
    data = ocr_bl.extraire_bl([_jpeg(), _jpeg()], "Saveurs d'Antoine")

    # une page = un appel, chacun avec la consigne Saveurs et une seule image
    assert sorted(a["page"] for a in f.appels) == [1, 2]
    for a in f.appels:
        assert len(a["images"]) == 1
        assert "SAVEURS D'ANTOINE" in a["texte"]
        assert a["model"] == "claude-sonnet-5-5"
        assert a["output_config"]["effort"] == "low"
        assert a["output_config"]["format"]["schema"] is ocr_bl._SCHEMA_COMPACT

    # fusion : en-tête de la page 1, « (suite) » rattachée à la merguez
    assert data["fournisseur"] == "Saveurs d'Antoine"
    assert data["numero_bl"] == "0745721"
    assert [l["designation"] for l in data["lignes"]] == [
        "001295 Merguez veritable", "001295 Merguez veritable", "001296 Saucisse cocktail"]

    # format complet restauré + post-traitement des dates conservé
    l0 = data["lignes"][0]
    assert set(ocr_bl._SCHEMA["properties"]["lignes"]["items"]["required"]) <= set(l0)
    assert l0["confiance"] == "haute"
    assert l0["dlc"] == "2026-06-18"
    assert data["lignes"][1]["dlc"] == "2026-06-25"
    assert data["_meta"]["pages"] == 2
    assert data["_meta"]["consigne_fournisseur"] == "saveurs"
    assert data["_meta"]["tokens_sortie"] == 1000


def test_elivia_redresse_et_page_unique(faux):
    f = faux({1: {"f": "Elivia", "bl": "01456458", "date": "03/08/2026", "L": [
        _ligne("BATEAU PAD BOVIN L", "26/08/2026", 8.253, l="AL60046992", pu=13.35),
    ]}})
    data = ocr_bl.extraire_bl([_jpeg(40, 20)], "ELIVIA SELVI ALENCON")

    assert len(f.appels) == 1
    assert "PAGE" not in f.appels[0]["texte"]          # pas de découpage pour 1 page
    assert "ELIVIA / SELVI" in f.appels[0]["texte"]
    import base64
    img = Image.open(io.BytesIO(base64.b64decode(f.appels[0]["images"][0]["source"]["data"])))
    assert img.size == (20, 40)                         # pivotée de 90°
    assert data["lignes"][0]["numero_lot"] == "AL60046992"


def test_fournisseur_inconnu_sans_consigne_ni_rotation(faux):
    f = faux({1: {"f": None, "bl": None, "date": None, "L": [_ligne("LONGE PORC", "16/07/26", 26.39)]}})
    ocr_bl.extraire_bl([_jpeg(40, 20)], "Cooperl")

    texte = f.appels[0]["texte"]
    assert "CONSIGNES SPÉCIFIQUES" not in texte
    import base64
    img = Image.open(io.BytesIO(base64.b64decode(f.appels[0]["images"][0]["source"]["data"])))
    assert img.size == (40, 20)
