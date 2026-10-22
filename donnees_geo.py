"""
================================================================================
LECTURE DES FORMATS GÉOGRAPHIQUES (seul module qui utilise rasterio et geopandas)
================================================================================

Ces bibliothèques ne servent qu'à DÉCODER les fichiers (GeoTIFF, shapefile) ; aucun calcul de modèle
n'y est fait. Le résultat est converti en tenseurs PyTorch et mis en cache dans data/climat/cache_D*.pt :
les étapes de calcul ne lisent que ce cache.

Données (licences vérifiées, voir A_REGENERER.md) :
  WorldClim 2.1, 2,5 minutes d'arc (Fick et Hijmans 2017) : usage académique, redistribution interdite ;
  Köppen-Geiger 1 km, version 1 (Beck et al. 2018), figshare 6396959 : CC BY 4.0 ;
  contour du Cameroun : Natural Earth 1:10 m (domaine public).
Variables (D = 5) : bio1, bio4, ln(bio12), bio15, altitude. Extension (D = 20) : bio1 à bio19 et altitude ;
seules les QUANTITÉS de précipitations (bio12, bio13, bio14, bio16, bio17, bio18, bio19) passent au
logarithme ; bio15 (saisonnalité, coefficient de variation) reste en l'état, comme à D = 5.
Coordonnées en km : projection équirectangulaire locale (cos de la latitude moyenne).
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import torch

import persistance as PE

DATA = Path(__file__).parent / "data" / "climat"
EMPRISE = (8.4, 1.6, 16.3, 13.2)                      # lon_min, lat_min, lon_max, lat_max
PRECIP_QUANTITES = {12, 13, 14, 16, 17, 18, 19}
FRONTIERE = DATA / "frontiere" / "cameroun.shp"
KOPPEN = DATA / "koppen" / "Beck_KG_V1_present_0p0083.tif"


def _lire_raster(chemin, transform_ref=None):
    import rasterio
    from rasterio.windows import from_bounds
    with rasterio.open(chemin) as src:
        w = from_bounds(*EMPRISE, src.transform)
        a = src.read(1, window=w, masked=True).astype("float64")
        return a, src.window_transform(w)


def _decoder(D: int) -> dict:
    import numpy as np
    from rasterio.features import geometry_mask
    import geopandas as gpd
    import rasterio
    variables = range(1, 20) if D == 20 else (1, 4, 12, 15)
    bios = {}
    for i in variables:
        bios[i], tr = _lire_raster(DATA / f"wc2.1_2.5m_bio_{i}.tif")
    elev, _ = _lire_raster(DATA / "wc2.1_2.5m_elev.tif")
    masque = np.ma.getmaskarray(elev)
    for a in bios.values():
        masque |= np.ma.getmaskarray(a)
    H, W = elev.shape
    geo = gpd.read_file(FRONTIERE).to_crs(4326)
    masque |= geometry_mask(geo.geometry, out_shape=(H, W), transform=tr, invert=False)
    lignes, colonnes = np.where(~masque)
    lon = tr.c + (colonnes + 0.5) * tr.a
    lat = tr.f + (lignes + 0.5) * tr.e
    cols, noms = [], []
    for i, a in bios.items():
        v = np.ma.getdata(a)[lignes, colonnes]
        if i in PRECIP_QUANTITES:
            cols.append(np.log(np.maximum(v, 1.0)))
            noms.append(f"ln(bio{i})")
        else:
            cols.append(v)
            noms.append(f"bio{i}")
    cols.append(np.ma.getdata(elev)[lignes, colonnes])
    noms.append("altitude")
    with rasterio.open(KOPPEN) as src:
        kg = np.array([v[0] for v in src.sample(list(zip(lon, lat)))])
    codes, kg_idx = np.unique(kg, return_inverse=True)
    lat0 = float(lat.mean())
    km = np.stack([(lon - lon.mean()) * 111.32 * math.cos(math.radians(lat0)), (lat - lat.mean()) * 110.57], axis=1)
    return {"X": torch.tensor(np.stack(cols, axis=1)), "noms": noms, "lon": torch.tensor(lon), "lat": torch.tensor(lat),
            "km": torch.tensor(km), "koppen": torch.tensor(kg_idx), "koppen_codes": torch.tensor(codes.astype("int64")),
            "decode_le": time.strftime("%Y-%m-%d")}


def charger_climat(D: int = 5) -> dict:
    """Données climatiques du Cameroun (cache tensoriel, décodé une seule fois)."""
    assert D in (5, 20)
    cache = DATA / f"cache_D{D}.pt"
    if cache.exists():
        return PE.charger(cache)
    d = _decoder(D)
    PE.sauver(cache, d)
    return d


def standardiser(X: torch.Tensor) -> torch.Tensor:
    return (X - X.mean(0)) / X.std(0).clamp(min=1e-12)
