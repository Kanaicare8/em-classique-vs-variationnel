# Outil de suivi des prix alimentaires du Cameroun

Outil tiré du cas pratique du mémoire de KANA TIODONG Icare Brichel (décision D-20, `SUIVI/DECISIONS.md`).
Il publie chaque mois un bulletin des marchés et permet de saisir des relevés de prix. Pour chaque marché et chaque
mois, il donne la probabilité que les prix relèvent du régime de tension, avec un intervalle à 90 %.

C'est une aide à la lecture des marchés. Le régime de tension est appris sans étiquette (composante d'un mélange
gaussien), sans vérité terrain : une alerte appelle une vérification, pas une décision automatique.

## Ce que fait l'outil

| Page | Pour qui | Contenu |
|---|---|---|
| Bulletin | tous | marchés en alerte ou incertains d'un mois, par région ; export PDF et CSV |
| Marchés | tous | carte du mois, prix et probabilité d'un marché dans le temps |
| Saisie | agents, analystes | relevé de trois prix, lecture immédiate, enregistrement |
| Validation | analystes | relevés des agents à valider ou rejeter (écart suspect signalé) |
| Modèle et fiabilité | tous | provenance, régimes appris, épisodes datés, limites |
| Administration | administrateurs | comptes, extraits du PAM (HDX ou fichier), journal |

Rôles : administrateur, analyste, agent de collecte. Les relevés d'un agent entrent dans le bulletin une fois validés ;
ceux d'un analyste ou d'un administrateur sont validés d'office. Un relevé du PAM l'emporte sur un relevé saisi du même
marché, de la même denrée et du même mois.

## Modèles

- `modeles/memoire/` : modèle du mémoire, **référence figée** (EM-BIC et VB-emp ajustés sur 2021-04 à 2023-12,
  10 000 réplicats bootstrap pour EM-BIC, 8 000 tirages de q pour VB-emp). Exporté par `exporter_modele.py`
  (seul script qui demande PyTorch), jamais réécrit.
- Réestimations : chaque réestimation sera un nouveau dossier de `modeles/`, avec sa fiche (données, période,
  code). L'outil les propose à côté de la référence, sans la remplacer.

Le calcul en ligne se fait en NumPy. `tests/test_equivalence.py` vérifie qu'il redonne les écarts (à 1e-12) et les
probabilités et intervalles du mémoire (à 1e-6) :

```
python -m pytest outil/tests
```

## Lancer en local

À la racine du dépôt :

```
pip install -r outil/requirements.txt
set OUTIL_ADMIN_EMAIL=vous@exemple.org
set OUTIL_ADMIN_MOT_DE_PASSE=un-mot-de-passe-long
python outil/web/app.py
```

puis ouvrir http://127.0.0.1:8060. Le premier administrateur n'est créé que si la base n'a aucun compte ; la base
locale est `outil/instance/outil.db` (SQLite, non versionnée).

## Mettre en ligne (Railway par exemple)

L'image se construit depuis la racine du dépôt avec `outil/Dockerfile`. Variables à définir :

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | base Postgres (fournie par Railway quand on ajoute une base) |
| `OUTIL_SECRET` | clé de signature des sessions, longue et aléatoire |
| `OUTIL_ADMIN_EMAIL`, `OUTIL_ADMIN_MOT_DE_PASSE` | premier administrateur |
| `PORT` | fourni par la plateforme |

## Données

Base de prix du PAM, diffusée sur HDX (licence CC BY-IGO ; citer « World Food Programme, Cameroon - Food Prices,
Humanitarian Data Exchange »). L'administration télécharge le dernier extrait ou accepte un fichier ; il est filtré
comme dans le mémoire (prix de détail en XAF/kg du maïs blanc, du riz importé et du niébé).
