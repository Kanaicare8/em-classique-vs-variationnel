"""Racinisation de Porter (exemples de l'article de 1980) et lecteurs de données sans bibliothèque externe."""
import math
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import donnees as DO  # noqa: E402

EXEMPLES = {
    # étape 1a
    "caresses": "caress", "ponies": "poni", "ties": "ti", "caress": "caress", "cats": "cat",
    # étape 1b
    "feed": "feed", "agreed": "agre", "plastered": "plaster", "bled": "bled", "motoring": "motor", "sing": "sing",
    "conflated": "conflat", "troubled": "troubl", "sized": "size", "hopping": "hop", "tanned": "tan",
    "falling": "fall", "hissing": "hiss", "fizzed": "fizz", "failing": "fail", "filing": "file",
    # étape 1c
    "happy": "happi", "sky": "sky",
    # étapes 2 à 5
    "relational": "relat", "conditional": "condit", "rational": "ration", "valenci": "valenc",
    "hesitanci": "hesit", "digitizer": "digit", "conformabli": "conform", "radicalli": "radic",
    "differentli": "differ", "vileli": "vile", "analogousli": "analog", "vietnamization": "vietnam",
    "predication": "predic", "operator": "oper", "feudalism": "feudal", "decisiveness": "decis",
    "hopefulness": "hope", "callousness": "callous", "formaliti": "formal", "sensitiviti": "sensit",
    "sensibiliti": "sensibl", "triplicate": "triplic", "formative": "form", "formalize": "formal",
    "electriciti": "electr", "electrical": "electr", "hopeful": "hope", "goodness": "good",
    "revival": "reviv", "allowance": "allow", "inference": "infer", "airliner": "airlin",
    "gyroscopic": "gyroscop", "adjustable": "adjust", "defensible": "defens", "irritant": "irrit",
    "replacement": "replac", "adjustment": "adjust", "dependent": "depend", "adoption": "adopt",
    "homologou": "homolog", "communism": "commun", "activate": "activ", "angulariti": "angular",
    "homologous": "homolog", "effective": "effect", "bowdlerize": "bowdler",
    "probate": "probat", "rate": "rate", "cease": "ceas", "controll": "control", "roll": "roll",
}


def test_porter_exemples_de_l_article():
    faux = {m: (DO.porter(m), r) for m, r in EXEMPLES.items() if DO.porter(m) != r}
    assert not faux, faux


def test_nettoyage_message():
    brut = "From: a@b\nSubject: x\n\nIn article <1> joe writes:\n> cite\nvrai texte ici\n--\nJoe, signature\n"
    assert DO._nettoyer_message(brut).strip() == "vrai texte ici"


def test_iris():
    X, y = DO.charger_iris()
    assert X.shape == (150, 4) and sorted(set(y.tolist())) == [0, 1, 2]


def test_prix_extrait_et_variables():
    d = DO.charger_prix()
    N = len(d["X"])
    assert d["X"].shape == (N, 3) and N > 1000 and bool(torch.isfinite(d["X"]).all())
    assert len(d["marche"]) == len(d["mois"]) == N
    assert bool((d["mois"][1:] >= d["mois"][:-1]).all())                     # ordre du temps
    # la variable est causale : recalcul à la main d'une observation à partir des seuls relevés antérieurs
    import csv
    import math
    i = N // 2
    m, t = d["marches"][int(d["marche"][i])], int(d["mois"][i])
    s = {DO.mois_index(l["date"]): math.log(float(l["price"])) for l in csv.DictReader(open(DO.DATA / "prix" / "wfp_cmr_panier.csv",
         encoding="utf-8")) if l["market"] == m and l["commodity"] == DO.PANIER_PRIX[0]}
    for e in d["ecartes"]:
        if e["marche"] == m and e["denree"] == DO.PANIER_PRIX[0]:
            s.pop(DO.mois_index(e["mois"]), None)
    passe = [s[u] for u in range(t - 12, t) if u in s]
    assert abs(float(d["X"][i, 0]) - (s[t] - sum(passe) / len(passe))) < 1e-12


def test_pics_isoles():
    s = {0: 0.0, 1: math.log(10.0), 2: 0.0, 3: 0.1, 4: math.log(2.0), 5: 0.0}
    assert DO.pics_isoles(s, 3.0) == [1]                                     # x10 aller-retour : écarté ; x2 : gardé
    assert DO.pics_isoles({0: 0.0, 1: math.log(10.0)}, 3.0) == []           # pas de mois suivant : gardé
