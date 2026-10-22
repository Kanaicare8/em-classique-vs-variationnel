"""Contrôles statiques LaTeX sans compilation : environnements équilibrés, fichiers inclus présents, références définies."""
import re
from pathlib import Path

R = Path(__file__).resolve().parent.parent
fichiers = [R / "main.tex", R / "body.tex", R / "introduction.tex", R / "resume.tex"] + sorted((R / "figures_tikz").glob("*.tex")) + sorted((R / "tables").glob("*.tex"))
tout = ""
erreurs = []
for f in fichiers:
    s = f.read_text(encoding="utf-8")
    tout += "\n" + s
    sans = re.sub(r"(?m)(?<!\\)%.*$", "", s)
    sans = re.sub(r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}", "", sans, flags=re.S)
    ouv = re.findall(r"\\begin\{([^}]*)\}", sans)
    fer = re.findall(r"\\end\{([^}]*)\}", sans)
    for env in set(ouv) | set(fer):
        if ouv.count(env) != fer.count(env):
            erreurs.append(f"{f.name}: environnement {env} : {ouv.count(env)} begin / {fer.count(env)} end")
    if sans.count("{") - sans.count(r"\{") != sans.count("}") - sans.count(r"\}"):
        erreurs.append(f"{f.name}: accolades non équilibrées ({sans.count('{') - sans.count(chr(92) + '{')} / {sans.count('}') - sans.count(chr(92) + '}')})")
    for m in re.finditer(r"\\input\{([^}]*)\}", sans):
        cible = m.group(1)
        if not (R / cible).exists() and not (R / (cible + ".tex")).exists():
            erreurs.append(f"{f.name}: \\input{{{cible}}} introuvable")
labels = set(re.findall(r"\\label\{([^}]*)\}", tout))
refs = set(re.findall(r"\\(?:ref|eqref|cref)\{([^}]*)\}", tout))
manquantes = sorted(r for r in refs if r not in labels)
for r in manquantes:
    erreurs.append(f"référence sans étiquette : {r}")
gen = set(re.findall(r"\\tableauGenere\{([^}]*)\}", tout))
absents = sorted(g for g in gen if not (R / "tables" / f"{g}.tex").exists())
print("\n".join(erreurs) if erreurs else "aucune erreur structurelle")
print("tableaux générés encore absents (résultats à produire) :", ", ".join(absents) if absents else "aucun")
