"""Téléchargements du bulletin : /export/bulletin.csv et /export/bulletin.pdf (?mois=aaaa-mm&mode=...&version=...)."""

from __future__ import annotations

import csv
import io
from datetime import date

from flask import Response, request

import composants as CO
import service as SV
from bulletin_calc import bulletin


def _parametres():
    st = SV.etat(request.args.get("version") or SV.REFERENCE)
    mois = request.args.get("mois")
    t = SV.mois_index(mois) if mois else max(st["mois"])
    mode = request.args.get("mode") or "accord"
    if mode != "accord" and mode not in st["proba"]:
        mode = "accord"
    return st, t, mode


def csv_bulletin():
    st, t, mode = _parametres()
    b = bulletin(st, t, mode)
    f = io.StringIO()
    w = csv.writer(f, delimiter=";")
    noms = st["modele"].fiche["noms"]
    w.writerow(["mois", "marche", "region", "etat", "modele"] +
               [f"{br}_{c}" for br in st["proba"] for c in ("p_tension", "ic90_bas", "ic90_haut")] +
               [f"prix_{n}_xaf_kg" for n in noms] + [f"ecart_{n}" for n in noms])
    for l in b["toutes"]:
        w.writerow([SV.mois_texte(t), l["marche"], l["region"], l["lecture"], st["modele"].version] +
                   [f"{v:.4f}" for br in st["proba"] for v in l["bras"][br]] +
                   [f"{p:.0f}" if p else "" for p in l["prix"]] + [f"{e:.4f}" for e in l["ecarts"]])
    return Response("﻿" + f.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=bulletin_{SV.mois_texte(t)}_{mode}.csv"})


def pdf_bulletin():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    st, t, mode = _parametres()
    b = bulletin(st, t, mode)
    vert, gris = colors.HexColor("#1F7A4D"), colors.HexColor("#52514e")
    ss = getSampleStyleSheet()
    titre = ParagraphStyle("t", parent=ss["Title"], textColor=vert, alignment=0, fontSize=18)
    h2 = ParagraphStyle("h", parent=ss["Heading2"], textColor=vert, fontSize=13)
    corps = ParagraphStyle("c", parent=ss["BodyText"], fontSize=9.5, leading=13)
    petit = ParagraphStyle("p", parent=corps, fontSize=8, textColor=gris)

    def tab(lignes, largeurs=None):
        tb = Table(lignes, colWidths=largeurs, repeatRows=1, hAlign="LEFT")
        tb.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TEXTCOLOR", (0, 0), (-1, 0), vert),
                                ("LINEBELOW", (0, 0), (-1, 0), 0.8, vert), ("LINEBELOW", (0, -1), (-1, -1), 0.5, gris),
                                ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        return tb

    f = io.BytesIO()
    doc = SimpleDocTemplate(f, pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, title=f"Bulletin des marchés {SV.mois_texte(t)}")
    el = [Paragraph(f"Bulletin des marchés, {SV.mois_humain(t)}", titre),
          Paragraph(b["phrase"], corps), Spacer(1, 4),
          Paragraph(f"Modèle : {st['modele'].fiche['libelle']} ; lecture : {b['mode_texte']} ; données : "
                    f"{st['extrait']['origine']} ; édité le {date.today():%d/%m/%Y}.", petit),
          Paragraph("Par région", h2),
          Paragraph(f"Marchés observés : {len(b['toutes'])} ; en alerte : {len(b['alerte'])} ; à surveiller : "
                    f"{len(b['surveiller'])}.", corps),
          tab([["Région", "Marchés observés", "En alerte", "À surveiller", "D'habitude en alerte"]] +
              [[r["region"], r["n"], r["alerte"], r["surveiller"], CO.pourcent(r["habituelle"], 0)]
               for r in b["regions"]])]
    el.append(Paragraph("Marchés à surveiller", h2))
    if b["a_voir"]:
        noms = st["modele"].fiche["noms"]
        el.append(tab([["Marché", "Région", "État", "Probabilité", "Fourchette"] + [f"{n} (XAF/kg)" for n in noms]] +
                      [[l["marche"], l["region"], l["lecture"], l["p_txt"], l["ic_txt"]] +
                       [f"{p} ({e})" for p, e in zip(l["prix_txt"], l["ecarts_txt"])] for l in b["a_voir"]]))
    else:
        el.append(Paragraph("Aucun marché en alerte ni à surveiller ce mois-là.", corps))
    el += [Spacer(1, 10), Paragraph(
        "Probabilité : chance que les écarts de prix du marché relèvent du régime de tension appris sur 2021-2023 "
        "(composante d'un mélange gaussien aux écarts les plus élevés). Fourchette : intervalle à 90 % de cette "
        "probabilité. Alerte : probabilité au-dessus de 50 % ; à surveiller : la fourchette contient 50 % ou les deux "
        "méthodes divergent. Entre parenthèses : écart du prix à sa moyenne des douze mois précédents. Outil d'aide à la lecture, sans "
        "vérité terrain : une alerte appelle une vérification, pas une décision automatique. Source des prix : World "
        "Food Programme, Cameroon - Food Prices, Humanitarian Data Exchange (CC BY-IGO).", petit)]
    doc.build(el)
    return Response(f.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=bulletin_{SV.mois_texte(t)}.pdf"})
