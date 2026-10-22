"""
================================================================================
CAS PRINCIPAL : RÉGIMES CLIMATIQUES DU CAMEROUN, EM CLASSIQUE CONTRE EM VARIATIONNEL
================================================================================

Usage :
    python cas_pratique_climat.py --preparer          télécharge WorldClim 2.1 (2,5 min) dans data/climat/
    python cas_pratique_climat.py [--rapide] [--d19]  lance les expériences
        --frontiere chemin.shp   contour du Cameroun (sinon : emprise rectangulaire, voir limites)
        --koppen chemin.tif      carte Köppen-Geiger de Beck et al. (2018), 1 km, codes 1..30
        --zones chemin.shp       zones agro-écologiques officielles (champ « zone »), facultatif

Disponibilité et licences (vérifiées le 2026-10-13, voir resultats/climat_sources.txt) :
  * WorldClim 2.1 : archives GeoTIFF https://geodata.ucdavis.edu/climate/worldclim/2_1/base/
    wc2.1_2.5m_bio.zip (19 variables) et wc2.1_2.5m_elev.zip. Usage académique et non
    commercial libre ; REDISTRIBUTION INTERDITE sans autorisation (worldclim.org/about.html).
    Les fichiers ne sont donc PAS versionnés dans le dépôt : le script les télécharge.
  * Zones agro-écologiques officielles : aucun shapefile téléchargeable retrouvé (carte IRAD
    2005 publiée en figure seulement). SANS le fichier fourni par --zones, la référence est
    Köppen-Geiger seul, ce que le script et le mémoire disent explicitement.
  * Köppen-Geiger : Beck et al. (2018), Sci. Data 5:180214, www.gloh2o.org/koppen. Licence à
    confirmer sur la page de distribution avant tout dépôt du fichier.

Variables (D = 5) : bio1, bio4, log(bio12), bio15, altitude. Extension D = 20 : bio1..bio19 et
altitude (log sur bio12 et sur les précipitations bio13 à bio19). Standardisation commune.
Hypothèses H1 à H8 et critères : voir hypotheses() ci-dessous ; correction de Holm sur
l'ensemble des tests.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
import torch

import algorithmes as A
import comparaison as C

RACINE = Path(__file__).parent
DATA = RACINE / "data" / "climat"
OUT = RACINE / "resultats" / "climat"
URL_BIO = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_2.5m_bio.zip"
URL_ELEV = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_2.5m_elev.zip"
EMPRISE = (8.4, 1.6, 16.3, 13.2)           # lon_min, lat_min, lon_max, lat_max (Cameroun, rectangle)
EFFECTIFS = (30, 60, 120, 500, 2000)
K_REF = 5
GRAINE0 = 9000


# ------------------------------------------------------------------------------
# données
# ------------------------------------------------------------------------------

def preparer():
    DATA.mkdir(parents=True, exist_ok=True)
    for url in (URL_BIO, URL_ELEV):
        z = DATA / url.rsplit("/", 1)[1]
        if not z.exists():
            print("téléchargement", url, flush=True)
            urllib.request.urlretrieve(url, z)
        with zipfile.ZipFile(z) as f:
            f.extractall(DATA)
    OUT.mkdir(parents=True, exist_ok=True)
    (RACINE / "resultats").mkdir(exist_ok=True)
    import hashlib
    with open(RACINE / "resultats" / "climat_sources.txt", "w", encoding="utf-8") as f:
        f.write(f"Téléchargé le {time.strftime('%Y-%m-%d')}\n")
        for z in sorted(DATA.glob("*.zip")):
            f.write(f"{z.name}  sha256={hashlib.sha256(z.read_bytes()).hexdigest()}\n")
        f.write("Licence WorldClim : usage académique et non commercial ; redistribution interdite sans autorisation.\n")


def charger(d19=False, frontiere=None, koppen=None, zones=None):
    """Retourne X (N, D) brut, coordonnées (km), références {nom: étiquettes entières ou None}, lon/lat."""
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.features import geometry_mask

    def lire(chemin):
        with rasterio.open(chemin) as src:
            w = from_bounds(EMPRISE[0], EMPRISE[1], EMPRISE[2], EMPRISE[3], src.transform)
            a = src.read(1, window=w, masked=True).astype("float64")
            return a, src.window_transform(w)

    bios = {}
    for i in (range(1, 20) if d19 else (1, 4, 12, 15)):
        bios[i], tr = lire(DATA / f"wc2.1_2.5m_bio_{i}.tif")
    elev, _ = lire(DATA / "wc2.1_2.5m_elev.tif")
    masque = np.ma.getmaskarray(elev)
    for a in bios.values():
        masque |= np.ma.getmaskarray(a)
    H, W = elev.shape
    if frontiere:
        import geopandas as gpd
        geo = gpd.read_file(frontiere).to_crs(4326)
        masque |= geometry_mask(geo.geometry, out_shape=(H, W), transform=tr, invert=False)
    lignes, colonnes = np.where(~masque)
    lon = tr.c + (colonnes + 0.5) * tr.a
    lat = tr.f + (lignes + 0.5) * tr.e
    cols = []
    for i, a in bios.items():
        v = np.ma.getdata(a)[lignes, colonnes]
        cols.append(np.log(np.maximum(v, 1.0)) if (i == 12 or (d19 and i >= 13)) else v)
    cols.append(np.ma.getdata(elev)[lignes, colonnes])
    X = torch.tensor(np.stack(cols, axis=1), dtype=torch.float64)
    km = torch.tensor(np.stack([(lon - lon.mean()) * 111.32 * math.cos(math.radians(lat.mean())),
                                (lat - lat.mean()) * 110.57], axis=1), dtype=torch.float64)
    refs = {"koppen": None, "zones": None}
    if koppen:
        with rasterio.open(koppen) as src:
            vals = np.array([v[0] for v in src.sample(list(zip(lon, lat)))])
        _, refs["koppen"] = np.unique(vals, return_inverse=True)
        refs["koppen"] = torch.tensor(refs["koppen"])
    if zones:
        import geopandas as gpd
        from shapely.geometry import Point
        z = gpd.read_file(zones).to_crs(4326)
        pts = gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in zip(lon, lat)], crs=4326)
        j = gpd.sjoin(pts, z, how="left", predicate="within")
        j = j[~j.index.duplicated()]
        _, ids = np.unique(j["zone"].fillna("hors").values, return_inverse=True)
        refs["zones"] = torch.tensor(ids)
    return X, km, refs, (lon, lat)


def standardiser(X):
    return (X - X.mean(0)) / X.std(0).clamp(min=1e-12)


# ------------------------------------------------------------------------------
# expériences
# ------------------------------------------------------------------------------

def sous_echantillons(X, km, blocs, refs, rapide, d19, effectifs=None, R=None):
    """Protocole d'échantillonnage : R sous-échantillons espacés par effectif, test hors blocs."""
    R = R or (5 if rapide else 100)
    n_init = 3 if rapide else 10
    dist_min = 15.0
    lignes = []
    for N in (effectifs or EFFECTIFS + ("complet",)):
        reps = 1 if N == "complet" else R
        for r in range(reps):
            graine = GRAINE0 + r
            if N == "complet":
                idx = torch.arange(len(X))
            else:
                idx, _ = C.echantillon_espace(km, N, dist_min, graine)
            blocs_pris = torch.unique(blocs[idx])
            test = (~torch.isin(blocs, blocs_pris)).nonzero().flatten()
            if len(test) > 5000:
                test = test[torch.randperm(len(test), generator=A.generateur(graine))[:5000]]
            if len(test) < 50:                               # trop peu de blocs libres : repli sur un tirage aléatoire
                test = torch.randperm(len(X), generator=A.generateur(graine))[:2000]
            sortie = C.protocole_cinq_em_plus_vb(X[idx], K_REF, kmax=10, n_init=n_init, graine=graine)
            y_sub = {k: v[idx] for k, v in refs.items() if v is not None}
            for bras, res in sortie.items():
                if "echec" in res:
                    lignes.append({"N": N, "rep": r, "bras": bras, "echec": True}); continue
                est_vb = bras.startswith("VB")
                mod = {"pi": res["pi"], "mu": res["m"] if est_vb else res["mu"], "cov": res["cov"]}
                lg = {"N": N, "rep": r, "bras": bras, "echec": False, "k_hat": res["k_hat"],
                      "loglik_plugin": C.sure(lambda: C.logdens_plugin(mod, X[test])),
                      "loglik_predictive": C.sure(lambda: C.logdens_predictive_vb(res, X[test])) if est_vb else float("nan"),
                      "degenere": bool(res["degenere"]), "converge": bool(res["converge"]),
                      "temps_s": res["temps_total"], "n_iter": res["n_iter"],
                      "cout_par_iter": res.get("temps_par_iter", float("nan")), "D": X.shape[1]}
                for nom, y in y_sub.items():
                    lg[f"ARI_{nom}"] = A.indice_rand_ajuste(y, res["labels"])
                lignes.append(lg)
        print(f"  N = {N} terminé", flush=True)
    return pd.DataFrame(lignes)


def echantillon_posterieur_vb(res, n=300, graine=0):
    """Tirages de (pi_k, mu_k) sous q (covariance pleine) : pi ~ Dirichlet(alpha), Lambda ~ Wishart(W, nu), mu | Lambda ~ N(m, (beta Lambda)^-1)."""
    g = torch.distributions
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        P = res["P"]
        pis = g.Dirichlet(P["alpha"]).sample((n,))
        mus = []
        for k in range(len(P["alpha"])):
            lam = g.Wishart(df=P["nu"][k], covariance_matrix=P["W"][k]).sample((n,))
            cov = torch.linalg.inv(P["beta"][k] * lam)
            mus.append(g.MultivariateNormal(P["m"][k], covariance_matrix=cov).sample())
        mus = torch.stack(mus, dim=1)
    return pis, mus


def semi_synthetique(X, rapide, effectifs=None, R=None, B=None):
    """Ajuste K = 5 à N complet, simule R jeux par N ; vérité connue : K, ARI, couverture des IC (H1, H6, H7)."""
    R = R or (8 if rapide else 200)
    n_init = 3 if rapide else 10
    ref = A.em_classique(X, K_REF, n_init=n_init, graine=GRAINE0)
    lignes, couv = [], []
    for N in (effectifs or EFFECTIFS):
        for r in range(R if N <= 500 else max(R // 4, 4)):
            Xs, z = C.simuler_depuis_modele(ref, N, GRAINE0 + 1000 + r)
            sortie = C.protocole_cinq_em_plus_vb(Xs, K_REF, kmax=10, n_init=n_init, graine=GRAINE0 + r, avec_vb_diffus=False)
            for bras, res in sortie.items():
                if "echec" in res:
                    continue
                lignes.append({"N": N, "rep": r, "bras": bras, "k_hat": res["k_hat"], "erreur_k": abs(res["k_hat"] - K_REF),
                               "ARI": A.indice_rand_ajuste(z, res["labels"]), "degenere": bool(res["degenere"]),
                               "temps_s": res["temps_total"]})
            vb = sortie["VB-emp"]
            if vb["k_hat"] == K_REF and N >= 120:
                # couverture à 90 % des intervalles de crédibilité du VB sur pi_k et mu_k (composantes actives appariées)
                act = (vb["Nk"] / N >= 0.01).nonzero().flatten()
                col = A.hongrois(torch.cdist(ref["mu"], vb["m"][act]).pow(2))
                pis, mus = echantillon_posterieur_vb(vb, graine=r)
                for k_ref_i, j in enumerate(col.tolist()):
                    jj = act[j]
                    lo, hi = torch.quantile(pis[:, jj], torch.tensor([0.05, 0.95]))
                    couv.append({"N": N, "rep": r, "methode": "VB", "param": "pi", "couvert": float(bool(lo <= ref["pi"][k_ref_i] <= hi))})
                    lo, hi = torch.quantile(mus[:, jj, :], torch.tensor([0.05, 0.95]), dim=0)
                    couv.append({"N": N, "rep": r, "methode": "VB", "param": "mu",
                                 "couvert": float(((lo <= ref["mu"][k_ref_i]) & (ref["mu"][k_ref_i] <= hi)).to(torch.float64).mean())})
                # bootstrap EM (B petit, percentiles 5 % / 95 %) sur les mêmes jeux
                B = B or (20 if rapide else 100)
                em = A.em_classique(Xs, K_REF, n_init=1, graine=r)
                pis_b, mus_b = [], []
                for b in range(B):
                    ib = torch.randint(N, (N,), generator=A.generateur(r * 1000 + b))
                    eb = A.em_classique(Xs[ib], K_REF, n_init=1, graine=b)
                    c = A.hongrois(torch.cdist(em["mu"], eb["mu"]).pow(2))
                    pis_b.append(eb["pi"][c]); mus_b.append(eb["mu"][c])
                pis_b, mus_b = torch.stack(pis_b), torch.stack(mus_b)
                cm = A.hongrois(torch.cdist(ref["mu"], em["mu"]).pow(2))
                for k_ref_i, j in enumerate(cm.tolist()):
                    lo, hi = torch.quantile(pis_b[:, j], torch.tensor([0.05, 0.95]))
                    couv.append({"N": N, "rep": r, "methode": "bootstrap EM", "param": "pi", "couvert": float(bool(lo <= ref["pi"][k_ref_i] <= hi))})
                    lo, hi = torch.quantile(mus_b[:, j, :], torch.tensor([0.05, 0.95]), dim=0)
                    couv.append({"N": N, "rep": r, "methode": "bootstrap EM", "param": "mu",
                                 "couvert": float(((lo <= ref["mu"][k_ref_i]) & (ref["mu"][k_ref_i] <= hi)).to(torch.float64).mean())})
        print(f"  semi-synthétique N = {N} terminé", flush=True)
    return pd.DataFrame(lignes), pd.DataFrame(couv), ref


def sensibilite_priors(X, rapide):
    """H5 : variance de K̂ du VB due aux priors (plan factoriel) contre variance de K̂ de l'EM-BIC due à l'initialisation."""
    N = 500
    idx = torch.randperm(len(X), generator=A.generateur(GRAINE0))[:N]
    Xs = X[idx]
    plan = C.plan_factoriel(alpha0=(0.1, 1.0, 2.5, 10.0), beta0=(1e-3, 1.0, 10.0), nu0_plus=(0.0, 5.0), echelle_w0=(0.1, 1.0, 10.0))
    if rapide:
        plan = plan[::6]
    kvb = []
    for e in plan:
        v = A.em_variationnel(Xs, 10, priori=C.priori_du_plan(Xs, e), n_init=1, graine=GRAINE0)
        kvb.append(int((v["Nk"] / N >= 0.01).sum()))
    kem = []
    for s in range(len(plan)):
        kem.append(C.choisir_k_critere(Xs, 10, "bic", n_init=1, graine=GRAINE0 + s)["pi"].shape[0])
    df = pd.DataFrame(plan)
    df["k_vb"] = kvb
    dec = C.decomposition_variance(torch.tensor(kvb, dtype=torch.float64), {f: df[f].tolist() for f in ("alpha0", "beta0", "nu0_plus", "echelle_w0")})
    return df, dec, float(torch.tensor(kvb, dtype=torch.float64).var()), float(torch.tensor(kem, dtype=torch.float64).var())


def hypotheses(sous, semi, couv, var_vb, var_em):
    """Une ligne par hypothèse, critères fixés avant les résultats (voir en-tête du mémoire §Introduction)."""
    out = []

    def apparie(df, a, b, col, **flt):
        d = df
        for k, v in flt.items():
            d = d[d[k] == v]
        pa = d[d.bras == a].set_index("rep")[col]
        pb = d[d.bras == b].set_index("rep")[col]
        return (pa - pb).dropna()

    # H1 : |K̂ - K_ref| VB contre EM-BIC (et ICL), jeu semi-synthétique, marge 0,5
    for N1 in (30, 60, 120, 500, 2000):
        for b in ("EM-BIC", "EM-ICL"):
            d = apparie(semi, "VB-emp", b, "erreur_k", N=N1)
            if len(d):
                out.append(C.rapport_hypothese(f"H1[{b},N={N1}]", "Sélection de K", f"|K̂-K_ref| VB-emp - {b}, N = {N1}", d.tolist(), marge=0.5))
    # H2 : qualité à N complet (ARI et log-vraisemblance hors bloc), marges 0,03 et 0,02
    sous = sous.assign(N=sous.N.astype(str))
    semi = semi.assign(N=semi.N.astype(str))
    # H2 testée sur les sous-échantillons espacés de N = 2000 (le jeu complet n'a qu'une exécution) : différences appariées VB-emp - EM-BIC
    g = sous[(sous.N == "2000") & (~sous.echec.astype(bool))]
    for col, marge, nom in (("ARI_koppen", 0.03, "ARI contre Köppen-Geiger"), ("loglik_plugin", 0.02, "log-vraisemblance hors bloc (nat/obs, plug-in)")):
        if col in g.columns:
            d = (g[g.bras == "VB-emp"].set_index("rep")[col] - g[g.bras == "EM-BIC"].set_index("rep")[col]).dropna()
            if len(d):
                out.append(C.rapport_hypothese(f"H2[{col}]", "Qualité à grand N", f"{nom} : VB-emp - EM-BIC, N = 2000 (marge {marge})", d.tolist(), marge=marge))
    c = sous[(sous.N == "complet")]
    if len(c):
        out.append({"id": "H2[complet]", "axe": "Qualité à N complet", "enonce": "une seule exécution à N complet : descriptif, pas de test", "decision": "descriptif",
                    "intervalle": "", "pvalue": float("nan"), "n": 1, "niveau_preuve": "expérience unique", "references": ""})
    # H8 : dégénérescence à D = 20 (la dépendance aux priors à D = 20 n'est pas testée)
    f19 = OUT / "sous_echantillons_D20.csv"
    if f19.exists():
        s19 = pd.read_csv(f19)
        s19 = s19.assign(N=s19.N.astype(str))
        for N in sorted(s19.N.unique(), key=lambda v: (not v.isdigit(), int(v) if v.isdigit() else 0)):
            s = s19[s19.N == N].copy()
            s["dg"] = s.apply(lambda r: True if bool(r.echec) else bool(r.degenere), axis=1)   # un échec numérique compte comme ajustement dégénéré
            a, na = int(s[s.bras == "VB-emp"].dg.sum()), int((s.bras == "VB-emp").sum())
            b, nb = int(s[s.bras == "EM-Kmax"].dg.sum()), int((s.bras == "EM-Kmax").sum())
            if na and nb:
                p = fisher_exact(a, na - a, b, nb - b)
                out.append({"id": f"H8[N={N}]", "axe": "Dimension", "enonce": f"D = 20, dégénérés : VB-emp {a}/{na} contre EM-Kmax {b}/{nb} (dépendance aux priors à D = 20 : non testée)",
                            "decision": "VB < EM" if p < 0.05 and a < b else ("EM < VB" if p < 0.05 and b < a else "indéterminé"), "intervalle": "", "pvalue": p,
                            "n": na, "niveau_preuve": "expérience répliquée", "references": ""})
    # H3 : dégénérescence VB vs EM-Kmax pour N <= 120 (Fisher exact)
    for N in (30, 60, 120):
        s = sous[(sous.N == str(N)) & (~sous.echec.astype(bool))]
        a = s[s.bras == "VB-emp"].degenere.sum(); na = (s.bras == "VB-emp").sum()
        b = s[s.bras == "EM-Kmax"].degenere.sum(); nb = (s.bras == "EM-Kmax").sum()
        p = fisher_exact(int(a), int(na - a), int(b), int(nb - b))
        out.append({"id": f"H3[N={N}]", "axe": "Petit N", "enonce": f"dégénérés : VB-emp {a}/{na} contre EM-Kmax {b}/{nb}",
                    "decision": "VB < EM" if p < 0.05 and a < b else ("EM < VB" if p < 0.05 and b < a else "indéterminé"),
                    "intervalle": "", "pvalue": p, "n": int(na), "niveau_preuve": "expérience répliquée", "references": ""})
    # H4 : coût du pipeline EM-BIC contre un VB (rapport des temps médians)
    for N in EFFECTIFS:
        s = sous[sous.N == str(N)]
        t_em = s[s.bras == "EM-BIC"].temps_s.values; t_vb = s[s.bras == "VB-emp"].temps_s.values
        if len(t_em) and len(t_vb):
            r = torch.tensor(t_em).median() / torch.tensor(t_vb).median()
            _, lo, hi = C.ic_bootstrap(torch.tensor(t_em[:min(len(t_em), len(t_vb))] / t_vb[:min(len(t_em), len(t_vb))]), stat=torch.median)
            out.append({"id": f"H4[N={N}]", "axe": "Coût", "enonce": "temps médian EM-BIC / VB-emp (ratio > 1 : EM-BIC plus coûteux)",
                        "decision": "ratio > 1" if lo > 1 else ("ratio < 1" if hi < 1 else "indéterminé"), "estimation": float(r),
                        "intervalle": f"[{lo:.2f} ; {hi:.2f}]", "pvalue": float("nan"), "n": len(t_em), "niveau_preuve": "expérience répliquée", "references": ""})
    # H5 : variances de K̂
    out.append({"id": "H5", "axe": "Hyperparamètres", "enonce": f"Var(K̂) VB (priors) = {var_vb:.2f} contre Var(K̂) EM-BIC (initialisation) = {var_em:.2f}",
                "decision": "Var VB >= Var EM" if var_vb >= var_em else "Var VB < Var EM", "intervalle": "", "pvalue": float("nan"),
                "n": 0, "niveau_preuve": "expérience unique", "references": ""})
    # H6 : couverture
    if len(couv):
        for (meth, par), s in couv.groupby(["methode", "param"]):
            k = int(round(s.couvert.sum())); n = len(s)
            p, lo, hi = C.couverture_wilson(k, n)
            out.append({"id": f"H6[{meth},{par}]", "axe": "Incertitude", "enonce": f"couverture empirique à 90 % ({k:.0f}/{n})",
                        "decision": "< 90 %" if hi < 0.90 else (">= 90 %" if lo >= 0.90 else "compatible 90 %"), "estimation": p,
                        "intervalle": f"[{lo:.3f} ; {hi:.3f}] (Wilson)", "pvalue": float("nan"), "n": n,
                        "niveau_preuve": "expérience répliquée", "references": ""})
    # H7 : fusion de zones voisines : k̂ moyen par bras (semi-synthétique, N = 2000)
    s = semi[semi.N == "2000"]
    if len(s):
        m = s.groupby("bras").k_hat.mean()
        out.append({"id": "H7", "axe": "Chevauchement", "enonce": "K̂ moyen à N = 2000 : " + ", ".join(f"{k} {v:.2f}" for k, v in m.items()),
                    "decision": "VB fusionne plus" if m.get("VB-emp", 5) < m.get("EM-BIC", 5) else "non", "intervalle": "", "pvalue": float("nan"),
                    "n": int(len(s)), "niveau_preuve": "expérience répliquée", "references": ""})
    return out


def fisher_exact(a, b, c, d):
    """Test exact de Fisher bilatéral sur [[a, b], [c, d]] (hypergéométrique)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def pmf(x):
        return math.exp(math.lgamma(r1 + 1) - math.lgamma(x + 1) - math.lgamma(r1 - x + 1)
                        + math.lgamma(n - r1 + 1) - math.lgamma(c1 - x + 1) - math.lgamma(n - r1 - c1 + x + 1)
                        - (math.lgamma(n + 1) - math.lgamma(c1 + 1) - math.lgamma(n - c1 + 1)))
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    p0 = pmf(a)
    return min(1.0, sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p0 * (1 + 1e-9)))


def cartes(X, lon, lat, refs, rapide):
    """Cartes des classes, des responsabilités maximales et de l'entropie d'affectation (N complet)."""
    import plotly.graph_objects as go
    n_init = 3 if rapide else 10
    em = C.choisir_k_critere(X, 10, "bic", n_init, GRAINE0)
    vb = A.em_variationnel(X, 10, priori=A.priori_empirique(X, 0.1), n_init=n_init, graine=GRAINE0)
    jeux = {"EM-BIC": (em["labels"], em["r"]), "VB-emp": (vb["labels"], vb["r"])}
    OUT.mkdir(parents=True, exist_ok=True)
    for nom, (lab, r) in jeux.items():
        ent = -torch.xlogy(r, r).sum(1)
        for suffixe, z, titre in (("classes", lab.tolist(), "classes"), ("responsabilite", r.max(1).values.tolist(), "responsabilité maximale"),
                                  ("entropie", ent.tolist(), "entropie d'affectation (nat)")):
            fig = go.Figure(go.Scattergl(x=lon, y=lat, mode="markers", marker=dict(size=3, color=z, colorscale="Blues" if suffixe != "classes" else "Turbo", colorbar=dict(title=titre))))
            fig.update_layout(title=f"Cameroun, {nom} : {titre} (WorldClim 2.1, 2,5 min, {len(lon)} cellules)", xaxis_title="longitude (°)",
                              yaxis_title="latitude (°)", yaxis_scaleanchor="x", template="simple_white")
            fig.write_html(OUT / f"carte_{nom}_{suffixe}.html")
    for nom, y in refs.items():
        if y is not None:
            fig = go.Figure(go.Scattergl(x=lon, y=lat, mode="markers", marker=dict(size=3, color=y.tolist(), colorscale="Turbo")))
            fig.update_layout(title=f"Cameroun, référence {nom}", xaxis_title="longitude (°)", yaxis_title="latitude (°)", yaxis_scaleanchor="x", template="simple_white")
            fig.write_html(OUT / f"carte_reference_{nom}.html")
    # données des cartes (pour figures_climat.py) et nombres de classes retenues
    import numpy as np
    sortie = {"lon": lon, "lat": lat}
    for nom, (lab, r) in jeux.items():
        sortie[f"{nom}_classe"] = lab.numpy()
        sortie[f"{nom}_resp_max"] = r.max(1).values.numpy()
        sortie[f"{nom}_entropie"] = (-torch.xlogy(r, r).sum(1)).numpy()
    if refs.get("koppen") is not None:
        sortie["koppen"] = refs["koppen"].numpy()
    pd.DataFrame(sortie).to_csv(OUT / "cartes_donnees.csv", index=False)
    pd.DataFrame([{"methode": "EM-BIC", "K_retenu": len(em["pi"]), "n_actives_1pct": int((em["Nk"] / len(X) >= 0.01).sum())},
                  {"methode": "VB-emp", "K_retenu": 10, "n_actives_1pct": int((vb["Nk"] / len(X) >= 0.01).sum())}]).to_csv(OUT / "cartes_K.csv", index=False)
    return em, vb


def fusion(d19=False):
    """Concatène les morceaux par effectif et calcule la grille des hypothèses avec la correction de Holm."""
    import glob
    D = 20 if d19 else 5
    sous = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(OUT / f"sous_echantillons_D{D}_N*.csv")))], ignore_index=True)
    sous.to_csv(OUT / f"sous_echantillons_D{int(sous.D.iloc[0])}.csv", index=False)
    if d19:
        return
    semi = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(OUT / "semi_synthetique_N*.csv")))], ignore_index=True)
    couv = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(OUT / "couverture_N*.csv")))], ignore_index=True)
    semi.to_csv(OUT / "semi_synthetique.csv", index=False)
    couv["couvert"] = couv["couvert"].map(lambda v: 1.0 if str(v) == "True" else 0.0 if str(v) == "False" else float(v))
    couv.to_csv(OUT / "couverture.csv", index=False)
    dec = pd.read_csv(OUT / "decomposition_variance.csv")
    var = pd.read_csv(OUT / "variances_h5.csv").iloc[0]
    grille = pd.DataFrame(hypotheses(sous, semi, couv, float(var.var_vb), float(var.var_em)))
    # Holm sur les seuls tests qui produisent une p-valeur (les décisions par intervalle ne sont pas des tests)
    ok = grille["pvalue"].notna()
    aj, rej = C.holm(grille.loc[ok, "pvalue"].tolist())
    grille["p_holm"], grille["rejet_holm"] = float("nan"), False
    grille.loc[ok, "p_holm"], grille.loc[ok, "rejet_holm"] = aj, rej
    grille.to_csv(OUT / "grille_hypotheses_climat.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preparer", action="store_true")
    ap.add_argument("--rapide", action="store_true")
    ap.add_argument("--d19", action="store_true")
    ap.add_argument("--frontiere"); ap.add_argument("--koppen"); ap.add_argument("--zones")
    ap.add_argument("--partie", default="tout", choices=["tout", "sous", "semi", "sens", "cartes", "fusion"])
    ap.add_argument("--effectifs", default=None, help="liste séparée par des virgules, ex. 30,60,complet")
    ap.add_argument("--R", type=int, default=None, help="nombre de sous-échantillons par effectif (défaut 100)")
    ap.add_argument("--Rsemi", type=int, default=None, help="nombre de jeux semi-synthétiques par effectif (défaut 200)")
    ap.add_argument("--B", type=int, default=None, help="réplicats bootstrap de la couverture (défaut 100)")
    a = ap.parse_args()
    if a.preparer:
        preparer(); return
    OUT.mkdir(parents=True, exist_ok=True)
    if a.partie == "fusion":
        fusion(a.d19); return
    if not (DATA / "wc2.1_2.5m_elev.tif").exists():
        sys.exit("Données absentes : lancer d'abord  python cas_pratique_climat.py --preparer")
    X, km, refs, (lon, lat) = charger(a.d19, a.frontiere, a.koppen, a.zones)
    if not a.frontiere:
        print("AVERTISSEMENT : sans --frontiere l'emprise est rectangulaire (pays voisins inclus).")
    if refs["zones"] is None:
        print("Zones agro-écologiques absentes : la référence est Köppen-Geiger seul." if refs["koppen"] is not None
              else "Aucune référence fournie : ARI non calculé, seuls les critères sans étiquette sont rapportés.")
    X = standardiser(X)
    blocs = C.blocs_spatiaux(km, 100.0)
    print(f"N = {len(X)} cellules, D = {X.shape[1]}", flush=True)
    eff = None
    if a.effectifs:
        eff = tuple(e if e == "complet" else int(e) for e in a.effectifs.split(","))
    tag = "_".join(str(e) for e in eff) if eff else "tous"
    if a.partie in ("tout", "sous"):
        sous = sous_echantillons(X, km, blocs, refs, a.rapide, a.d19, eff, a.R)
        sous.to_csv(OUT / f"sous_echantillons_D{X.shape[1]}_N{tag}.csv", index=False)
    if not a.d19:
        if a.partie in ("tout", "semi"):
            eff_semi = tuple(e for e in eff if e != "complet") if eff else None
            if eff_semi is None or eff_semi:
                semi, couv, _ = semi_synthetique(X, a.rapide, eff_semi, a.Rsemi, a.B)
                semi.to_csv(OUT / f"semi_synthetique_N{tag}.csv", index=False)
                couv.to_csv(OUT / f"couverture_N{tag}.csv", index=False)
        if a.partie in ("tout", "sens"):
            plan, dec, vvb, vem = sensibilite_priors(X, a.rapide)
            plan.to_csv(OUT / "plan_factoriel.csv", index=False)
            pd.DataFrame([{"facteur": k, "part_variance": v} for k, v in dec.items()]).to_csv(OUT / "decomposition_variance.csv", index=False)
            pd.DataFrame([{"var_vb": vvb, "var_em": vem}]).to_csv(OUT / "variances_h5.csv", index=False)
        if a.partie in ("tout", "cartes"):
            cartes(X, lon, lat, refs, a.rapide)
    if a.partie == "tout":
        fusion(a.d19)


if __name__ == "__main__":
    main()
