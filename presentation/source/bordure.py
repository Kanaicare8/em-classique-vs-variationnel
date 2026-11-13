"""
Bordure en oscillation des diapositives : deux sinusoïdes déphasées le long des quatre bords, centre transparent.

Usage : python bordure.py     (écrit visuels/bordure.png, au format 16:9 de la présentation)
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

SORTIE = Path(__file__).resolve().parent / "visuels" / "bordure.png"
L_PO, H_PO = 13.333, 7.5                 # format de la diapositive, en pouces
DPI, SUR = 200, 3                        # résolution finale ; suréchantillonnage pour lisser les courbes
FONCE, CLAIR = (20, 67, 42, 255), (46, 158, 100, 200)

MARGE = 0.17                             # distance de l'axe de la vague au bord (pouces)
AMPL = 0.055                             # amplitude (pouces)
PERIODE = 0.62                           # longueur d'onde (pouces)
EPAIS = (3.2, 2.0)                       # épaisseur des deux traits (pixels de l'image finale)


def px(v):
    return v * DPI * SUR


def vague(dessin, longueur, axe, horizontal, phase, couleur, epaisseur):
    n = int(longueur * 60)
    pts = []
    for i in range(n + 1):
        t = longueur * i / n
        d = axe + AMPL * math.sin(2 * math.pi * t / PERIODE + phase)
        pts.append((px(t), px(d)) if horizontal else (px(d), px(t)))
    dessin.line(pts, fill=couleur, width=max(1, round(epaisseur * SUR)), joint="curve")


def main():
    img = Image.new("RGBA", (round(px(L_PO)), round(px(H_PO))), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for phase, couleur, ep in ((0.0, CLAIR, EPAIS[1]), (math.pi, FONCE, EPAIS[0])):
        vague(d, L_PO, MARGE, True, phase, couleur, ep)                 # haut
        vague(d, L_PO, H_PO - MARGE, True, phase, couleur, ep)          # bas
        vague(d, H_PO, MARGE, False, phase, couleur, ep)                # gauche
        vague(d, H_PO, L_PO - MARGE, False, phase, couleur, ep)         # droite
    img = img.resize((round(L_PO * DPI), round(H_PO * DPI)), Image.LANCZOS)
    SORTIE.parent.mkdir(exist_ok=True)
    img.save(SORTIE)
    print("écrit", SORTIE, img.size)


if __name__ == "__main__":
    main()
