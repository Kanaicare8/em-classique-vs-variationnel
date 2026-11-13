// Régénère ../NOTES.md (notes lisibles sur GitHub) à partir de notes.js. Usage : node notes_md.js
const fs = require("fs");
const path = require("path");
const src = fs.readFileSync(path.join(__dirname, "notes.js"), "utf8");
const notes = require("./notes.js");
const titres = [...src.matchAll(/^\/\/ (\d+) · (.+)$/gm)].map((m) => [m[1], m[2]]);
let md = "# Notes de l'orateur : présentation de pré-soutenance\n\n" +
  "Présentation : [`Presoutenance_Icare.pptx`](Presoutenance_Icare.pptx) (aussi en [PDF](Presoutenance_Icare.pdf)), " +
  notes.length + " diapositives, 19 à 20 minutes, fond blanc pour une projection sur mur blanc. Les diapositives portent peu " +
  "de texte : les mots sont ici. Les durées entre parenthèses sont celles de chaque diapositive ; les indications entre " +
  "crochets sont des indications de jeu, à ne pas lire. Les chiffres sont ceux des tableaux du mémoire (`memoire/tables/`) ; " +
  "les figures sont celles du mémoire, re-tracées depuis les résultats déjà calculés ; les deux schémas marqués « illustration » " +
  "ne portent aucun résultat. Source : [`source/`](source/).\n\n";
titres.forEach(([n, t], i) => { md += "## " + n + ". " + t + "\n\n" + notes[i].trim().split("\n").join("\n\n") + "\n\n"; });
fs.writeFileSync(path.join(__dirname, "..", "NOTES.md"), md);
console.log(titres.length, "titres,", notes.length, "notes");
