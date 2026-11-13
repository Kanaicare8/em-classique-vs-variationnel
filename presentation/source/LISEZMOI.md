# Source de la présentation

| Fichier | Rôle |
|---|---|
| `construire.js` | construit les diapositives (pptxgenjs) |
| `notes.js` | notes de l'orateur, une entrée par diapositive |
| `notes_md.js` | régénère `../NOTES.md`, les notes lisibles sur GitHub |
| `visuels.py` | figures : re-tracées depuis les résultats du mémoire (`emvb.figures`), et deux schémas d'illustration |
| `visuels/` | figures déjà produites (refaire les figures réelles demande le magasin de résultats) |
| `animer.ps1` | montage : transitions et animations, posées par PowerPoint |
| `bordure.py` | bordure en oscillation des diapositives (`visuels/bordure.png`) |
| `logos/` | logos de l'Université de Douala et de l'ENSPD |

Reconstruire (Windows, PowerPoint installé), depuis ce dossier :

```
npm install
node construire.js ../Presoutenance_Icare_brut.pptx
powershell -File animer.ps1 -Source ..\Presoutenance_Icare_brut.pptx -Sortie ..\Presoutenance_Icare.pptx
node notes_md.js
```

Pour refaire les figures : `python visuels.py concept` (schémas) ou `python visuels.py reel` (figures réelles).
