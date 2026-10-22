"""
================================================================================
DONNÉES : générateurs synthétiques et lecteurs écrits à la main (sans scikit-learn ni nltk)
================================================================================

  Synthétiques   gen_gauss(), gen_student(), centres_triangle(), centres_ligne()
  Iris           charger_iris()              data/iris.csv (Fisher 1936, UCI)
  S&P 500        charger_sp500()             data/sp500_fred.csv, empreinte SHA-256 vérifiée
  Texte          charger_20newsgroups()      archive originale 20news-bydate.tar.gz (Lang 1995),
                                             lue avec tarfile ; en-têtes, citations et signatures
                                             retirés ; racinisation de Porter (1980) écrite ici ;
                                             mots vides définis par la fréquence documentaire
                                             (aucune liste externe).
  Climat         voir donnees_geo.py (seul module qui lit des formats géographiques).
"""

from __future__ import annotations

import csv
import hashlib
import math
import re
import tarfile
from collections import Counter
from datetime import date
from pathlib import Path

import torch

import algorithmes as A

RACINE = Path(__file__).parent
DATA = RACINE / "data"


# ==============================================================================
# SYNTHÉTIQUES
# ==============================================================================

def gen_gauss(n, centres, sigma, poids=None, graine=0):
    """Mélange de gaussiennes isotropes d'écart-type sigma. Retourne (X, y)."""
    g = A.generateur(graine)
    centres = torch.as_tensor(centres, dtype=torch.float64)
    K = centres.shape[0]
    p = torch.full((K,), 1.0 / K) if poids is None else torch.as_tensor(poids, dtype=torch.float64)
    y = torch.multinomial(p, n, replacement=True, generator=g)
    X = centres[y] + sigma * torch.randn(n, centres.shape[1], generator=g)
    return X, y


def gen_student(n, centres, sigma, nu, graine=0):
    """Composantes de Student (nu degrés de liberté) de variance sigma², mêmes centres : queues épaisses."""
    g = A.generateur(graine)
    centres = torch.as_tensor(centres, dtype=torch.float64)
    K, D = centres.shape
    y = torch.randint(K, (n,), generator=g)
    z = torch.randn(n, D, generator=g)
    with torch.random.fork_rng():
        torch.manual_seed(int(graine) % (2 ** 62))
        chi2 = torch.distributions.Gamma(torch.tensor(nu / 2.0), torch.tensor(0.5)).sample((n,))
    X = centres[y] + sigma * z * torch.sqrt(nu / chi2)[:, None] / (nu / (nu - 2.0)) ** 0.5
    return X, y


def centres_triangle(d_sigma, sigma=1.0, D=2):
    """Trois centres équidistants, distance d_sigma x sigma deux à deux (D >= 2)."""
    c = torch.zeros(3, D)
    c[1, 0] = d_sigma * sigma
    c[2, 0] = d_sigma * sigma / 2
    c[2, 1] = d_sigma * sigma * 3 ** 0.5 / 2
    return c


def centres_ligne(K, ecart, D=2):
    c = torch.zeros(K, D)
    c[:, 0] = torch.arange(K) * ecart
    return c


# ==============================================================================
# IRIS ET S&P 500
# ==============================================================================

def charger_iris():
    """Iris de Fisher (1936) : X (150, 4) en centimètres, y (150,) espèces 0, 1, 2."""
    lignes = list(csv.reader(open(DATA / "iris.csv", encoding="utf-8")))[1:]
    lignes = [l for l in lignes if l]
    X = torch.tensor([[float(v) for v in l[:4]] for l in lignes], dtype=torch.float64)
    especes = {e: i for i, e in enumerate(dict.fromkeys(l[4] for l in lignes))}
    return X, torch.tensor([especes[l[4]] for l in lignes])


SHA256_SP500 = "551b282c417da2e7fa38ad4da0c5ebc2c907d386272a0752d04f97e16b7c90dc"


def charger_sp500():
    """
    Clôtures quotidiennes du S&P 500 (FRED, série SP500), archive data/sp500_fred.csv dont l'empreinte
    SHA-256 est vérifiée. Retourne (dates, rendements en % = 100 ln(P_t / P_{t-1})).
    """
    chemin = DATA / "sp500_fred.csv"
    empreinte = hashlib.sha256(chemin.read_bytes()).hexdigest()
    if empreinte != SHA256_SP500:
        raise RuntimeError(f"{chemin.name} : empreinte {empreinte[:12]}... différente de l'archive du mémoire")
    dates, prix = [], []
    for l in list(csv.reader(open(chemin, encoding="utf-8")))[1:]:
        if len(l) >= 2 and l[1] not in ("", "."):
            dates.append(date.fromisoformat(l[0]))
            prix.append(float(l[1]))
    p = torch.tensor(prix, dtype=torch.float64)
    return dates[1:], 100.0 * torch.log(p[1:] / p[:-1])


# ==============================================================================
# RACINISATION DE PORTER (1980), écrite d'après l'article original
# ==============================================================================

_VOY = set("aeiou")


def _consonne(m: str, i: int) -> bool:
    c = m[i]
    if c in _VOY:
        return False
    if c == "y":
        return i == 0 or not _consonne(m, i - 1)
    return True


def _mesure(m: str) -> int:
    """m dans [C](VC)^m[V]."""
    n, i, L = 0, 0, len(m)
    while i < L and _consonne(m, i):
        i += 1
    while i < L:
        while i < L and not _consonne(m, i):
            i += 1
        if i >= L:
            break
        while i < L and _consonne(m, i):
            i += 1
        n += 1
    return n


def _a_voyelle(m: str) -> bool:
    return any(not _consonne(m, i) for i in range(len(m)))


def _double_consonne(m: str) -> bool:
    return len(m) >= 2 and m[-1] == m[-2] and _consonne(m, len(m) - 1)


def _cvc(m: str) -> bool:
    """*o : consonne-voyelle-consonne finale, la dernière n'étant ni w, ni x, ni y."""
    if len(m) < 3:
        return False
    return (_consonne(m, len(m) - 3) and not _consonne(m, len(m) - 2) and _consonne(m, len(m) - 1)
            and m[-1] not in "wxy")


def _remplacer(mot: str, regles, condition) -> str:
    """Applique la règle au suffixe le plus long ; si sa condition échoue, aucune autre règle de l'étape."""
    for suf, rep in sorted(regles, key=lambda t: -len(t[0])):
        if mot.endswith(suf):
            radical = mot[: len(mot) - len(suf)]
            return radical + rep if condition(radical, suf) else mot
    return mot


_ETAPE2 = [("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"), ("izer", "ize"),
           ("abli", "able"), ("alli", "al"), ("entli", "ent"), ("eli", "e"), ("ousli", "ous"), ("ization", "ize"),
           ("ation", "ate"), ("ator", "ate"), ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"),
           ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble")]
_ETAPE3 = [("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"), ("ical", "ic"), ("ful", ""), ("ness", "")]
_ETAPE4 = ["al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment", "ent", "ion", "ou", "ism",
           "ate", "iti", "ous", "ive", "ize"]


def porter(mot: str) -> str:
    """Racine de Porter (1980) d'un mot anglais en minuscules."""
    m = mot
    if len(m) <= 2:
        return m
    # étape 1a
    if m.endswith("sses"):
        m = m[:-2]
    elif m.endswith("ies"):
        m = m[:-2]
    elif m.endswith("ss"):
        pass
    elif m.endswith("s"):
        m = m[:-1]
    # étape 1b
    suite = False
    if m.endswith("eed"):
        if _mesure(m[:-3]) > 0:
            m = m[:-1]
    elif m.endswith("ed") and _a_voyelle(m[:-2]):
        m, suite = m[:-2], True
    elif m.endswith("ing") and _a_voyelle(m[:-3]):
        m, suite = m[:-3], True
    if suite:
        if m.endswith(("at", "bl", "iz")):
            m += "e"
        elif _double_consonne(m) and m[-1] not in "lsz":
            m = m[:-1]
        elif _mesure(m) == 1 and _cvc(m):
            m += "e"
    # étape 1c
    if m.endswith("y") and _a_voyelle(m[:-1]):
        m = m[:-1] + "i"
    # étapes 2 et 3
    m = _remplacer(m, _ETAPE2, lambda r, s: _mesure(r) > 0)
    m = _remplacer(m, _ETAPE3, lambda r, s: _mesure(r) > 0)
    # étape 4
    m = _remplacer(m, [(s, "") for s in _ETAPE4],
                   lambda r, s: _mesure(r) > 1 and (s != "ion" or (len(r) > 0 and r[-1] in "st")))
    # étape 5a
    if m.endswith("e"):
        r = m[:-1]
        if _mesure(r) > 1 or (_mesure(r) == 1 and not _cvc(r)):
            m = r
    # étape 5b
    if _mesure(m) > 1 and _double_consonne(m) and m.endswith("l"):
        m = m[:-1]
    return m


# ==============================================================================
# 20 NEWSGROUPS
# ==============================================================================

_CITATION = re.compile(r"(writes in|writes:|wrote:|says:|said:|^In article|^Quoted from|^\||^>)")


def _nettoyer_message(texte: str) -> str:
    """Retire l'en-tête (jusqu'à la première ligne vide), les lignes de citation et la signature (après « -- »)."""
    _, _, corps = texte.partition("\n\n")
    lignes = [l for l in corps.split("\n") if not _CITATION.search(l)]
    lignes = "\n".join(lignes).strip().split("\n")
    for i in range(len(lignes) - 1, -1, -1):
        if lignes[i].strip().strip("-") == "" and lignes[i].strip().startswith("--"):
            lignes = lignes[:i]
            break
    return "\n".join(lignes)


def charger_20newsgroups(categories, archive: Path = DATA / "texte" / "20news-bydate.tar.gz"):
    """
    Documents bruts des catégories demandées (parties train et test de « bydate » réunies, l'échantillonnage
    étant refait par le protocole). Retourne (textes nettoyés, étiquettes).
    """
    textes, etiq = [], []
    ordre = {c: i for i, c in enumerate(categories)}
    with tarfile.open(archive, "r:gz") as t:
        for m in t:
            if not m.isfile():
                continue
            parties = m.name.split("/")
            if len(parties) < 3 or parties[-2] not in ordre:
                continue
            brut = t.extractfile(m).read().decode("latin-1")
            textes.append(_nettoyer_message(brut))
            etiq.append(ordre[parties[-2]])
    return textes, torch.tensor(etiq)


def tokeniser(texte: str, longueur_min_mot: int) -> list[str]:
    return [porter(w) for w in re.findall(r"[a-z]+", texte.lower()) if len(w) >= longueur_min_mot]


def matrice_documents(textes, vocab_taille: int, df_min: int, df_max: float, longueur_min_mot: int,
                      longueur_min_doc: int):
    """
    Matrice documents x mots. Vocabulaire : racines présentes dans au moins df_min documents et dans au plus
    une fraction df_max des documents (les mots grammaticaux, présents partout, sont écartés par ce seul
    critère de fréquence documentaire), puis les vocab_taille plus fréquentes. Documents d'au moins
    longueur_min_doc occurrences retenus. Retourne (comptes (D,V), indices des documents retenus, vocabulaire).
    """
    docs = [tokeniser(t, longueur_min_mot) for t in textes]
    df = Counter(w for d in docs for w in set(d))
    freq = Counter(w for d in docs for w in d)
    n = len(docs)
    vocab = [w for w, _ in freq.most_common() if df_min <= df[w] <= df_max * n][:vocab_taille]
    idx = {w: i for i, w in enumerate(vocab)}
    lignes, garde = [], []
    for j, d in enumerate(docs):
        c = Counter(idx[w] for w in d if w in idx)
        if sum(c.values()) >= longueur_min_doc:
            v = torch.zeros(len(vocab), dtype=torch.float64)
            for i, k in c.items():
                v[i] = k
            lignes.append(v)
            garde.append(j)
    return torch.stack(lignes), torch.tensor(garde), vocab
