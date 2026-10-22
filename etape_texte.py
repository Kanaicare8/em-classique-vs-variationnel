"""
================================================================================
ÉTAPE « texte » : pLSA (EM, sans prior) contre LDA (EM variationnel, prior de Dirichlet sur theta_d)
================================================================================

Corpus : 20 Newsgroups « bydate » (Lang 1995), archive d'origine lue par donnees.py (tarfile), quatre
groupes : sci.space, rec.sport.baseball, talk.politics.mideast, comp.graphics. Prétraitement entièrement
écrit à la main : en-têtes, citations et signatures retirés ; minuscules ; racinisation de Porter (1980) ;
mots vides écartés par leur fréquence documentaire (df_max) ; vocabulaire des mots les plus fréquents.
Le vocabulaire est un choix de conception (registre « vocabulaire ») ; la sensibilité des conclusions à
sa taille est mesurée (unités « vocab=... »).

Unités :
  corpus/V=v                matrice documents x mots, documents de test (fixes) et réservoir d'apprentissage
  V=v/N=n/rep=r             échantillon de n documents ; pLSA et LDA, n_init relances chacun (meilleur critère)
Mesures (identiques pour les deux modèles) :
  perplexité par complétion de document : la moitié des mots d'un document (tirée au hasard) estime theta_d
  (repli, « fold-in », avec les distributions de mots fixées), l'autre moitié est évaluée ;
  écart relatif test / apprentissage ; part de mots dont la probabilité est nulle (plancher numérique 1e-300) ;
  cohérence NPMI des 10 premiers mots de chaque thème (co-occurrences dans les documents de test) ;
  pureté du thème dominant par rapport aux étiquettes.
"""

from __future__ import annotations

import math

import torch

import algorithmes as A
import donnees as DO
import etapes as E
import hypotheses as HY
import parametres as PARAM
import persistance as PE
import statistique as S

CATEGORIES = ["sci.space", "rec.sport.baseball", "talk.politics.mideast", "comp.graphics"]
K = len(CATEGORIES)               # nombre de thèmes = nombre de groupes du corpus
N_TEST = 600
EFFECTIFS = (50, 200, 1000)
PLANCHER = 1e-300


def unite_corpus(memo, rapide, V):
    voc = PARAM.valeur("vocabulaire")
    textes, y = DO.charger_20newsgroups(CATEGORIES)
    comptes, garde, vocab = DO.matrice_documents(textes, V, int(voc["df_min"]), float(voc["df_max"]),
                                                 int(voc["longueur_min_mot"]), int(voc["longueur_min_doc"]))
    y = y[garde]
    perm = torch.randperm(len(y), generator=A.generateur(PE.graine("texte", "test")))
    return {"lignes": [{"V": V, "documents": len(y), "vocabulaire": len(vocab)}],
            "artefacts": {"comptes": comptes.to(torch.float32), "y": y, "vocab": vocab,
                          "test": perm[:N_TEST], "reservoir": perm[N_TEST:]}}


def separer_moitie(comptes, graine):
    """Chaque occurrence de mot est affectée au hasard à la moitié « observée » ou « évaluée »."""
    g = A.generateur(graine)
    obs = torch.zeros_like(comptes)
    for d in range(comptes.shape[0]):
        n = comptes[d].long()
        mots = torch.repeat_interleave(torch.arange(comptes.shape[1]), n)
        pris = torch.rand(len(mots), generator=g) < 0.5
        obs[d] = torch.bincount(mots[pris], minlength=comptes.shape[1]).to(comptes.dtype)
    return obs, comptes - obs


def repli_plsa(phi, c_obs):
    """theta_d par EM avec phi fixé, critère d'arrêt commun."""
    tol, n_iter, _ = A._defauts(None, None, 0.0)
    theta = torch.full((c_obs.shape[0], phi.shape[0]), 1.0 / phi.shape[0], dtype=torch.float64)
    prec = None
    for _ in range(n_iter + 1):
        m = theta @ phi
        ll = float(torch.xlogy(c_obs, m).sum())
        if prec is not None and A.a_converge(prec, ll, tol):
            break
        prec = ll
        th = theta * ((c_obs / m.clamp(min=PLANCHER)) @ phi.T)
        theta = th / th.sum(1, keepdim=True).clamp(min=PLANCHER)
    return theta


def repli_lda(beta, alpha, c_obs):
    """Point fixe variationnel sur gamma_d avec beta fixé, même tolérance que le critère commun."""
    tol, n_iter, _ = A._defauts(None, None, 0.0)
    gamma = alpha + c_obs.sum(1, keepdim=True) / beta.shape[0]
    lb = beta.clamp(min=PLANCHER).log().T
    for _ in range(n_iter):
        Elog = torch.special.digamma(gamma) - torch.special.digamma(gamma.sum(1, keepdim=True))
        phi = torch.softmax(Elog[:, None, :] + lb[None], dim=2)
        g2 = alpha + (c_obs[:, :, None] * phi).sum(1)
        fini = bool(((g2 - gamma).abs() <= tol * gamma.abs().clamp(min=1.0)).all())
        gamma = g2
        if fini:
            break
    return gamma / gamma.sum(1, keepdim=True)


def perplexite(theta, phi, c_eval):
    p = theta @ phi
    nul = p < PLANCHER
    n = c_eval.sum()
    return float(torch.exp(-(c_eval * p.clamp(min=PLANCHER).log()).sum() / n)), float((c_eval * nul).sum() / n)


def npmi(phi, c_ref, top=10):
    B = (c_ref > 0).to(torch.float64)
    pm = B.mean(0)
    scores = []
    for k in range(phi.shape[0]):
        mots = torch.topk(phi[k], top).indices
        s = []
        for i in range(top):
            for j in range(i + 1, top):
                pij = float((B[:, mots[i]] * B[:, mots[j]]).mean())
                s.append(-1.0 if pij <= 0 else math.log(pij / (float(pm[mots[i]]) * float(pm[mots[j]]))) / (-math.log(pij)))
        scores.append(sum(s) / len(s))
    return sum(scores) / len(scores)


def purete(theta, y):
    z = theta.argmax(1)
    return sum(int(torch.bincount(y[z == k]).max()) for k in range(theta.shape[1]) if (z == k).any()) / len(y)


def _meilleur(f, n_init, base):
    meilleur = None
    for s in range(n_init):
        r = f(base + s)
        crit = r["ll_hist"][-1] if "ll_hist" in r else r["bornes"][-1]
        if meilleur is None or crit > meilleur[0]:
            meilleur = (crit, r)
    return meilleur[1]


def unite_echantillon(memo, rapide, V, N, rep, etape_corpus="texte"):
    cor = E.magasin(etape_corpus, rapide).lire(f"corpus/V={V}")["artefacts"]
    comptes = cor["comptes"].double()
    y = cor["y"]
    sel = cor["reservoir"][torch.randperm(len(cor["reservoir"]), generator=A.generateur(PE.graine("texte", V, N, rep)))[:N]]
    c_tr, y_tr = comptes[sel], y[sel]
    c_te, y_te = comptes[cor["test"]], y[cor["test"]]
    n_init = min(int(PARAM.valeur("n_init")["texte"]), 2 if rapide else 10 ** 9)
    base = PE.graine("texte", "ajustement", V, N, rep) % 2 ** 31
    hyp = PARAM.valeur("lda_hyper")
    pl = memo("pLSA", lambda: _meilleur(lambda g: A.plsa_em(c_tr, K, graine=g), n_init, base))
    ld = memo("LDA", lambda: _meilleur(lambda g: A.lda_variationnel(c_tr, K, alpha=float(hyp["alpha"]),
                                                                    lissage=float(hyp["lissage"]), graine=g), n_init, base))
    obs_te, ev_te = separer_moitie(c_te, PE.graine("texte", "moitie_test"))
    obs_tr, ev_tr = separer_moitie(c_tr, PE.graine("texte", "moitie_app", V, N, rep))
    lignes = []
    for nom, phi, repli, conv in (("pLSA", pl["phi"], lambda o: repli_plsa(pl["phi"], o), pl["converge"]),
                                  ("LDA", ld["beta"], lambda o: repli_lda(ld["beta"], ld["alpha"], o), ld["converge"])):
        ppl_tr, _ = perplexite(repli(obs_tr), phi, ev_tr)
        th_te = repli(obs_te)
        ppl_te, nul = perplexite(th_te, phi, ev_te)
        lignes.append({"V": str(V), "N": str(N), "rep": rep, "bras": nom, "perplexite_apprentissage": ppl_tr,
                       "perplexite_test": ppl_te, "ecart_relatif": ppl_te / ppl_tr - 1.0, "part_mots_nuls": nul,
                       "NPMI": npmi(phi, c_te), "purete": purete(th_te, y_te), "converge": float(conv)})
    return {"lignes": lignes, "artefacts": {"documents": sel, "phi_plsa": pl["phi"].float(), "beta_lda": ld["beta"].float(),
                                            "theta_plsa": pl["theta"].float(), "theta_lda": ld["theta"].float()}}


def unites(rapide: bool):
    R = 2 if rapide else int(PARAM.valeur("replications")["texte"])
    V0 = int(PARAM.valeur("vocabulaire")["taille"])
    tailles = (V0,) if rapide else (V0, int(PARAM.valeur("vocabulaire")["sensibilite"][0]),
                                    int(PARAM.valeur("vocabulaire")["sensibilite"][1]))
    us = []
    for V in tailles:
        us.append(E.Unite("texte", f"corpus/V={V}", "etape_texte", "unite_corpus", dict(V=V)))
        for N in EFFECTIFS:
            for r in range(R):
                us.append(E.Unite("texte", f"V={V}/N={N}/rep={r:03d}", "etape_texte", "unite_echantillon",
                                  dict(V=V, N=N, rep=r), depend=(f"corpus/V={V}",)))
    return us


def agreger(rapide: bool):
    L = []
    for r in E.resultats("texte", rapide, "V="):
        L += r["lignes"]
    E.ecrire_csv("texte_brut", L, rapide)
    V0 = str(int(PARAM.valeur("vocabulaire")["taille"]))
    principal = [l for l in L if l["V"] == V0]
    hyp = [{"id": h.id, "axe": h.axe, "enonce": h.enonce, "test": h.test, "marge": HY.marge(h),
            "diffs": HY.diffs(h, principal)} for h in HY.famille("texte")]
    E.ecrire_csv("texte_decisions", S.decider_famille(hyp, float(PARAM.valeur("alpha_test")),
                                                      int(PARAM.valeur("n_bootstrap_ic"))), rapide)
    resume = {}
    for l in L:
        resume.setdefault((l["V"], l["N"], l["bras"]), []).append(l)
    out = []
    for (V, N, b), ls in sorted(resume.items(), key=lambda t: (int(t[0][0]), int(t[0][1]), t[0][2])):
        out.append({"V": V, "N": N, "bras": b, "n": len(ls),
                    **{m: sum(x[m] for x in ls) / len(ls) for m in ("perplexite_test", "ecart_relatif", "part_mots_nuls",
                                                                     "NPMI", "purete", "converge")}})
    E.ecrire_csv("texte_resume", out, rapide)
