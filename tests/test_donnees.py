"""Racinisation de Porter (exemples de l'article de 1980) et lecteurs de données sans bibliothèque externe."""
import os
import sys

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


def test_iris_et_sp500():
    X, y = DO.charger_iris()
    assert X.shape == (150, 4) and sorted(set(y.tolist())) == [0, 1, 2]
    dates, r = DO.charger_sp500()
    assert len(dates) == len(r) and abs(float(r.mean())) < 1.0
