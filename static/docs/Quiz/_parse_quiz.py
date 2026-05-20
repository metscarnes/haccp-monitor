"""Parse un quiz .docx (déjà dézippé) -> JSON structuré.

Usage : python _parse_quiz.py <dossier_extract> <numero_quiz> <theme> <sortie.json>
Le <dossier_extract> doit contenir word/document.xml
"""
import re
import json
import sys


def extraire_paragraphes(xml_path):
    with open(xml_path, "rb") as f:
        data = f.read().decode("utf-8")
    paras = re.split(r"</w:p>", data)
    out = []
    for p in paras:
        textes = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p)
        ligne = "".join(textes)
        ligne = (
            ligne.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&apos;", "'")
        )
        ligne = ligne.strip()
        if ligne:
            out.append(ligne)
    return out


RE_QUESTION_MARK = re.compile(r"^(\d+)\s*/\s*10$")
RE_OPTION = re.compile(r"^([A-D])\.\s*(.*)$", re.S)


def extraire_themes(paras):
    """Extrait la liste de la section finale « Thèmes abordés ».
    Retourne (themes, index_debut) ; index_debut = len(paras) si absente."""
    idx = next(
        (i for i, l in enumerate(paras)
         if l.lower().startswith("thèmes abordés") or l.lower().startswith("themes abordés")),
        None,
    )
    if idx is None:
        return [], len(paras)
    themes = [l for l in paras[idx + 1:] if l.strip()]
    return themes, idx


def parser(paras):
    # Isoler la section « Thèmes abordés » pour ne pas la mêler à Q10
    themes, idx_themes = extraire_themes(paras)
    paras = paras[:idx_themes]

    # Découpe en blocs par marqueur "N / 10"
    indices = [i for i, l in enumerate(paras) if RE_QUESTION_MARK.match(l)]
    blocs = []
    for k, start in enumerate(indices):
        end = indices[k + 1] if k + 1 < len(indices) else len(paras)
        blocs.append(paras[start:end])

    questions = []
    for bloc in blocs:
        num = int(RE_QUESTION_MARK.match(bloc[0]).group(1))
        # 1) énoncé = lignes après le marqueur jusqu'à la 1re option A.
        idx = 1
        enonce_parts = []
        while idx < len(bloc) and not RE_OPTION.match(bloc[idx]):
            enonce_parts.append(bloc[idx])
            idx += 1
        enonce = " ".join(enonce_parts).strip()

        # 2) options A-D
        options = {}
        while idx < len(bloc):
            m = RE_OPTION.match(bloc[idx])
            if not m:
                break
            lettre = m.group(1)
            # le reste de l'option peut continuer sur la même ligne uniquement
            options[lettre] = m.group(2).strip()
            idx += 1
            if len(options) == 4:
                break

        # 3) indice
        indice = ""
        while idx < len(bloc):
            if bloc[idx].lower().startswith("indice"):
                indice = re.sub(r"^indice\s*:\s*", "", bloc[idx], flags=re.I).strip()
                idx += 1
                break
            idx += 1

        # 4) correction détaillée : trouver "Correction détaillée"
        while idx < len(bloc) and not bloc[idx].lower().startswith("correction"):
            idx += 1
        idx += 1  # passer le titre
        # l'énoncé est répété juste après -> on le saute (jusqu'à 1re option)
        while idx < len(bloc) and not RE_OPTION.match(bloc[idx]):
            idx += 1

        # corrections par option
        corrections = {}
        bonne = None
        # On lit jusqu'à "Explications"
        cur_lettre = None
        buf = []
        while idx < len(bloc):
            ligne = bloc[idx]
            if ligne.lower().startswith("explication"):
                break
            m = RE_OPTION.match(ligne)
            if m:
                # flush précédent
                if cur_lettre is not None:
                    corrections[cur_lettre] = " ".join(buf).strip()
                cur_lettre = m.group(1)
                contenu = m.group(2).strip()
                # détecter bonne réponse
                if "(bonne réponse)" in contenu.lower():
                    bonne = cur_lettre
                buf = [contenu]
            else:
                buf.append(ligne)
            idx += 1
        if cur_lettre is not None:
            corrections[cur_lettre] = " ".join(buf).strip()

        # nettoyer le libellé option/correction : enlever le texte d'option dupliqué
        # Les corrections commencent par le libellé de l'option suivi du commentaire.
        # On retire le préfixe "(Bonne réponse)" du texte de correction.
        for k in corrections:
            txt = re.sub(r"\s*\(bonne réponse\)\s*", " ", corrections[k], flags=re.I).strip()
            # retirer le libellé de l'option répété en tête de correction
            libelle = options.get(k, "").strip()
            if libelle:
                # tolère un espace manquant après le libellé (ex: "...2004Bien que")
                lib_pattern = re.escape(libelle)
                m = re.match(lib_pattern + r"\s*", txt)
                if m:
                    txt = txt[m.end():].strip()
            corrections[k] = txt

        # 5) explications : tout le reste après "Explications"
        explication_parts = []
        # idx pointe sur "Explications :" ; passer le titre
        if idx < len(bloc):
            idx += 1
        while idx < len(bloc):
            explication_parts.append(bloc[idx])
            idx += 1
        explication = "\n".join(explication_parts).strip()

        questions.append(
            {
                "num": num,
                "enonce": enonce,
                "options": options,
                "indice": indice,
                "corrections": corrections,
                "bonne_reponse": bonne,
                "explication": explication,
            }
        )
    return questions, themes


def main():
    extract_dir = sys.argv[1]
    numero = int(sys.argv[2])
    theme = sys.argv[3]
    sortie = sys.argv[4]

    paras = extraire_paragraphes(extract_dir + "/word/document.xml")
    questions, themes = parser(paras)

    quiz = {
        "id": numero,
        "titre": "Quiz " + str(numero),
        "theme": theme,
        "seuil_validation": 80,
        "themes_abordes": themes,
        "questions": questions,
    }
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(quiz, f, ensure_ascii=False, indent=2)
    print("OK -", len(questions), "questions ->", sortie)
    # contrôle : chaque question a 4 options, 4 corrections, 1 bonne réponse
    for q in questions:
        ok = len(q["options"]) == 4 and len(q["corrections"]) == 4 and q["bonne_reponse"]
        if not ok:
            print(
                "  ATTENTION Q%s : options=%d corrections=%d bonne=%s"
                % (q["num"], len(q["options"]), len(q["corrections"]), q["bonne_reponse"])
            )


if __name__ == "__main__":
    main()
