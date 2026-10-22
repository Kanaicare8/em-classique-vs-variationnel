"""Rend en PNG les pages du PDF qui contiennent un mot-clé (contrôle visuel des schémas) : python apercu_pages.py mot [mot ...]"""
import sys
from pathlib import Path

import fitz

R = Path(__file__).resolve().parent.parent
sortie = Path(sys.argv[0]).resolve().parent / "apercus"
sortie.mkdir(exist_ok=True)
doc = fitz.open(R / "main.pdf")
for mot in sys.argv[1:]:
    for i, page in enumerate(doc):
        if mot in page.get_text():
            f = sortie / f"p{i + 1:03d}.png"
            page.get_pixmap(dpi=80).save(f)
            print(mot, "-> page", i + 1, f.name)
            break
