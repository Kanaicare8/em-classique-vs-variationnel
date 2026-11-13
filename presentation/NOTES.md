# Notes de l'orateur : présentation de pré-soutenance

Présentation : [`Presoutenance_Icare_v1.pptx`](Presoutenance_Icare_v1.pptx), 26 diapositives, 20 minutes environ (les durées entre parenthèses sont celles de chaque diapositive). Les indications entre crochets sont des indications de jeu : elles ne se lisent pas. Les chiffres des diapositives 20 à 26 sont repris des tableaux du mémoire (`tables/`).

## 1. Page de garde (15 s)

Bonjour à tous. Je m'appelle KANA TIODONG Icare Brichel, étudiant en Master Data Science et Intelligence Artificielle à l'ENSPD.

Je vous présente mon mémoire : « Comparaison entre l'algorithme EM classique et l'EM variationnel : avantages, inconvénients et applications », sous le co-encadrement du Professeur NJIONOU SADJANG et du Professeur TAKAM SOH.

[Transition] Je pars d'un problème très concret.

## 2. Contexte (1 min)

Des relevés de prix ne disent pas dans quel régime se trouve un marché : calme ou tension. Un modèle de mélange peut apprendre ces régimes à partir des données, à condition de savoir quel algorithme d'estimation choisir, et ce que valent ses réponses.

L'enjeu est réel : plus de 2,8 millions de personnes en insécurité alimentaire aiguë au Cameroun entre juin et août 2026, selon le Cadre Harmonisé. Les prix y connaissent des chocs brusques dans les deux sens : le maïs a pris 24 % en un mois dans l'Extrême-Nord en août 2023, et il était 40 à 50 % moins cher qu'un an plus tôt à Kousseri, Mokolo et Mora en avril 2026.

Aujourd'hui, le PAM classe ces prix par des seuils fixés à l'avance, sans régimes appris ni incertitude sur l'alerte.

[Transition] Apprendre ces régimes suppose de choisir un algorithme. C'est là que se pose ma question.

## 3. Problématique (50 s)

L'EM classique, de Dempster, Laird et Rubin, donne une estimation ponctuelle ; il exige de fixer le nombre de composantes K à l'avance et peut dégénérer.

L'EM variationnel bayésien place des lois a priori sur les paramètres, approche leur loi a posteriori par un champ moyen, et élimine de lui-même les composantes superflues.

Ma question : que gagne-t-on, et que perd-on, en passant de l'un à l'autre, et sur quelles preuves ? Je ne tiens aucun avantage pour acquis : chacun est relié à un théorème, une expérience, ou la mention « non testé ».

[Transition] Cette posture conduit à une thèse.

## 4. Thèse et hypothèses (1 min 10)

Ma thèse : le VB ne bat pas l'EM, il déplace la difficulté. Il reporte la sélection de K sur ses hyperparamètres et sur Kmax, et apporte une incertitude approchée, au prix d'un coût et d'une sensibilité aux priors.

Elle se décompose en cinq hypothèses. RH1 : pas de supériorité générale. RH2 : le K du VB dépend de ses priors au moins autant que celui de l'EM de ses choix. RH3 : les intervalles du VB couvrent moins que leur niveau nominal. RH4 : à petit effectif, le VB dégénère moins, et c'est l'effet des priors. RH5 : un ajustement VB coûte plus qu'un ajustement EM, mais moins que le balayage complet de K par EM-BIC.

[Transition] D'où mes objectifs.

## 5. Objectifs (40 s)

L'objectif général est de mesurer, sous un protocole commun et avec des tests déclarés à l'avance, ce que l'on gagne et ce que l'on perd en remplaçant l'EM par l'EM variationnel.

Il se décline en cinq objectifs : les fondements communs, le choix de K, l'incertitude et la robustesse, le coût, et l'application aux prix du Cameroun, avec un guide de choix.

[Transition] Première partie : la revue de la littérature.

## 6. Cadre conceptuel (45 s)

Les deux algorithmes reposent sur la même décomposition : la log-évidence est la somme de l'ELBO et d'une divergence de Kullback-Leibler. L'ELBO minore donc la log-évidence, et la maximiser rapproche l'approximation q de la loi a posteriori.

Variables latentes, mélange gaussien, cadre bayésien : ce sont les trois notions du mémoire. L'EM et l'EM variationnel optimisent la même borne ; ils ne diffèrent que par la famille de q.

[Transition] D'abord l'EM classique.

## 7. EM classique (45 s)

L'EM classique alterne deux étapes : l'étape E calcule les responsabilités, la probabilité que chaque point appartienne à chaque composante ; l'étape M met à jour poids, moyennes et covariances.

La vraisemblance croît à chaque itération, mais la convergence est lente quand K est surestimé. Ses limites : K fixé à l'avance, pas d'incertitude native sans bootstrap, et des solutions dégénérées possibles.

[Transition] L'EM variationnel répond à ces limites, à sa manière.

## 8. EM variationnel et élagage (50 s)

L'EM variationnel approche la loi a posteriori par un produit, c'est le champ moyen.

L'élagage vient du prior de Dirichlet : une composante qui capte peu de points voit l'espérance du logarithme de son poids chuter ; ses responsabilités s'effondrent, et elle ne revient presque plus.

Rousseau et Mengersen garantissent cet élagage sous un seuil d sur 2, mais pour la loi a posteriori exacte : son transfert au champ moyen est une hypothèse que je teste.

[Transition] Ce champ moyen a un prix.

## 9. KL inverse (40 s)

Minimiser la KL inverse a deux conséquences à ne pas confondre. Sur une loi multimodale, q se concentre sur un seul mode : c'est la divergence. Même sur une loi unimodale, la variance de q est trop petite : c'est la factorisation.

D'où des intervalles trop étroits. La théorie ne dit pas de combien : je le mesure, c'est RH3.

[Transition] Pour comparer proprement, trois niveaux d'inférence.

## 10. Trois niveaux d'inférence (35 s)

Maximum de vraisemblance : un point, l'EM classique. Maximum a posteriori : un point régularisé, le MAP-EM. Bayes complet : une distribution, l'EM variationnel.

Le MAP-EM porte les priors du VB sans loi sur les paramètres : il isole l'effet des priors du reste de l'approche variationnelle.

[Transition] Ce que dit la littérature.

## 11. État de l'art (45 s)

L'EM avec BIC choisit K par balayage et n'a d'incertitude que par bootstrap ; le VB choisit K de l'intérieur par élagage et donne une incertitude native mais trop étroite.

J'en retiens quatre constats : le choix de K est déplacé, pas supprimé ; l'ELBO ne se compare pas au BIC ; l'incertitude oppose une crédibilité trop étroite à un bootstrap coûteux ; et seul le temps total départage les coûts.

[Transition] Ce qui manque à la littérature.

## 12. Limites de la littérature (40 s)

Cinq manques, cinq réponses. L'élagage n'est garanti que pour la loi exacte : RH2. La couverture du VB n'est pas mesurée à K inconnu : RH3. Les avantages pratiques du VB ne sont pas mesurés contre EM-BIC à coût total égal : RH1, RH4, RH5. Ne pas voir de différence ne prouve pas l'équivalence : des tests d'équivalence. Et aucune application aux prix du Cameroun : le cas pratique.

[Transition] Deuxième partie : la méthodologie.

## 13. Type et cadre de recherche (25 s)

La recherche est explicative, expérimentale, appliquée et quantitative : chaque hypothèse a sa métrique et un test déclaré avant les calculs. Les unités sont des jeux de données, aucune population humaine, et seuls les plans répliqués tranchent une hypothèse.

[Transition] Sur quelles données ?

## 14. Sources de données (35 s)

Cinq sources publiques : un jeu synthétique de référence, les scénarios S1 à S10, Iris, les prix du PAM au Cameroun, 77 268 relevés sur 83 marchés dont j'utilise le maïs, le riz importé et le niébé, et un corpus de texte pour comparer pLSA et LDA. La carte montre les marchés, surtout dans l'Extrême-Nord.

[Transition] Les scénarios isolent chacun un facteur.

## 15. Scénarios (35 s)

Chaque scénario fait varier un seul facteur : chevauchement, poids déséquilibrés, K sous-estimé, queues épaisses, dimension, petit effectif, aberrations. S8 à S10 sont descriptifs. Le nombre de réplications est fixé par un calcul de puissance.

[Transition] À côté, le cas pratique pose la question réelle.

## 16. Cas pratique (50 s)

Un mélange gaussien peut-il apprendre des régimes de prix sans seuils fixés à l'avance, et donner à chaque marché et chaque mois une probabilité de tension avec son incertitude ?

La variable est l'écart du log-prix à son niveau des douze mois précédents. 562 observations d'apprentissage jusqu'en décembre 2023, 493 de test ensuite. Le régime de tension est la composante aux écarts moyens les plus élevés, et une observation est en alerte quand sa probabilité dépasse 0,5.

[Transition] Il reste à comparer à armes égales.

## 17. Protocole de comparaison (35 s)

Cinq bras : l'EM au K de référence, l'EM à Kmax, l'EM-BIC et l'EM-ICL, le MAP-EM, et le VB. Mêmes données, même critère d'arrêt, mêmes relances, fixés par un calibrage écrit à l'avance. Les métriques : ARI, vraisemblance hors échantillon, erreur sur K, dégénérescence, couverture, temps total.

[Transition] Et des tests déclarés pour trancher.

## 18. Tests et règle de décision (40 s)

Pour une absence de différence, un test d'équivalence, le TOST, à marges fixées par l'importance pratique ; pour une différence, un Wilcoxon exact. Holm dans chaque famille, Diebold et Mariano pour la prévision.

Chaque test conclut conforme, contraire ou non tranché, et une équivalence non démontrée n'est pas une différence démontrée.

[Transition] Avant les résultats, les limites que je déclare.

## 19. Limites et transition (35 s)

Le jeu semi-synthétique est tiré du modèle EM-BIC, ce qui peut l'avantager ; les mélanges restent simples et les séries de prix courtes ; les observations ne sont pas indépendantes. Et les écarts au protocole sont tous déclarés, dont un défaut du bootstrap des prix corrigé après les résultats.

[Transition] Place aux résultats, dans l'ordre des hypothèses.

## 20. Bilan des hypothèses (50 s)

Voici le bilan des 63 décisions déclarées. 31 sont conformes aux hypothèses, 4 contraires, 22 non tranchées et 6 sont des différences sans sens prédit.

Les 4 contraires portent toutes sur le bootstrap de l'EM, que je supposais proche de 90 % : il ne l'est pas. Et sur les 22 non tranchées, 9 sont des équivalences non démontrées : ne pas conclure, ce n'est pas conclure à l'égalité.

La thèse tient : aucune supériorité générale.

[Transition] Voyons d'où viennent ces verdicts, d'abord sur les scénarios.

## 21. Scénarios (55 s)

Quand les groupes sont bien séparés, ou contaminés par des aberrations, le VB et l'EM-BIC sont équivalents à la marge de 0,05 d'ARI.

Quand les groupes se chevauchent ou que la dimension croît, le VB fait mieux : 0,17 et 0,28 d'ARI en plus pour des groupes séparés de 2 et 3 écarts-types, 0,28 et 0,79 en dimension 10 et 20.

À petit effectif, le VB dégénère moins que l'EM de même capacité : 76 points de moins à 30 observations.

Explication probable, non testée : la pénalité du BIC fait retenir trop peu de composantes dans ces situations.

[Transition] Sur les prix réels, le tableau change.

## 22. Prix : régimes et prévision (50 s)

Sur les prix, l'EM-BIC retient deux régimes, le VB à priors empiriques quatre, et le VB calibré huit.

Ce nombre dépend des priors : il varie bien plus entre priors plausibles que celui de l'EM entre ses propres choix, c'est RH2.

La vraisemblance de test du VB est inférieure de 0,16 nat par observation : l'équivalence n'est pas démontrée. Et sur 32 mois de test, aucun mélange ne prévoit mieux qu'une simple loi gaussienne.

[Transition] Que donne l'alerte elle-même ?

## 23. Alerte (55 s)

Voici l'Extrême-Nord aux deux mois documentés. En août 2023, la hausse du maïs : l'EM-BIC met Mara, Koza, Zamay et Gazawa en alerte, le VB seulement Mara et Gazawa. En avril 2026, la baisse : aucune alerte, ce qui est attendu.

Les deux méthodes classent de la même façon 84 % des observations. Leur fourchette à 90 % est étroite, et contient le seuil de 0,5 pour 6 à 11 % des observations.

Ce seuil est une convention, la règle de Bayes à coûts égaux : en pratique, il revient aux organismes de sécurité alimentaire.

[Transition] Mais que vaut cette fourchette ?

## 24. Incertitude (50 s)

C'est RH3. Sur un jeu où la vérité est connue, les intervalles du VB couvrent la valeur vraie 22 % du temps pour les poids et 64 % pour les moyennes, pour un niveau annoncé de 90 %.

Le bootstrap de l'EM-BIC fait mieux, 44 et 78 %, mais reste lui aussi sous 90 %, même quand K est connu.

C'est ce que prédit la théorie du champ moyen. Conclusion : aucun de ces intervalles ne se lit comme une incertitude calibrée.

[Transition] Reste la régularisation et le coût.

## 25. Régularisation et coût (45 s)

RH4 : sur les prix, le MAP-EM, qui porte les priors du VB sans loi sur les paramètres, réduit la dégénérescence autant ou plus que le VB. L'effet régularisant tient donc aux priors, pas à l'inférence variationnelle.

RH5 : une itération du VB coûte 1,1 à 2,2 fois une itération de l'EM, mais le pipeline EM-BIC, qui balaie toutes les valeurs de K, coûte 2,6 à 5 fois le temps d'un VB.

[Transition] J'en tire une conclusion pratique.

## 26. Conclusion (1 min)

Le VB ne bat pas l'EM : il déplace la sélection de K vers ses hyperparamètres, régularise par ses priors, comme le ferait un MAP-EM, et donne des intervalles qu'il ne faut pas lire comme calibrés.

D'où un guide : EM ou VB quand K est connu ; le VB quand les groupes se chevauchent ; le bootstrap quand on a besoin d'une incertitude ; des priors à petit effectif ; et toujours une gaussienne simple comme référence pour prévoir.

Limites : des choix de variables posés sans test, un seuil conventionnel, des régimes sans vérité terrain. J'ai prolongé le cas pratique par un outil de bulletin mensuel qui reprend le modèle à l'identique.

Je vous remercie de votre attention, et je suis prêt à répondre à vos questions.

