"""Outils du cas climatique sans données externes : point dans polygone (zonage IRAD), couverture par coordonnée."""
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import donnees_geo as G  # noqa: E402
import etape_climat as EC  # noqa: E402


def test_point_dans_polygone_avec_trou():
    carre = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    trou = [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]
    geom = {"type": "Polygon", "coordinates": [carre, trou]}
    lon = torch.tensor([1.0, 5.0, 11.0, 9.9, 5.0], dtype=torch.float64)
    lat = torch.tensor([1.0, 5.0, 5.0, 9.9, 2.0], dtype=torch.float64)
    assert G.dans_polygone(lon, lat, geom).tolist() == [True, False, False, True, True]
    multi = {"type": "MultiPolygon", "coordinates": [[carre], [[[20, 0], [30, 0], [30, 10], [20, 0]]]]}
    assert G.dans_polygone(torch.tensor([25.0, 15.0], dtype=torch.float64),
                           torch.tensor([2.0, 2.0], dtype=torch.float64), multi).tolist() == [True, False]


def test_couverture_par_coordonnee_et_non_appariee():
    ref = {"pi": torch.tensor([0.5, 0.5], dtype=torch.float64),
           "mu": torch.tensor([[0.0, 0.0], [10.0, 10.0]], dtype=torch.float64)}
    # une seule composante active, proche de la première : la seconde composante vraie n'est pas couverte
    pi_inf, pi_sup = torch.tensor([0.4]), torch.tensor([0.6])
    mu_inf, mu_sup = torch.tensor([[-1.0, 0.5]]), torch.tensor([[1.0, 2.0]])
    out = EC._couverts(ref, pi_inf, pi_sup, mu_inf, mu_sup, torch.tensor([[0.0, 1.0]], dtype=torch.float64),
                       torch.tensor([0]))
    assert out[0] == (0, 1.0, [1.0, 0.0])                 # x couvert, y hors intervalle
    assert out[1] == (1, 0.0, [0.0, 0.0])
    lignes = EC._lignes_couverture(120, 3, "VB", out)
    assert len(lignes) == 2 * (1 + 2) and all(l["couvert"] in (0.0, 1.0) for l in lignes)
