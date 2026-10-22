"""Rend le protocole robuste aux échecs numériques (matrice non définie positive en dimension élevée) : l'échec est enregistré comme tel."""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "comparaison.py"
s = p.read_text(encoding="utf-8")

a = s.index("def choisir_k_critere(")
b = s.index("# ==============================================================================\n# ÉCHANTILLONNAGE SPATIAL")
nouveau = '''def choisir_k_critere(X: Tensor, kmax: int = 10, critere: str = "bic", n_init: int = 10, graine: int = 0):
    """Balaye K = 1..kmax par EM (n_init relances), retourne le meilleur ajustement et le temps total du balayage.
    Un K dont l'ajustement échoue numériquement (covariance non définie positive) est ignoré ; si tous échouent, l'erreur est levée."""
    t0 = time.perf_counter()
    meilleur, vals, echecs = None, {}, 0
    for K in range(1, kmax + 1):
        if K > X.shape[0] // 2:
            break
        try:
            res = A.em_classique(X, K, n_init=n_init, graine=graine)
        except Exception:
            echecs += 1
            continue
        vals[K] = res[critere]
        if meilleur is None or res[critere] < meilleur[critere]:
            meilleur = res
    if meilleur is None:
        raise RuntimeError("tous les ajustements EM du balayage ont échoué")
    meilleur = dict(meilleur)
    meilleur["temps_balayage"] = time.perf_counter() - t0
    meilleur["critere_par_k"] = vals
    meilleur["k_echecs"] = echecs
    return meilleur


def protocole_cinq_em_plus_vb(X: Tensor, k_ref: int, kmax: int = 10, n_init: int = 10, graine: int = 0,
                              avec_vb_diffus: bool = True, seuil_actif: float = 0.01):
    """
    Ajuste, avec le même critère d'arrêt, les bras :
        EM-5 (K = k_ref), EM-10 (K = kmax), EM-BIC, EM-ICL, MAP-EM (priors empiriques, alpha0 = 2),
        VB-emp, VB-diff (Kmax = kmax, alpha0 = 1/Kmax).
    Retourne {bras: dict de résultats} avec la clé "k_hat" (nombre de composantes retenu :
    K pour l'EM, composantes actives N_k / N >= seuil_actif pour MAP-EM et VB) et "temps_total".
    Un bras dont l'ajustement échoue numériquement est renvoyé sous la forme {"echec": message}.
    """
    N = X.shape[0]
    sortie = {}

    def actives(Nk):
        return int((Nk / N >= seuil_actif).sum())

    def essayer(nom, ajuster, k_hat):
        t0 = time.perf_counter()
        try:
            r = ajuster()
            r.update(k_hat=k_hat(r), temps_total=r.get("temps_balayage", time.perf_counter() - t0))
            sortie[nom] = r
        except Exception as e:
            sortie[nom] = {"echec": f"{type(e).__name__}: {str(e)[:80]}"}

    essayer("EM-K", lambda: A.em_classique(X, k_ref, n_init=n_init, graine=graine), lambda r: k_ref)
    essayer("EM-Kmax", lambda: A.em_classique(X, kmax, n_init=n_init, graine=graine), lambda r: kmax)
    for nom, crit in (("EM-BIC", "bic"), ("EM-ICL", "icl")):
        essayer(nom, lambda crit=crit: choisir_k_critere(X, kmax, crit, n_init, graine), lambda r: len(r["pi"]))
    pr = A.priori_empirique(X, 2.0)
    pr = A.PrioriNW(2.0, pr.m0, pr.beta0, pr.W0inv, pr.nu0)
    essayer("MAP-EM", lambda: A.map_em(X, kmax, pr, n_init=n_init, graine=graine), lambda r: actives(r["Nk"]))
    for nom, tp in (("VB-emp", "emp"),) + ((("VB-diff", "diff"),) if avec_vb_diffus else ()):
        essayer(nom, lambda tp=tp: A.em_variationnel(X, kmax, priori=prioris_vb(X, kmax, tp), n_init=n_init, graine=graine),
                lambda r: actives(r["Nk"]))
    return sortie


'''
s = s[:a] + nouveau + s[b:]
p.write_text(s, encoding="utf-8")
import ast
ast.parse(s)
print("protocole robuste aux échecs numériques")
