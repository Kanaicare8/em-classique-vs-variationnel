"""
================================================================================
TEXTE : pLSA (EM, sans prior) CONTRE LDA (EM variationnel, prior de Dirichlet) (phase 4C)
================================================================================

Usage : python texte_plsa_lda.py [--rapide]

Corpus : 20 Newsgroups (Lang, 1995), 4 groupes : sci.space, rec.sport.baseball,
talk.politics.mideast, comp.graphics, via sklearn.datasets.fetch_20newsgroups (téléchargement
unique, mis en cache par scikit-learn). Le jeu n'a pas de licence explicite ; il est de
diffusion libre pour la recherche (page scikit-learn). Si le téléchargement est impossible :
    python -c "from sklearn.datasets import fetch_20newsgroups as f; f(subset='all')"
sur une machine connectée, puis copier ~/scikit_learn_data/ sur la machine hors ligne.

Prétraitement : minuscules, suppression des en-têtes, citations et signatures (remove=...),
ponctuation et chiffres, mots vides (liste anglaise de scikit-learn), racinisation de Porter
(nltk, sans téléchargement de données), vocabulaire = 1500 mots les plus fréquents avec
apparition dans au moins 5 documents, documents d'au moins 20 mots retenus.

Hypothèse (fixée avant les résultats) : pLSA sur-apprend davantage que LDA quand N est petit
(écart entre perplexité d'apprentissage et perplexité hors échantillon), et l'écart se réduit
quand N croît. Test : différence appariée (pLSA - LDA) de l'écart de généralisation, par N.

Mesures : perplexité hors échantillon par complétion de document (la moitié des mots d'un
document de test sert à estimer theta_d, l'autre moitié à évaluer ; même procédure pour les
deux modèles), cohérence NPMI des 10 premiers mots de chaque thème (co-occurrence en document
sur le corpus de test), pureté contre les étiquettes. pLSA peut donner une probabilité nulle
à un mot : les probabilités sont planchées à 1e-12 pour les deux modèles et la part de mots
planchés est rapportée.
Précision : la LDA est ici l'EM variationnel de Blei et al. (2003) : prior de Dirichlet sur theta, beta ponctuel (lissage 1e-3).
Elle n'est pas un VB complet (pas de prior sur beta) ; la comparaison porte donc sur l'effet du prior sur theta.
Critère d'arrêt : le même pour les deux (A.a_converge, tolérance TOL_REL, plafond commun).
"""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import torch

import algorithmes as A
import comparaison as C

SORTIE = Path(__file__).parent / "resultats"
CATEGORIES = ["sci.space", "rec.sport.baseball", "talk.politics.mideast", "comp.graphics"]
PLAFOND = 150
K = 4
PLANCHER = 1e-12


def charger_corpus():
    from sklearn.datasets import fetch_20newsgroups
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    from nltk.stem import PorterStemmer
    brut = fetch_20newsgroups(subset="all", categories=CATEGORIES, remove=("headers", "footers", "quotes"))
    st = PorterStemmer()
    cache = {}

    def stem(m):
        if m not in cache:
            cache[m] = st.stem(m)
        return cache[m]
    docs = []
    for t in brut.data:
        mots = [stem(m) for m in re.findall(r"[a-z]{3,}", t.lower()) if m not in ENGLISH_STOP_WORDS]
        docs.append(mots)
    df = Counter(m for d in docs for m in set(d))
    freq = Counter(m for d in docs for m in d)
    vocab = [m for m, _ in freq.most_common() if df[m] >= 5][:1500]
    idx = {m: i for i, m in enumerate(vocab)}
    lignes, y = [], []
    for d, lab in zip(docs, brut.target):
        c = Counter(idx[m] for m in d if m in idx)
        if sum(c.values()) >= 20:
            v = torch.zeros(len(vocab))
            for i, n in c.items():
                v[i] = n
            lignes.append(v); y.append(int(lab))
    return torch.stack(lignes), torch.tensor(y), vocab


def separer_moitie(comptes, graine):
    """Chaque mot (occurrence) est affecté au hasard à la moitié « observée » ou « évaluée »."""
    g = A.generateur(graine)
    obs = torch.zeros_like(comptes)
    for d in range(comptes.shape[0]):
        n = comptes[d].long()
        mots = torch.repeat_interleave(torch.arange(comptes.shape[1]), n)
        pris = torch.rand(len(mots), generator=g) < 0.5
        obs[d] = torch.bincount(mots[pris], minlength=comptes.shape[1]).to(comptes.dtype)
    return obs, comptes - obs


def theta_plsa(phi, c_obs, n_iter=PLAFOND):
    """Repli (fold-in) du pLSA : EM sur theta_d avec phi fixé, même critère d'arrêt."""
    Dn = c_obs.shape[0]
    theta = torch.full((Dn, phi.shape[0]), 1.0 / phi.shape[0])
    prec = None
    for _ in range(n_iter):
        m = theta @ phi
        ll = float(torch.xlogy(c_obs, m).sum())
        if prec is not None and A.a_converge(prec, ll):
            break
        prec = ll
        th = theta * ((c_obs / m.clamp(min=1e-300)) @ phi.T)
        theta = th / th.sum(1, keepdim=True)
    return theta


def theta_lda(beta, alpha, c_obs, n_iter=PLAFOND):
    """Repli de la LDA : point fixe variationnel sur gamma_d avec beta fixé."""
    Dn, V = c_obs.shape
    Kk = beta.shape[0]
    gamma = alpha + c_obs.sum(1, keepdim=True) / Kk
    lb = beta.clamp(min=1e-300).log().T
    for _ in range(n_iter):
        Elog = torch.special.digamma(gamma) - torch.special.digamma(gamma.sum(1, keepdim=True))
        phi = torch.softmax(Elog[:, None, :] + lb[None], dim=2)
        g2 = alpha + (c_obs[:, :, None] * phi).sum(1)
        if (g2 - gamma).abs().max() < 1e-8:
            gamma = g2
            break
        gamma = g2
    return gamma / gamma.sum(1, keepdim=True)


def perplexite(theta, phi, c_eval):
    p = theta @ phi
    planche = p < PLANCHER
    p = p.clamp(min=PLANCHER)
    n = c_eval.sum()
    return float(torch.exp(-(c_eval * p.log()).sum() / n)), float((c_eval * planche).sum() / n)


def npmi(phi, c_ref, top=10):
    """Cohérence NPMI moyenne : co-occurrence en document sur c_ref ; paires des `top` mots de chaque thème."""
    B = (c_ref > 0).to(torch.float64)
    Dn = B.shape[0]
    pm = B.mean(0)
    scores = []
    for k in range(phi.shape[0]):
        mots = torch.topk(phi[k], top).indices
        s = []
        for i in range(top):
            for j in range(i + 1, top):
                wi, wj = mots[i], mots[j]
                pij = float((B[:, wi] * B[:, wj]).mean())
                if pij <= 0:
                    s.append(-1.0)
                    continue
                s.append(math.log(pij / (float(pm[wi]) * float(pm[wj]))) / (-math.log(pij)))
        scores.append(sum(s) / len(s))
    return sum(scores) / len(scores)


def purete(theta, y):
    """Pureté : chaque document est affecté à son thème dominant ; fraction d'étiquettes majoritaires par thème."""
    z = theta.argmax(1)
    bons = 0
    for k in range(theta.shape[1]):
        m = y[z == k]
        if len(m):
            bons += int(torch.bincount(m).max())
    return bons / len(y)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapide", action="store_true")
    a = ap.parse_args(argv)
    R = 3 if a.rapide else 10
    comptes, y, vocab = charger_corpus()
    Dn = comptes.shape[0]
    print(f"{Dn} documents, vocabulaire {len(vocab)}", flush=True)
    g = A.generateur(0)
    perm = torch.randperm(Dn, generator=g)
    test_idx = perm[:600]
    pool = perm[600:]
    c_test, y_test = comptes[test_idx], y[test_idx]
    obs, ev = separer_moitie(c_test, 1)
    lignes = []
    for N in (50, 200, 1000):
        for r in range(R):
            gr = A.generateur(100 * N + r)
            sel = pool[torch.randperm(len(pool), generator=gr)[:N]]
            c_tr, y_tr = comptes[sel], y[sel]
            pl = A.plsa_em(c_tr, K, n_iter=PLAFOND, graine=r)
            ld = A.lda_variationnel(c_tr, K, n_iter=PLAFOND, graine=r)
            for nom, phi, th_tr, conv, fold in (
                    ("pLSA", pl["phi"], pl["theta"], pl["converge"], lambda ph, co: theta_plsa(ph, co)),
                    ("LDA", ld["beta"], ld["theta"], ld["converge"], lambda ph, co: theta_lda(ph, ld["alpha"], co))):
                th_obs_tr, ev_tr = separer_moitie(c_tr, 2)
                th_in = fold(phi, th_obs_tr)
                ppl_tr, _ = perplexite(th_in, phi, ev_tr)
                th_te = fold(phi, obs)
                ppl_te, plancher = perplexite(th_te, phi, ev)
                lignes.append({"N": N, "rep": r, "modele": nom, "perplexite_apprentissage": ppl_tr, "perplexite_test": ppl_te,
                               "ecart_generalisation": ppl_te - ppl_tr, "ecart_relatif": ppl_te / ppl_tr - 1.0,
                               "part_mots_planches": plancher, "NPMI": npmi(phi, c_test), "purete_test": purete(th_te, y_test),
                               "converge": bool(conv)})
        print(f"N = {N} terminé", flush=True)
    df = pd.DataFrame(lignes)
    SORTIE.mkdir(exist_ok=True)
    df.to_csv(SORTIE / "texte_plsa_lda_brut.csv", index=False)
    res = df.groupby(["N", "modele"]).agg(ppl_test=("perplexite_test", "mean"), ecart_rel=("ecart_relatif", "mean"),
                                           planchers=("part_mots_planches", "mean"), NPMI=("NPMI", "mean"),
                                           purete=("purete_test", "mean"), non_converge=("converge", lambda s: 1 - s.mean())).reset_index()
    res.to_csv(SORTIE / "texte_plsa_lda.csv", index=False)
    grille = []
    for N, s in df.groupby("N"):
        d = (s[s.modele == "pLSA"].set_index("rep").ecart_relatif - s[s.modele == "LDA"].set_index("rep").ecart_relatif).dropna()
        grille.append(C.rapport_hypothese(f"H-texte[N={N}]", "Surapprentissage", "écart relatif de perplexité (pLSA - LDA)", d.tolist(), niveau="expérience répliquée"))
    pd.DataFrame(grille).to_csv(SORTIE / "texte_grille.csv", index=False)
    print(res.to_string(index=False))


if __name__ == "__main__":
    main()
