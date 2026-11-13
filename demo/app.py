"""
================================================================================
APPLICATION DE PRÉSENTATION DU CAS PRATIQUE : prix alimentaires du Cameroun (Dash)
================================================================================

python demo/app.py            puis ouvrir http://127.0.0.1:8051 dans le navigateur (port : variable ICARE_PORT)

Six pages : données, régimes, alerte, bulletin du mois, nouveau relevé (ajustements et tirages de demo/precalcul.py) et
résultats du mémoire (magasin confirmatoire, lecture seule). Le démarrage charge PyTorch : compter une à deux minutes sur le poste du mémoire, à faire AVANT la
soutenance ; la page s'affiche ensuite instantanément.
"""

import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path[:0] = [str(ICI), str(ICI.parent)]

t0 = time.perf_counter()
print("Chargement de PyTorch et des données (une à deux minutes)...", flush=True)
import service as SV  # noqa: E402

import dash  # noqa: E402
from dash import Dash, Input, Output, dcc, html  # noqa: E402

POLICES = ("https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,400;0,600;1,400"
           "&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap")

app = Dash(__name__, use_pages=True, pages_folder=str(ICI / "pages"), external_stylesheets=[POLICES],
           title="Prix alimentaires du Cameroun", update_title=None, suppress_callback_exceptions=True)


def _navigation():
    return html.Nav([dcc.Link(p["name"], href=p["relative_path"],
                              id={"type": "nav", "index": p["relative_path"]}, className="nav-lien")
                     for p in dash.page_registry.values()], className="nav")


app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div([
        html.Div([html.Span("Mémoire de KANA TIODONG Icare Brichel, cas pratique", className="marque-sur"),
                  html.Span("EM et EM variationnel : prix alimentaires du Cameroun", className="marque")],
                 className="marque-bloc"),
        _navigation(),
    ], className="barre"),
    html.Main(dash.page_container, className="contenu"),
    html.Footer([
        html.P(["Données : Programme alimentaire mondial, ", html.Em("Cameroon – Food Prices"),
                ", Humanitarian Data Exchange, licence CC BY-IGO ; extrait ", html.Code("data/prix/wfp_cmr_panier.csv"),
                " (empreinte SHA-256 vérifiée au chargement)."]),
        html.P(["Calculs : ", html.Code("etape_prix.py"), ", ", html.Code("comparaison.py"), ", ",
                html.Code("algorithmes.py"), " du dépôt du mémoire, appelés sans modification."]),
    ], className="pied"),
])


@app.callback(Output({"type": "nav", "index": dash.ALL}, "className"), Input("url", "pathname"))
def _lien_actif(chemin):
    return ["nav-lien actif" if p["relative_path"] == chemin else "nav-lien" for p in dash.page_registry.values()]


if __name__ == "__main__":
    port = int(__import__("os").environ.get("ICARE_PORT", "8051"))   # 8050 est pris par le suivi du mémoire de Miguel
    print(f"Prêt en {time.perf_counter() - t0:.0f} s : ouvrez http://127.0.0.1:{port}", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False)
