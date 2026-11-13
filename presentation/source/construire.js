// Présentation de pré-soutenance d'Icare : comparaison de l'EM classique et de l'EM variationnel.
// Projection sur un mur blanc : fond blanc partout. Un titre descriptif et un visuel par diapositive ; les figures
// viennent de visuels.py (re-tracées depuis les résultats du mémoire) ; les chiffres sont ceux de memoire/tables/.
//
// Usage (depuis ce dossier) :  npm install      puis   node construire.js [sortie.pptx]
// Montage (animations, transitions) :  powershell -File animer.ps1 -Source <brut.pptx> -Sortie <final.pptx>
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ICI = __dirname;
const VIS = (f) => path.join(ICI, "visuels", f + ".png");
const LOGO = (f) => path.join(ICI, "logos", f);
const SORTIE = path.resolve(process.argv[2] || path.join(ICI, "..", "Presoutenance_Icare_brut.pptx"));
const NOTES = require("./notes.js");

const FONCE = "14432A", VERT = "1F7A4D", CLAIR = "2E9E64", PALE = "EEF5F0", SAUGE = "7A9E8A";
const AMBRE = "D89A2B", ROUGE = "B03A2E", INK = "1E2124", GRIS = "5F656B", LIGNE = "C9D6CD", BLANC = "FFFFFF";
const H = "Segoe UI Semibold", B = "Segoe UI";
const W = 13.333, HT = 7.5, M = 0.75;
const TOTAL = NOTES.length;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "KANA TIODONG Icare Brichel";
pres.title = "Comparaison entre l'algorithme EM classique et l'EM variationnel";
pres.subject = "Présentation de l'état d'avancement des travaux de Master recherche";
pres.company = "ENSPD, Université de Douala";
pres.theme = { headFontFace: H, bodyFontFace: B };

function taille(p) { const b = fs.readFileSync(p); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; }
function image(s, p, x, y, w, h, o = {}) {
  const t = taille(p), r = Math.min(w / t.w, h / t.h), iw = t.w * r, ih = t.h * r;
  const dx = o.align === "left" ? 0 : o.align === "right" ? w - iw : (w - iw) / 2;
  s.addImage({ path: p, x: x + dx, y: o.valign === "top" ? y : y + (h - ih) / 2, w: iw, h: ih, altText: o.alt || path.basename(p) });
}
function texte(s, t, o) { s.addText(t, Object.assign({ isTextBox: true, fontFace: B, fontSize: 18, color: INK, margin: 0, valign: "top" }, o)); }
// Paragraphe dont le début est en gras : [["Début", " suite du texte."]]
function phrases(s, items, x, y, w, h, taillePolice = 19) {
  const runs = [];
  items.forEach(([gras, suite], i) => {
    runs.push({ text: gras, options: { bold: true, color: FONCE } });
    runs.push({ text: suite, options: { color: INK, breakLine: i < items.length - 1 } });
    if (i < items.length - 1) runs.push({ text: " ", options: { breakLine: true, fontSize: 8 } });
  });
  s.addText(runs, { x, y, w, h, isTextBox: true, fontFace: B, fontSize: taillePolice, margin: 0, valign: "top", paraSpaceAfter: 6 });
}

// Bordure en oscillation (visuels/bordure.png, produite par bordure.py), sur toute la diapositive
function bordure(s) { s.addImage({ path: VIS("bordure"), x: 0, y: 0, w: W, h: HT, altText: "Bordure" }); }

let numero = 0;
// Titre, puis pied de page (partie à gauche, numéro à droite) : ces trois formes viennent en premier et restent
// fixes au montage.
function page(partie, titre) {
  numero += 1;
  const s = pres.addSlide();
  s.background = { color: BLANC };
  bordure(s);
  texte(s, titre, { x: M, y: 0.45, w: W - 2 * M, h: 1.0, fontFace: H, fontSize: 34, color: FONCE, valign: "middle" });
  texte(s, partie, { x: M, y: 6.93, w: 8, h: 0.26, fontSize: 12, color: GRIS });
  texte(s, numero + " / " + TOTAL, { x: W - M - 1.6, y: 6.93, w: 1.6, h: 0.26, fontSize: 12, color: GRIS, align: "right" });
  if (NOTES[numero - 1]) s.addNotes(NOTES[numero - 1]);
  return s;
}
function source(s, t) { texte(s, t, { x: M, y: 6.56, w: W - 2 * M, h: 0.3, fontSize: 13, color: GRIS }); }

// Barres horizontales dessinées une à une (le montage les fait pousser depuis l'axe)
let nBarre = 0;
function barresH(s, items, x, y, w, h, o = {}) {
  const max = o.max || Math.max(...items.map((t) => t[1])) * 1.1, lw = o.largeurEtiquette || 2.6;
  const pas = h / items.length, eb = Math.min(0.55, pas * 0.62), zone = w - lw - 1.0;
  items.forEach(([lab, v, c], i) => {
    const bw = Math.max(0.02, zone * v / max), by = y + i * pas + (pas - eb) / 2;
    nBarre++;
    texte(s, lab, { x, y: by, w: lw - 0.15, h: eb, fontSize: 16, color: INK, align: "right", valign: "middle", objectName: "lab" + nBarre });
    s.addShape(pres.shapes.RECTANGLE, { x: x + lw, y: by, w: bw, h: eb, fill: { color: c }, line: { color: c }, objectName: "barreH" + nBarre });
    const val = String(v).replace(".", ",") + (o.unite || "");
    texte(s, val, o.dedans
      ? { x: x + lw + bw - 1.15, y: by, w: 1.05, h: eb, fontFace: H, fontSize: 17, color: BLANC, align: "right", valign: "middle", objectName: "val" + nBarre }
      : { x: x + lw + bw + 0.1, y: by, w: 1.0, h: eb, fontFace: H, fontSize: 17, color: FONCE, valign: "middle", objectName: "val" + nBarre });
  });
}

// ═══════════════ 1. Page de garde ═══════════════
{
  numero += 1;
  const s = pres.addSlide();
  s.background = { color: BLANC };
  // en-tête institutionnel, aligné à gauche, logos côte à côte
  image(s, LOGO("logo_udo.png"), M, 0.5, 1.05, 1.05, { align: "left", alt: "Logo de l'Université de Douala" });
  image(s, LOGO("logo_enspd.png"), M + 1.2, 0.5, 1.05, 1.05, { align: "left", alt: "Logo de l'ENSPD" });
  s.addText([
    { text: "UNIVERSITÉ DE DOUALA", options: { bold: true, breakLine: true } },
    { text: "The University of Douala", options: { italic: true, color: GRIS, breakLine: true } },
    { text: "École Nationale Supérieure Polytechnique de Douala (ENSPD)", options: { breakLine: true } },
    { text: "Département de Génie Informatique", options: { bold: true } },
  ], { x: M + 2.5, y: 0.45, w: 6.2, h: 1.1, isTextBox: true, fontFace: B, fontSize: 14, color: INK, margin: 0, valign: "middle" });
  s.addText([
    { text: "Mémoire de Master", options: { bold: true, color: FONCE, breakLine: true } },
    { text: "Master of Science en Data Science", options: { breakLine: true } },
    { text: "et Intelligence Artificielle (SDIA)" },
  ], { x: 8.6, y: 0.45, w: W - M - 8.6, h: 1.1, isTextBox: true, fontFace: B, fontSize: 14, color: INK, margin: 0, align: "right", valign: "middle" });
  // double filet
  s.addShape(pres.shapes.LINE, { x: M, y: 1.78, w: W - 2 * M, h: 0, line: { color: FONCE, width: 2.25 } });
  s.addShape(pres.shapes.LINE, { x: M, y: 1.86, w: W - 2 * M, h: 0, line: { color: CLAIR, width: 0.75 } });
  texte(s, "Présentation de l'état d'avancement des travaux de Master recherche", { x: M, y: 2.1, w: W - 2 * M, h: 0.35, fontSize: 15, color: VERT });
  texte(s, "Comparaison entre l'algorithme EM classique\net l'EM variationnel", { x: M, y: 2.55, w: W - 2 * M, h: 1.6, fontFace: H, fontSize: 38, color: FONCE, lineSpacingMultiple: 1.0 });
  texte(s, "Avantages, inconvénients et applications", { x: M, y: 4.2, w: W - 2 * M, h: 0.5, fontSize: 22, italic: true, color: GRIS });
  // bande basse : auteur et directeurs
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.15, w: W, h: 2.35, fill: { color: PALE }, line: { color: PALE } });
  texte(s, "Dressé et présenté par", { x: M, y: 5.45, w: 5, h: 0.3, fontSize: 13, color: GRIS });
  texte(s, "KANA TIODONG Icare Brichel", { x: M, y: 5.75, w: 5.5, h: 0.45, fontFace: H, fontSize: 23, color: FONCE });
  texte(s, "Année académique 2025-2026", { x: M, y: 6.55, w: 5, h: 0.35, fontSize: 14, color: GRIS });
  texte(s, "Sous la co-direction de", { x: 6.9, y: 5.45, w: 5.7, h: 0.3, fontSize: 13, color: GRIS });
  s.addText([
    { text: "Prof. Dr. habil. P. NJIONOU SADJANG", options: { bold: true, color: FONCE, breakLine: true } },
    { text: "Professeur Associé, ENSPD", options: { color: GRIS, breakLine: true } },
    { text: "Prof. Patrice TAKAM SOH", options: { bold: true, color: FONCE, breakLine: true } },
    { text: "Professeur Associé, Université de Yaoundé 1", options: { color: GRIS } },
  ], { x: 6.9, y: 5.78, w: 5.7, h: 1.3, isTextBox: true, fontFace: B, fontSize: 15, margin: 0, valign: "top" });
  bordure(s);
  s.addNotes(NOTES[0]);
}

// ═══════════════ 2. Question de recherche ═══════════════
{
  const s = page("Introduction", "Question de recherche");
  texte(s, "Que gagne-t-on, et que perd-on, en passant de l'algorithme EM classique à l'EM variationnel, et sur quelles preuves ?",
    { x: M, y: 2.0, w: 11.3, h: 2.2, fontFace: H, fontSize: 32, color: FONCE });
  texte(s, "Chaque avantage et chaque inconvénient est relié à une preuve : un théorème, une expérience répliquée, une expérience unique, ou la mention « non testé ».",
    { x: M, y: 4.6, w: 11.3, h: 1.2, fontSize: 21, color: INK });
}

// ═══════════════ 3. Le problème ═══════════════
{
  const s = page("Introduction", "Retrouver des groupes non étiquetés");
  image(s, VIS("groupes"), M, 1.7, 5.9, 4.9, { align: "left" });
  phrases(s, [["Des données", " sans étiquettes."], ["Un nombre de groupes", " inconnu."],
              ["Des paramètres à estimer :", " poids, centres et formes des groupes."]], 7.2, 2.4, 5.4, 3.5, 22);
}

// ═══════════════ 4. L'EM ═══════════════
{
  const s = page("Partie I. Fondements", "L'algorithme EM classique");
  s.addShape(pres.shapes.OVAL, { x: 1.4, y: 2.0, w: 3.3, h: 3.3, fill: { color: FONCE }, line: { color: FONCE } });
  texte(s, "Étape E", { x: 1.4, y: 2.55, w: 3.3, h: 0.9, fontFace: H, fontSize: 34, color: BLANC, align: "center", valign: "middle" });
  texte(s, "probabilité qu'un point\nappartienne à chaque\ncomposante", { x: 1.6, y: 3.45, w: 2.9, h: 1.3, fontSize: 16, color: BLANC, align: "center" });
  s.addShape(pres.shapes.OVAL, { x: 8.6, y: 2.0, w: 3.3, h: 3.3, fill: { color: CLAIR }, line: { color: CLAIR } });
  texte(s, "Étape M", { x: 8.6, y: 2.55, w: 3.3, h: 0.9, fontFace: H, fontSize: 34, color: BLANC, align: "center", valign: "middle" });
  texte(s, "mise à jour des poids,\ncentres et covariances", { x: 8.8, y: 3.45, w: 2.9, h: 1.3, fontSize: 16, color: BLANC, align: "center" });
  s.addShape(pres.shapes.LINE, { x: 4.95, y: 3.0, w: 3.4, h: 0, line: { color: FONCE, width: 3.5, endArrowType: "triangle" } });
  texte(s, "responsabilités", { x: 4.95, y: 2.55, w: 3.4, h: 0.35, fontSize: 16, color: GRIS, align: "center" });
  s.addShape(pres.shapes.LINE, { x: 4.95, y: 4.3, w: 3.4, h: 0, flipH: true, line: { color: CLAIR, width: 3.5, endArrowType: "triangle" } });
  texte(s, "paramètres", { x: 4.95, y: 4.4, w: 3.4, h: 0.35, fontSize: 16, color: GRIS, align: "center" });
  texte(s, "On répète jusqu'à convergence. La vraisemblance croît à chaque itération ; le résultat est un seul jeu de paramètres, et le nombre de composantes K est fixé à l'avance.",
    { x: M, y: 5.65, w: W - 2 * M, h: 0.9, fontSize: 19, color: INK, align: "center" });
}

// ═══════════════ 5. L'EM variationnel ═══════════════
{
  const s = page("Partie I. Fondements", "L'algorithme EM variationnel");
  image(s, VIS("point_loi"), M, 1.65, W - 2 * M, 4.0);
  texte(s, "Le VB place des lois a priori sur les paramètres et renvoie une loi approchée, au lieu d'un point.",
    { x: M, y: 5.8, w: W - 2 * M, h: 0.5, fontSize: 20, color: INK, align: "center" });
  source(s, "Schéma d'illustration, sans résultat.");
}

// ═══════════════ 6. Décomposition de la log-évidence ═══════════════
{
  const s = page("Partie I. Fondements", "Décomposition de la log-évidence");
  s.addShape(pres.shapes.RECTANGLE, { x: M, y: 1.9, w: W - 2 * M, h: 1.0, fill: { color: FONCE }, line: { color: FONCE } });
  texte(s, "log p(X)", { x: M + 0.35, y: 1.9, w: 5.5, h: 1.0, fontFace: H, fontSize: 32, color: BLANC, valign: "middle" });
  texte(s, "log-évidence des données", { x: 6.2, y: 1.9, w: 6.0, h: 1.0, fontSize: 19, color: BLANC, valign: "middle", align: "right" });
  texte(s, "=", { x: M, y: 2.95, w: 1.2, h: 0.65, fontFace: H, fontSize: 40, color: GRIS, valign: "middle" });
  s.addShape(pres.shapes.RECTANGLE, { x: M, y: 3.65, w: 8.35, h: 1.0, fill: { color: CLAIR }, line: { color: CLAIR } });
  texte(s, "ELBO", { x: M + 0.35, y: 3.65, w: 3, h: 1.0, fontFace: H, fontSize: 32, color: BLANC, valign: "middle" });
  texte(s, "borne inférieure maximisée", { x: 4.0, y: 3.65, w: 4.9, h: 1.0, fontSize: 19, color: BLANC, valign: "middle", align: "right" });
  s.addShape(pres.shapes.RECTANGLE, { x: M + 8.35, y: 3.65, w: W - 2 * M - 8.35, h: 1.0, fill: { color: AMBRE }, line: { color: AMBRE } });
  texte(s, "+ KL(q ‖ p)", { x: M + 8.6, y: 3.65, w: 3.4, h: 1.0, fontFace: H, fontSize: 28, color: FONCE, valign: "middle" });
  texte(s, "La divergence KL étant positive, l'ELBO minore la log-évidence, et la maximiser réduit l'écart entre l'approximation q et la loi a posteriori. Les deux algorithmes optimisent cette même borne ; ils diffèrent par la famille de q.",
    { x: M, y: 5.1, w: W - 2 * M, h: 1.3, fontSize: 20, color: INK });
}

// ═══════════════ 7. Élagage ═══════════════
{
  const s = page("Partie I. Fondements", "Élagage des composantes par l'EM variationnel");
  image(s, VIS("ellipses"), 0.9, 1.6, 11.5, 4.6);
  texte(s, "Mêmes données, six composantes permises : l'EM les garde toutes, le VB en conserve trois.", { x: M, y: 6.2, w: W - 2 * M, h: 0.4, fontSize: 19, color: INK, align: "center" });
  source(s, "Jeu synthétique de référence (300 points, trois groupes), figure 1.4 du mémoire.");
}

// ═══════════════ 8. Poids ═══════════════
{
  const s = page("Partie I. Fondements", "Poids des composantes après ajustement");
  image(s, VIS("poids"), M, 1.55, 8.4, 4.9, { align: "left" });
  phrases(s, [["EM :", " six poids non nuls, dont deux groupes coupés en deux."],
              ["VB :", " trois poids de un tiers, et trois poids réduits à 0,001."]], 9.4, 2.4, 3.2, 3.5, 19);
  source(s, "Même ajustement que la diapositive précédente.");
}

// ═══════════════ 9. Effets du champ moyen ═══════════════
{
  const s = page("Partie I. Fondements", "Effets de l'approximation en champ moyen");
  image(s, VIS("deux_effets"), M, 1.6, W - 2 * M, 4.2);
  texte(s, "Conséquence pratique : des intervalles de crédibilité plus étroits que la loi exacte.", { x: M, y: 5.95, w: W - 2 * M, h: 0.5, fontSize: 20, color: INK, align: "center" });
  source(s, "Schéma d'illustration, sans résultat. Gauche : effet de la divergence KL inverse ; droite : effet de la factorisation.");
}

// ═══════════════ 10. Trois niveaux d'inférence ═══════════════
{
  const s = page("Partie I. Fondements", "Trois niveaux d'inférence");
  const niv = [[0.9, 4.1, 1.95, SAUGE, "Maximum de vraisemblance", "EM classique : un point"],
               [4.85, 3.2, 2.85, CLAIR, "Maximum a posteriori", "MAP-EM : un point régularisé"],
               [8.8, 2.3, 3.75, FONCE, "Bayes complet", "EM variationnel : une loi sur les paramètres"]];
  niv.forEach(([x, y, h, c, t, d]) => {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.6, h, fill: { color: c }, line: { color: c } });
    texte(s, t, { x: x + 0.25, y: y + 0.2, w: 3.15, h: 0.9, fontFace: H, fontSize: 21, color: BLANC });
    texte(s, d, { x: x + 0.25, y: y + 1.05, w: 3.15, h: 0.8, fontSize: 17, color: BLANC });
  });
  texte(s, "Le MAP-EM porte les priors du VB sans loi sur les paramètres : il isole l'effet des priors.", { x: M, y: 6.25, w: W - 2 * M, h: 0.4, fontSize: 18, color: INK });
}

// ═══════════════ 11. Protocole ═══════════════
{
  const s = page("Partie II. Méthodologie", "Protocole de comparaison");
  const et = [["Données", "scénarios synthétiques S1 à S10, Iris, prix du PAM"], ["Méthodes", "EM-K, EM-Kmax, EM-BIC, MAP-EM, VB"],
              ["Règles communes", "même critère d'arrêt, mêmes relances, mêmes graines"], ["Tests déclarés", "équivalence (TOST), Wilcoxon, correction de Holm"]];
  et.forEach(([t, d], i) => {
    const x = M + i * 3.05;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.2, w: 2.7, h: 2.6, fill: { color: i % 2 ? PALE : BLANC }, line: { color: FONCE, width: 1.25 } });
    texte(s, t, { x: x + 0.2, y: 2.35, w: 2.3, h: 0.85, fontFace: H, fontSize: 20, color: FONCE, valign: "middle" });
    texte(s, d, { x: x + 0.2, y: 3.3, w: 2.3, h: 1.4, fontSize: 17, color: INK });
    if (i < 3) s.addShape(pres.shapes.LINE, { x: x + 2.72, y: 3.5, w: 0.31, h: 0, line: { color: GRIS, width: 2, endArrowType: "triangle" } });
  });
  texte(s, "Les tests et leurs marges sont déclarés avant les calculs confirmatoires ; les paramètres sont fixés par un calibrage écrit à l'avance.",
    { x: M, y: 5.3, w: W - 2 * M, h: 0.9, fontSize: 19, color: INK });
}

// ═══════════════ 12. Hypothèses ═══════════════
{
  const s = page("Partie II. Méthodologie", "Hypothèses de recherche");
  const rh = [["RH1", "Aucune supériorité générale de l'un sur l'autre"], ["RH2", "Le choix de K se déplace vers les priors et K max"],
              ["RH3", "Les intervalles du VB couvrent moins que leur niveau annoncé"], ["RH4", "À petit effectif, le VB dégénère moins, par l'effet des priors"],
              ["RH5", "Un ajustement VB coûte plus qu'un ajustement EM"]];
  s.addTable([[{ text: "Hypothèse", options: { bold: true, color: BLANC, fill: { color: FONCE } } }, { text: "Énoncé", options: { bold: true, color: BLANC, fill: { color: FONCE } } }],
              ...rh.map(([a, b], i) => [{ text: a, options: { bold: true, color: FONCE, fill: { color: i % 2 ? PALE : BLANC } } }, { text: b, options: { color: INK, fill: { color: i % 2 ? PALE : BLANC } } }])],
    { x: M, y: 1.75, w: W - 2 * M, colW: [2.0, W - 2 * M - 2.0], rowH: 0.72, fontFace: B, fontSize: 20, valign: "middle", border: { type: "solid", pt: 0.75, color: LIGNE }, margin: [0.05, 0.15, 0.05, 0.15] });
}

// ═══════════════ 13. Bilan des décisions ═══════════════
{
  const s = page("Partie III. Résultats", "Bilan des 63 décisions déclarées");
  const lab = ["RH1", "RH2", "RH3", "RH4", "RH5"];
  s.addChart(pres.charts.BAR, [
    { name: "Conformes", labels: lab, values: [11, 1, 4, 11, 4] }, { name: "Contraires", labels: lab, values: [0, 0, 4, 0, 0] },
    { name: "Non tranchées", labels: lab, values: [12, 4, 1, 4, 1] }, { name: "Sans sens prédit", labels: lab, values: [6, 0, 0, 0, 0] }],
    { x: M, y: 1.6, w: 8.6, h: 4.9, barDir: "bar", barGrouping: "stacked", chartColors: [VERT, ROUGE, AMBRE, "A9B0B5"], barGapWidthPct: 40,
      catAxisOrientation: "maxMin", catAxisLabelFontSize: 18, catAxisLabelColor: INK, valAxisLabelFontSize: 14, valAxisLabelColor: GRIS,
      valGridLine: { color: "E6ECE8", size: 1 }, catGridLine: { style: "none" }, showLegend: true, legendPos: "t", legendFontSize: 16, legendColor: INK,
      showValue: true, dataLabelFontSize: 15, dataLabelColor: BLANC, dataLabelFontBold: true, dataLabelFormatCode: "0;;;" });
  phrases(s, [["31", " conformes à l'hypothèse."], ["4", " contraires, toutes sur la couverture du bootstrap de l'EM."],
              ["22", " non tranchées, dont 9 équivalences non démontrées."], ["6", " différences sans sens prédit."]], 9.7, 2.3, 2.9, 4.2, 18);
}

// ═══════════════ 14. Qualité de partition (RH1) ═══════════════
{
  const s = page("Partie III. Résultats", "Qualité de partition : VB contre EM-BIC (RH1)");
  s.addChart(pres.charts.BAR, [{ name: "Gain d'ARI du VB", labels: ["Groupes à 2 écarts-types", "Groupes à 3 écarts-types", "Dimension 10", "Dimension 20"], values: [0.17, 0.28, 0.28, 0.79] }],
    { x: M, y: 1.55, w: 7.6, h: 4.9, barDir: "col", chartColors: [CLAIR, CLAIR, FONCE, FONCE], barGapWidthPct: 45, showLegend: false,
      showValue: true, dataLabelFontSize: 17, dataLabelColor: FONCE, dataLabelFontBold: true, dataLabelFormatCode: "0.00",
      catAxisLabelFontSize: 14, catAxisLabelColor: INK, valAxisLabelFontSize: 14, valAxisLabelColor: GRIS, valAxisMaxVal: 0.9, valAxisMinVal: 0,
      valGridLine: { color: "E6ECE8", size: 1 }, catGridLine: { style: "none" }, showValAxisTitle: true, valAxisTitle: "gain d'ARI du VB sur l'EM-BIC", valAxisTitleFontSize: 14, valAxisTitleColor: GRIS });
  phrases(s, [["Groupes qui se chevauchent ou dimension élevée :", " le VB retrouve mieux les groupes (différences démontrées, S1 et S5)."],
              ["Groupes séparés ou aberrations :", " les deux sont équivalents à la marge de 0,05 d'ARI."],
              ["Petit effectif :", " le VB produit moins d'ajustements dégénérés (S6)."]], 8.7, 1.9, 3.9, 4.6, 18);
  source(s, "Scénarios synthétiques répliqués. ARI : indice de Rand ajusté, accord entre groupes retrouvés et groupes vrais.");
}

// ═══════════════ 15. Priors (RH2) ═══════════════
{
  const s = page("Partie III. Résultats", "Composantes retenues selon les priors (RH2)");
  image(s, VIS("priors"), M, 1.5, 8.6, 4.8, { align: "left" });
  phrases(s, [["Au-delà d'un seuil de concentration,", " le VB cesse d'élaguer."],
              ["Sur le cas pratique,", " la variance du nombre de composantes du VB entre priors plausibles dépasse celle de l'EM entre ses propres choix (écart de 3,2, test HP5)."]], 9.5, 1.9, 3.1, 4.5, 17);
  source(s, "Courbe : scénario S8, synthétique, descriptif.");
}

// ═══════════════ 16. Couverture (RH3) ═══════════════
{
  const s = page("Partie III. Résultats", "Couverture des intervalles à 90 % (RH3)");
  const items = [["VB, poids", 22, CLAIR], ["Bootstrap EM-BIC, poids", 44, FONCE], ["Bootstrap EM-K, poids", 48, SAUGE],
                 ["VB, moyennes", 64, CLAIR], ["Bootstrap EM-BIC, moyennes", 78, FONCE], ["Bootstrap EM-K, moyennes", 82, SAUGE]];
  const x = M, y = 1.75, w = 10.4, h = 3.9, lw = 3.6, max = 100;
  const xN = x + lw + (w - lw - 1.0) * 90 / max;
  s.addShape(pres.shapes.LINE, { x: xN, y: y - 0.1, w: 0, h: h + 0.1, line: { color: ROUGE, width: 2.5, dashType: "dash" } });
  barresH(s, items, x, y, w, h, { largeurEtiquette: lw, max, unite: " %", dedans: true });
  texte(s, "niveau annoncé : 90 %", { x: xN - 1.3, y: y + h + 0.05, w: 2.6, h: 0.35, fontSize: 16, color: ROUGE, align: "center" });
  texte(s, "Aucun intervalle n'atteint 90 % ; ceux du VB couvrent le moins, comme le prévoit le champ moyen.", { x: M, y: 6.1, w: W - 2 * M, h: 0.45, fontSize: 19, color: INK });
  source(s, "Jeu semi-synthétique tiré du modèle des prix (cas pratique, test HP6).");
}

// ═══════════════ 17. Coût (RH5) : intervalles de rapports de temps ═══════════════
{
  const s = page("Partie III. Résultats", "Coût de calcul (RH5)");
  const x0 = 4.6, x1 = 12.3, vmax = 6, X = (v) => x0 + (x1 - x0) * v / vmax, yAxe = 4.75;
  s.addShape(pres.shapes.LINE, { x: x0, y: yAxe, w: x1 - x0, h: 0, line: { color: GRIS, width: 1.25 } });
  for (let v = 0; v <= vmax; v++) {
    s.addShape(pres.shapes.LINE, { x: X(v), y: yAxe, w: 0, h: 0.1, line: { color: GRIS, width: 1 } });
    texte(s, "× " + v, { x: X(v) - 0.4, y: yAxe + 0.15, w: 0.8, h: 0.3, fontSize: 14, color: GRIS, align: "center" });
  }
  s.addShape(pres.shapes.LINE, { x: X(1), y: 1.9, w: 0, h: yAxe - 1.9, line: { color: ROUGE, width: 2, dashType: "dash" } });
  texte(s, "coût égal", { x: X(1) - 0.75, y: 1.6, w: 1.5, h: 0.3, fontSize: 14, color: ROUGE, align: "center" });
  const lignes = [["Une itération du VB rapportée à une itération de l'EM", "données synthétiques", 1.1, 2.2, FONCE, 2.35],
                  ["Pipeline EM-BIC rapporté à un ajustement VB", "cas pratique, N ≥ 60 (test HP4)", 2.6, 5.0, CLAIR, 3.55]];
  lignes.forEach(([t, d, a, b, c, y]) => {
    nBarre++;
    s.addText([{ text: t, options: { breakLine: true, color: INK } }, { text: d, options: { color: GRIS, fontSize: 13 } }],
      { x: M, y: y - 0.12, w: x0 - M - 0.2, h: 0.85, isTextBox: true, fontFace: B, fontSize: 16, margin: 0, align: "right", valign: "middle", objectName: "lab" + nBarre });
    s.addShape(pres.shapes.RECTANGLE, { x: X(a), y, w: X(b) - X(a), h: 0.6, fill: { color: c }, line: { color: c }, objectName: "barreH" + nBarre });
    texte(s, String(a).replace(".", ",") + " à " + String(b).replace(".", ","), { x: X(b) + 0.12, y, w: 1.6, h: 0.6, fontFace: H, fontSize: 18, color: FONCE, valign: "middle", objectName: "val" + nBarre });
  });
  texte(s, "Une itération du VB coûte plus, mais choisir K par EM-BIC coûte plus qu'un seul ajustement VB.", { x: M, y: 5.6, w: W - 2 * M, h: 0.5, fontSize: 19, color: INK });
}

// ═══════════════ 18. Cas pratique : régimes et prévision ═══════════════
{
  const s = page("Partie III. Résultats, cas pratique", "Cas pratique : régimes retenus et prévision");
  texte(s, "Régimes retenus sur les prix du Cameroun (apprentissage 2021-2023)", { x: M, y: 1.7, w: 6.5, h: 0.4, fontFace: H, fontSize: 17, color: FONCE });
  barresH(s, [["EM-BIC", 2, FONCE], ["VB, priors empiriques", 4, CLAIR], ["VB, priors calibrés", 8, CLAIR]], M, 2.4, 6.4, 3.6, { largeurEtiquette: 2.6, max: 9 });
  phrases(s, [["Prévision.", " Sur 32 mois de test, aucune des six comparaisons de log-score n'est significative (Diebold-Mariano, correction de Holm) : aucun mélange ne prévoit mieux qu'une loi gaussienne simple."],
              ["Alerte.", " EM-BIC et VB classent de la même façon 83,8 % des observations."]], 7.6, 1.75, 5.0, 4.6, 19);
  source(s, "Données : Programme alimentaire mondial (HDX). Test de janvier 2024 à août 2026.");
}

// ═══════════════ 19. Cas pratique : alerte ═══════════════
{
  const s = page("Partie III. Résultats, cas pratique", "Cas pratique : alerte sur deux mois documentés");
  image(s, VIS("carte"), M, 1.55, W - 2 * M, 4.2);
  texte(s, "Août 2023 : hausse du maïs, plusieurs marchés passent en alerte.\nAvril 2026 : baisse des prix, les marchés restent presque tous calmes.", { x: M, y: 5.8, w: W - 2 * M, h: 0.75, fontSize: 18, color: INK, align: "center" });
  source(s, "Extrême-Nord. Probabilité du régime de tension par marché ; alerte au-dessus de 0,5.");
}

// ═══════════════ 20. Guide de choix ═══════════════
{
  const s = page("Conclusion", "Guide de choix");
  s.addShape(pres.shapes.OVAL, { x: 0.7, y: 2.65, w: 2.6, h: 1.9, fill: { color: FONCE }, line: { color: FONCE } });
  texte(s, "Situation", { x: 0.7, y: 2.65, w: 2.6, h: 1.9, fontFace: H, fontSize: 24, color: BLANC, align: "center", valign: "middle" });
  const br = [["K connu", "EM ou VB"], ["Groupes qui se chevauchent", "VB"], ["Besoin d'une incertitude", "Bootstrap de l'EM-BIC"], ["Petit effectif", "Des priors : VB ou MAP-EM"]];
  br.forEach(([c, r], i) => {
    const y = 1.8 + i * 1.12, yc = y + 0.4, y0 = 3.6, dy = yc - y0;
    s.addShape(pres.shapes.LINE, { x: 3.3, y: dy >= 0 ? y0 : yc, w: 1.0, h: Math.abs(dy), flipV: dy < 0, line: { color: LIGNE, width: 3 } });
    s.addShape(pres.shapes.RECTANGLE, { x: 4.3, y, w: 3.75, h: 0.8, fill: { color: PALE }, line: { color: PALE } });
    texte(s, c, { x: 4.5, y, w: 3.45, h: 0.8, fontFace: H, fontSize: 18, color: FONCE, valign: "middle" });
    s.addShape(pres.shapes.LINE, { x: 8.15, y: yc, w: 0.6, h: 0, line: { color: CLAIR, width: 3, endArrowType: "triangle" } });
    s.addShape(pres.shapes.RECTANGLE, { x: 8.85, y, w: 3.8, h: 0.8, fill: { color: i === 1 ? CLAIR : FONCE }, line: { color: i === 1 ? CLAIR : FONCE } });
    texte(s, r, { x: 9.0, y, w: 3.5, h: 0.8, fontFace: H, fontSize: 18, color: BLANC, valign: "middle" });
  });
  texte(s, "Dans tous les cas, comparer d'abord à une loi gaussienne simple.", { x: M, y: 6.3, w: W - 2 * M, h: 0.4, fontSize: 17, color: INK });
}

// ═══════════════ 21. Conclusion ═══════════════
{
  const s = page("Conclusion", "Conclusion");
  phrases(s, [["Pas de supériorité générale :", " le VB fait mieux sur des groupes qui se chevauchent, les deux sont équivalents ailleurs."],
              ["Le choix de K se déplace :", " il dépend des priors du VB et de K max."],
              ["La régularisation vient des priors :", " le MAP-EM obtient le même effet."],
              ["L'incertitude du VB n'est pas calibrée :", " ses intervalles couvrent bien moins que leur niveau annoncé."]], M, 1.8, 11.6, 3.9, 21);
  texte(s, "Merci de votre attention.", { x: M, y: 5.9, w: W - 2 * M, h: 0.6, fontFace: H, fontSize: 26, color: VERT });
}

(async () => {
  await pres.writeFile({ fileName: SORTIE });
  console.log("écrit :", SORTIE, numero, "diapositives");
})();
