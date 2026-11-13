# Guide : publier le mémoire sur Zenodo et obtenir un DOI

*À suivre par KANA TIODONG Icare Brichel, propriétaire du dépôt GitHub `Kanaicare8/em-classique-vs-variationnel`.
Durée : environ 20 minutes. Rien n'est à installer.*

## 1. À quoi cela sert

Zenodo est une archive scientifique ouverte, gérée par le CERN. Elle prend une copie figée du dépôt à une date donnée
et lui attribue un **DOI** : un identifiant permanent, que l'on peut citer dans le mémoire, sur un CV ou dans un
article, et qui désignera toujours exactement cette version du code et des résultats. GitHub seul ne le garantit pas :
un dépôt peut être modifié, renommé ou supprimé.

## 2. Ce qu'il faut savoir avant de publier

- **Une publication est définitive.** Le contenu d'une version publiée ne peut plus être modifié ni retiré, et le DOI
  ne disparaît pas. On peut seulement publier une nouvelle version, qui reçoit un nouveau DOI.
- **Le contenu devient public** : tout ce qui est dans le dépôt à cette version, y compris l'historique des
  décisions (`SUIVI/`). Relisez ce qui vous gêne avant de publier.
- **Une licence est demandée.** Le dépôt n'en a pas encore. Voir l'étape 3.
- **Les données du PAM** (`data/prix/`) sont sous licence CC BY-IGO : leur redistribution est autorisée avec
  attribution, et le `README` la mentionne.

## 3. Choisir une licence (avant tout)

Sans licence, le code est publié mais personne n'a le droit de le réutiliser. À vous de choisir :

| Licence | Effet |
|---|---|
| **MIT** | tout le monde peut réutiliser le code, à condition de citer votre nom ; la plus simple |
| **Apache 2.0** | comme MIT, avec une protection explicite sur les brevets |
| **CC BY 4.0** | adaptée au texte du mémoire plutôt qu'au code ; réutilisation avec attribution |

Un choix courant pour un mémoire avec son code : **MIT pour le code** et **CC BY 4.0 pour le texte**. Demandez
conseil à votre encadreur si l'ENSPD a une règle sur la propriété intellectuelle.

Pour l'ajouter : sur la page GitHub du dépôt, bouton **Add file**, **Create new file**, nommez le fichier `LICENSE` ;
GitHub propose alors **Choose a license template** : choisissez-en une, saisissez votre nom et l'année, puis validez
(**Commit changes**).

## 4. Relier Zenodo à GitHub (une seule fois)

1. Allez sur <https://zenodo.org> et cliquez sur **Log in**, puis **Log in with GitHub**.
   Connectez-vous avec le compte qui possède le dépôt (**Kanaicare8**).
2. GitHub demande d'autoriser Zenodo : acceptez.
3. Cliquez sur votre nom en haut à droite, puis **GitHub**.
   (Adresse directe : <https://zenodo.org/account/settings/github/>.)
4. Si la liste est vide, cliquez sur **Sync now** et attendez quelques secondes.
5. Dans la liste, trouvez `Kanaicare8/em-classique-vs-variationnel` et mettez l'interrupteur sur **ON**.

À partir de là, chaque *release* GitHub sera archivée automatiquement par Zenodo.

## 5. Vérifier les métadonnées (avant de publier)

Le dépôt contient deux fichiers qui renseignent Zenodo : `.zenodo.json` et `CITATION.cff`. Zenodo en lit les
champs : titre, auteur, directeurs de mémoire, mots-clés, résumé. Ouvrez-les sur GitHub et vérifiez :

- votre nom : `KANA TIODONG, Icare Brichel` ;
- les deux directeurs : Prof. Dr. habil. P. NJIONOU SADJANG et Prof. Patrice TAKAM SOH ;
- le titre et le résumé.

Pour corriger, modifiez le fichier sur GitHub (icône crayon), puis validez. Si vous le modifiez **après** avoir créé
la release, il faudra créer une nouvelle release : Zenodo lit les fichiers au moment de la release.

Vous pouvez aussi ajouter votre identifiant **ORCID** (gratuit, <https://orcid.org>) : dans `.zenodo.json`, à la ligne
de l'auteur, ajoutez `"orcid": "0000-0000-0000-0000"` avec votre numéro ; dans `CITATION.cff`, ajoutez
`orcid: "https://orcid.org/0000-0000-0000-0000"`.

## 6. Publier : créer une release GitHub

1. Sur la page GitHub du dépôt, colonne de droite, cliquez sur **Releases**, puis **Create a new release**
   (ou **Draft a new release**).
2. Dans **Choose a tag**, choisissez l'étiquette de la version à publier. Pour la version finale rangée :
   **`v1.3`** (voir la note ci-dessous).
3. **Release title** : `Version 1.3, mémoire final`.
4. **Description** : une ou deux phrases, par exemple « Version finale du mémoire, du code et des résultats ».
5. Cliquez sur **Publish release**.

> **Quelle étiquette ?** `v1.0` est la version rendue ; `v1.0.1` y ajoute le `README` et les métadonnées ;
> `v1.1` range le dépôt en dossiers (`emvb/`, `memoire/`, `demo/`, `bulletin/`…) sans changer le texte ni les
> résultats ; `v1.2` recentre l'introduction du mémoire sur son thème et remplace la présentation ; `v1.3` complète la
> présentation avec les résultats du cas pratique. C'est la bonne
> version à archiver : c'est la plus récente, et la seule dont le texte et la présentation sont les définitifs. Si
> une étiquette encore plus récente existe sur GitHub, prenez la plus récente de la forme `v1.x`.

## 7. Récupérer le DOI

1. Retournez sur <https://zenodo.org/account/settings/github/> : sous le dépôt, la version apparaît quelques minutes
   après la release, avec un badge **DOI**.
2. Cliquez sur le badge : vous arrivez sur la page de l'archive, avec le DOI complet (de la forme
   `10.5281/zenodo.1234567`).
3. Sur cette page, à droite, **Versions** donne deux DOI : celui de **cette version** (à citer pour désigner
   exactement ce que vous avez archivé) et le **DOI « concept »** (qui désigne toutes les versions, présentes et
   futures).

## 8. Placer le DOI dans le mémoire et dans le dépôt

Le DOI n'existe qu'après la publication ; il faut donc le placer ensuite.

1. **Badge dans le `README`** : sur la page Zenodo de l'archive, cliquez sur le badge DOI à droite, copiez le code
   **Markdown**, et collez-le sous le titre du fichier `README.md`.
2. **`CITATION.cff`** : ajoutez une ligne `doi: "10.5281/zenodo.XXXXXXX"` avec le DOI **concept**.
3. **Annexe A du mémoire** (`memoire/body.tex`, section « Accès au code complet ») : ajoutez une phrase du type
   « Une version archivée du dépôt est disponible avec le DOI 10.5281/zenodo.XXXXXXX. » puis recompilez
   (`cd memoire && latexmk -pdf main.tex`).
4. Ordre à respecter si le PDF déposé à l'école doit citer le DOI : publier d'abord (étapes 6 et 7), puis
   modifier le mémoire (point 3), puis déposer le PDF corrigé. L'archive Zenodo contient alors l'ancienne annexe A,
   ce qui est normal : le DOI désigne le code et les résultats. Pour que l'archive contienne aussi la phrase,
   publiez ensuite une nouvelle release (`v1.3.1`) ; elle recevra un nouveau DOI de version, et le DOI « concept »
   restera le même.

## 9. Si quelque chose ne va pas

| Problème | Solution |
|---|---|
| Le dépôt n'apparaît pas dans la liste Zenodo | cliquer sur **Sync now** ; vérifier que vous êtes connecté avec le bon compte GitHub (Kanaicare8) |
| Aucune archive après la release | attendre 5 minutes ; vérifier que l'interrupteur est sur **ON** **avant** la release (une release faite avant l'activation n'est pas archivée : recréez-en une) |
| Le nom de l'auteur est faux | corriger `.zenodo.json` sur GitHub, puis créer une nouvelle release |
| Je veux retirer une version publiée | impossible ; contacter le support depuis le site de Zenodo (rubrique **Support**) en cas de réel problème (donnée personnelle, erreur grave) |
| Le fichier est trop gros | Zenodo accepte de gros fichiers ; l'archive d'une release ne contient que les fichiers suivis par Git, soit une quarantaine de Mo |

## 10. Récapitulatif

1. Choisir et ajouter une licence (étape 3).
2. Se connecter à Zenodo avec le compte GitHub et activer le dépôt (étape 4).
3. Vérifier `.zenodo.json` et `CITATION.cff` (étape 5).
4. Créer la release GitHub sur l'étiquette `v1.3` (étape 6).
5. Récupérer le DOI (étape 7) et le placer dans le `README`, le `CITATION.cff` et l'annexe A (étape 8).
