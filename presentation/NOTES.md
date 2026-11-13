# Notes de l'orateur : présentation de pré-soutenance

Présentation : [`Presoutenance_Icare.pptx`](Presoutenance_Icare.pptx) (aussi en [PDF](Presoutenance_Icare.pdf)), 20 diapositives, 18 à 19 minutes. Les diapositives portent peu de texte : les mots sont ici. Les durées entre parenthèses sont celles de chaque diapositive ; les indications entre crochets sont des indications de jeu, à ne pas lire. Les chiffres sont ceux des tableaux du mémoire (`memoire/tables/`) ; les figures sont les figures du mémoire, re-tracées depuis les résultats déjà calculés, et les deux schémas marqués « illustration » ne portent aucun résultat.

## 1. Couverture (15 s)

Bonjour à tous. Je m'appelle KANA TIODONG Icare Brichel, étudiant en Master Data Science et Intelligence Artificielle à l'ENSPD. Mon mémoire pose une question simple : l'EM classique ou l'EM variationnel ? Il est dirigé par le Professeur NJIONOU SADJANG et le Professeur TAKAM SOH.

[Transition] Voici la question.

## 2. La question (40 s)

Que gagne-t-on, et que perd-on, quand on remplace l'EM classique par l'EM variationnel ? Et surtout : sur quelles preuves ?

La littérature présente volontiers l'EM variationnel comme un progrès. Moi, je ne tiens aucun avantage pour acquis : chacun doit être relié à un théorème, à une expérience, ou à la mention « non testé ».

[Transition] Pour comparer, il faut d'abord dire ce que chacun fait.

## 3. Le problème (1 min)

Le problème est celui des groupes cachés. On a des données, ici en deux dimensions, sans étiquettes. On sait qu'elles viennent de plusieurs groupes, mais on ne sait pas combien, et on ne sait pas à quoi ils ressemblent.

Un modèle de mélange gaussien décrit chaque groupe par un poids, un centre et une forme. Il faut estimer ces paramètres sans jamais voir les étiquettes. C'est ce que font les deux algorithmes.

[Transition] Commençons par l'EM classique.

## 4. L'EM (1 min 10)

L'EM classique alterne deux étapes qui se répondent.

À l'étape E, on calcule, pour chaque point, la probabilité d'appartenir à chaque composante : ce sont les responsabilités.

À l'étape M, on met à jour les paramètres, poids, centres et formes, à partir de ces responsabilités.

On répète jusqu'au point fixe. La vraisemblance ne peut que croître, et on obtient un seul jeu de paramètres : un point.

Mais le nombre de composantes doit être fixé à l'avance, et l'algorithme ne dit rien de l'incertitude de ses réponses.

[Transition] L'EM variationnel change un point essentiel.

## 5. L'EM variationnel (1 min)

L'EM variationnel ne cherche pas un point mais une loi. Les paramètres reçoivent des lois a priori, et le résultat est une loi approchée : on ne dit plus « le centre est ici », on dit « le centre est probablement dans cette zone ».

C'est ce qui lui donne, en principe, une incertitude native, et un mécanisme que nous allons voir : l'élagage des composantes inutiles.

Cette illustration est un schéma, pas un résultat.

[Transition] Les deux algorithmes ont pourtant un socle commun.

## 6. Le socle commun (1 min 10)

Les deux reposent sur la même décomposition : la log-évidence, c'est-à-dire ce que les données disent du modèle, est la somme de deux termes, l'ELBO et une divergence de Kullback-Leibler.

Comme la divergence est toujours positive, l'ELBO minore la log-évidence. Et maximiser l'ELBO revient exactement à réduire cet écart.

L'EM et l'EM variationnel poursuivent donc le même but. Ils ne diffèrent que par la forme de la loi q qu'ils s'autorisent.

[Transition] Voyons ce que cette différence change, sur des données réelles de simulation.

## 7. L'élagage (1 min)

Voici les mêmes données, trois groupes bien séparés, ajustées avec six composantes permises.

À gauche, l'EM classique garde ses six composantes : il coupe un groupe en deux, il en double un autre. À droite, l'EM variationnel en retient trois, exactement les trois groupes.

Il a retiré les composantes inutiles, sans qu'on le lui demande. C'est l'élagage.

[Transition] Les poids le montrent très clairement.

## 8. Les poids (40 s)

Voici les poids des six composantes. Pour l'EM, en sombre, six poids non nuls. Pour l'EM variationnel, en vert, trois poids à un tiers, et trois poids à 0,001 : ces composantes sont éliminées.

Retenez que ce nettoyage dépend de réglages, les priors, et du nombre maximal de composantes permis. Nous y reviendrons.

[Transition] Ce mécanisme a un prix.

## 9. Le prix du champ moyen (1 min 10)

L'EM variationnel approche la loi exacte par une loi plus simple, en minimisant la divergence KL inverse. Cela a deux conséquences qu'il ne faut pas confondre.

À gauche : si la loi exacte a deux modes, l'approximation se concentre sur un seul. C'est l'effet de la divergence.

À droite : même sur une loi à un seul mode, l'approximation est trop étroite, parce qu'elle ignore les corrélations. C'est l'effet de la factorisation.

Conséquence pratique : des intervalles de crédibilité trop étroits. De combien ? La théorie ne le dit pas : je le mesure, c'est l'hypothèse 3. Ce schéma est une illustration.

[Transition] Il reste à situer les méthodes entre elles.

## 10. Trois niveaux d'inférence (50 s)

On peut ranger les méthodes en trois niveaux. Le maximum de vraisemblance, un point : c'est l'EM classique. Le maximum a posteriori, un point régularisé par des priors : c'est le MAP-EM. Et le Bayes complet, une loi sur les paramètres : c'est l'EM variationnel.

Le MAP-EM est mon comparateur intermédiaire : il porte les mêmes priors que le VB, sans la loi sur les paramètres. Il permet d'attribuer un effet aux priors, ou à l'approche variationnelle elle-même.

[Transition] Voyons comment je les compare.

## 11. Le protocole (1 min)

Quatre ingrédients. Des données : des scénarios synthétiques, le jeu Iris, et un cas réel, les prix alimentaires du Cameroun.

Cinq méthodes : l'EM avec le bon K, l'EM avec le K maximal, l'EM avec K choisi par le critère BIC, le MAP-EM et le VB.

Les mêmes règles : même critère d'arrêt, mêmes relances, mêmes graines, fixés par un calibrage écrit à l'avance.

Et des tests déclarés avant les calculs : équivalence, Wilcoxon, correction de Holm.

[Transition] Ces tests portent sur cinq hypothèses.

## 12. Cinq hypothèses (1 min 10)

Cinq hypothèses. RH1 : pas de supériorité générale. RH2 : le choix de K se déplace, il dépend des priors du VB au moins autant que de l'EM. RH3 : l'incertitude du VB est approchée, ses intervalles couvrent moins que leur niveau annoncé. RH4 : à petit effectif, le VB dégénère moins, et c'est l'effet des priors. RH5 : le coût est plus élevé à l'itération.

Un point de méthode important : ne pas voir de différence ne prouve pas l'équivalence. Quand l'hypothèse prédit une absence de différence, j'utilise un vrai test d'équivalence.

[Transition] Voici les résultats.

## 13. Bilan (50 s)

63 décisions déclarées. 31 sont conformes à l'hypothèse, 4 contraires, 22 non tranchées, et 6 sont des différences sans sens prédit.

Les 4 contraires portent toutes sur la couverture du bootstrap de l'EM, que je supposais proche du niveau annoncé : elle ne l'est pas. Et sur les 22 non tranchées, 9 sont des équivalences non démontrées.

Le bilan est donc nuancé : aucune supériorité générale.

[Transition] Regardons d'abord les scénarios.

## 14. Scénarios (1 min 10)

Premier résultat, hypothèse 1. Quand les groupes sont bien séparés, ou contaminés par des aberrations, le VB et l'EM avec BIC sont équivalents.

Mais quand les groupes se chevauchent, ou que la dimension augmente, le VB fait mieux : jusqu'à 0,79 d'ARI de plus en dimension 20. L'ARI mesure l'accord entre les groupes retrouvés et les vrais groupes.

À petit effectif, le VB produit moins d'ajustements dégénérés que l'EM de même capacité.

Explication probable, que je n'ai pas testée : la pénalité du BIC fait retenir trop peu de composantes dans ces situations.

[Transition] Mais ce gain dépend des réglages.

## 15. Les priors (1 min)

C'est l'hypothèse 2. Sur ce scénario, le nombre de composantes retenues par le VB dépend de la concentration du prior de Dirichlet. Tant qu'elle reste faible, le VB retrouve les trois groupes. Au-delà d'un seuil, il cesse d'élaguer.

Sur les prix, la variance du nombre de composantes du VB selon les priors dépasse celle de l'EM selon ses propres choix, d'un écart de 3,2.

Le VB n'a donc pas supprimé le choix de K : il l'a déplacé vers ses réglages. Ce scénario est descriptif.

[Transition] Passons à l'incertitude.

## 16. Incertitude (1 min)

Hypothèse 3. Sur un jeu où la vérité est connue, on mesure la fréquence à laquelle les intervalles à 90 % contiennent la vraie valeur. Pour le VB : 22 % pour les poids, 64 % pour les moyennes. Pour le bootstrap de l'EM avec BIC : 44 % et 78 %.

Aucun n'atteint 90 %, et le VB est le plus loin. C'est ce que prédit la théorie du champ moyen. Le bootstrap lui-même reste en dessous, même quand K est connu.

Conclusion : il ne faut lire aucun de ces intervalles comme une incertitude calibrée.

[Transition] Et le coût ?

## 17. Coût (50 s)

Hypothèse 5. Une itération du VB coûte de 1,1 à 2,2 fois une itération de l'EM.

Mais pour obtenir un modèle final, il faut choisir K. Le pipeline de l'EM avec BIC ajuste le modèle pour toutes les valeurs de K : il coûte de 2,6 à 5 fois le temps d'un seul VB, dès 60 observations.

Le VB est donc plus cher à l'itération, mais moins cher au total. C'est le temps total qui compte.

[Transition] Un mot de l'application.

## 18. Application (1 min)

Pour voir ces méthodes à l'œuvre, je les ai appliquées à un problème réel : les prix alimentaires du Cameroun, données publiques du Programme alimentaire mondial. Chaque marché reçoit, chaque mois, une probabilité d'être en régime de tension.

Voici deux mois documentés dans l'Extrême-Nord. En août 2023, le maïs a pris 24 % en un mois : des marchés passent en alerte, Mara, Gazawa, et Koza et Zamay pour l'EM seulement. En avril 2026, le maïs baisse : les marchés restent presque tous calmes, avec un marché à la limite pour l'EM.

Ici encore, aucune méthode ne prévoit mieux qu'une simple loi gaussienne.

[Transition] Que retenir pour choisir ?

## 19. Choisir (1 min 10)

Voici le guide qui en résulte, avec son niveau de preuve. Si K est connu : l'EM ou le VB conviennent. Si les groupes se chevauchent : le VB. Si l'on a besoin d'une incertitude : le bootstrap de l'EM avec BIC, plutôt que les intervalles du VB, en vérifiant leur couverture. À petit effectif : des priors, avec le VB ou le MAP-EM.

Et dans tous les cas, comparez d'abord à une simple gaussienne : sur les prix, aucun mélange ne la bat.

Limites : des choix de construction des variables posés sans alternative testée, un seuil d'alerte conventionnel, et des régimes appris sans vérité terrain.

[Transition] Pour finir, en une phrase.

## 20. Fin (30 s)

Le VB ne bat pas l'EM : il déplace la difficulté, du choix de K vers le choix des priors. Il régularise comme le ferait un MAP-EM, et ses intervalles ne se lisent pas comme calibrés.

Je vous remercie de votre attention, et je suis prêt à répondre à vos questions.

