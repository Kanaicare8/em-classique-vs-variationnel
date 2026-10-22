"""Ajoute au carnet code.ipynb les cellules des scénarios, du cas climatique, du S&P 500 (compléments) et du texte, puis la production des tableaux."""
import json
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "code.ipynb"
nb = json.loads(p.read_text(encoding="utf-8"))


def md(txt):
    return {"cell_type": "markdown", "metadata": {}, "source": txt.splitlines(True)}


def code(txt):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": txt.splitlines(True)}


nouvelles = [
    md("## 16bis. Scénarios synthétiques S1 à S10 et comparaison avec EM-BIC et EM-ICL\n"
       "Chaque scénario compte au moins 30 réplications et compare EM-K, EM-Kmax, EM-BIC, EM-ICL, MAP-EM et le VB avec le **même critère d'arrêt**. "
       "Durée complète : plusieurs heures (un processus par scénario conseillé, voir `A_REGENERER.md`). `RAPIDE` lance une version réduite."),
    code("import subprocess, sys\n"
         "def lancer(*args):\n"
         "    r = subprocess.run([sys.executable, *args], capture_output=True, text=True)\n"
         "    print(r.stdout[-2000:] or r.stderr[-2000:])\n"
         "lancer('scenarios.py', *(['--rapide'] if RAPIDE else []), 'S1', 'S2', 'S3')   # priorité absolue ; les autres : S4 à S10\n"
         "lancer('scenarios.py', '--regrille')"),
    code("display(pd.read_csv(M.SORTIE / 'grille_scenarios.csv')[['id', 'decision', 'estimation', 'intervalle', 'p_holm']])"),
    md("## 16ter. Cas principal : régimes climatiques du Cameroun\n"
       "Données WorldClim 2.1 (téléchargement par `python cas_pratique_climat.py --preparer`, redistribution interdite) et Köppen–Geiger (Beck et al., 2018). "
       "Le zonage agro-écologique officiel n'étant pas disponible, la référence est Köppen–Geiger seul. Hypothèses H1 à H8 fixées avant l'analyse (tableau du chapitre 3)."),
    code("K = ['--koppen', 'data/climat/koppen/Beck_KG_V1_present_0p0083.tif', '--frontiere', 'data/climat/frontiere/cameroun.shp']\n"
         "if (M.DOSSIER / 'data' / 'climat' / 'wc2.1_2.5m_elev.tif').exists():\n"
         "    lancer('cas_pratique_climat.py', *K, *(['--rapide'] if RAPIDE else []))\n"
         "else:\n"
         "    print('Données absentes : lancer python cas_pratique_climat.py --preparer')"),
    code("g = M.SORTIE / 'climat' / 'grille_hypotheses_climat.csv'\n"
         "if g.exists(): display(pd.read_csv(g)[['id', 'decision', 'estimation', 'intervalle', 'p_holm']])"),
    md("## 16quater. S&P 500 : compléments (Student-t, GARCH-t, simulation historique, Christoffersen, ES, filtrage forward)"),
    code("lancer('cas_pratique_sp500_complement.py', *(['--rapide'] if RAPIDE else []))\n"
         "display(pd.read_csv(M.SORTIE / 'sp500_backtests.csv'))"),
    md("## 16quinquies. pLSA contre LDA sur un corpus réel (20 Newsgroups)"),
    code("lancer('texte_plsa_lda.py', *(['--rapide'] if RAPIDE else []))\n"
         "display(pd.read_csv(M.SORTIE / 'texte_plsa_lda.csv'))"),
    md("## 16sexies. Production des tableaux du mémoire\n`tex_tables.py` écrit `tables/*.tex` à partir de `resultats/` : aucun nombre n'est saisi à la main."),
    code("lancer('tex_tables.py')"),
]
i = next(k for k, c in enumerate(nb["cells"]) if "".join(c["source"]).startswith("## 17. Export des figures"))
nb["cells"][i:i] = nouvelles
p.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("carnet mis à jour :", len(nb["cells"]), "cellules")
