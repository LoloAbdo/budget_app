# Journal des modifications

Toutes les modifications notables de Budget Manager sont documentées ici.

Le format s'appuie sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet respecte le [versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

## [2.11.0] - 2026-07-11

### Ajouté
- **Aperçus des dépenses sur le tableau de bord.** Une nouvelle carte d'aperçus
  explique pourquoi vos chiffres ont bougé ce mois-ci — en signalant les
  catégories nettement au-dessus ou en dessous de votre propre moyenne récente,
  et si vous dépensez plus ou moins que le mois dernier, pour que les totaux
  s'accompagnent d'un contexte plutôt que d'un simple montant.
- **Détecteur d'abonnements.** Un nouveau panneau **Abonnements** analyse votre
  historique de transactions pour repérer les frais qui reviennent à un rythme
  régulier et pour un montant stable (Netflix, gym, forfait téléphonique…) et
  les liste avec un coût mensuel et annuel estimé — pour repérer facilement les
  dépenses récurrentes oubliées ou qui augmentent.

## [2.10.0] - 2026-07-09

### Corrigé
- **Les boutons s'adaptent maintenant à leur libellé dans toutes les langues.**
  Les boutons se dimensionnent selon leur texte plutôt qu'à une largeur fixe :
  les libellés traduits plus longs (par exemple en français) s'affichent en
  entier au lieu d'être tronqués par des points de suspension.

### Ajouté
- **Les tableaux retiennent la largeur de vos colonnes.** Redimensionnez une
  colonne dans les tableaux Transactions, Comptes, Récurrences, Journal
  d'activité ou Tableau de bord et vos largeurs sont enregistrées par
  utilisateur — elles restent en place après les rafraîchissements, les
  changements d'onglet et les redémarrages.

## [2.9.0] - 2026-07-09

### Corrigé
- **Les transactions récurrentes sont maintenant enregistrées sans redémarrer
  l'application.** Lorsqu'une récurrence arrive à échéance alors que
  l'application reste ouverte, ouvrir l'onglet **Transactions** l'enregistre
  aussitôt et met à jour vos soldes, budgets et rapports — sans recharger
  l'application.
- **Les alertes de budget ne masquent plus un budget dont le report a épuisé
  la marge.** Lorsqu'un dépassement important est reporté et ne laisse plus
  aucune marge à une catégorie, celle-ci s'affiche désormais correctement comme
  dépassée au lieu d'être ignorée.

## [2.8.0] - 2026-07-08

### Ajouté
- **Plan de remboursement des dettes.** Un nouveau panneau **Dettes** vous
  permet de lister ce que vous devez (solde, taux d'intérêt et paiement minimum)
  et construit un plan de remboursement. Choisissez la stratégie **Avalanche**
  (attaquer d'abord le taux d'intérêt le plus élevé — la moins chère au total)
  ou **Boule de neige** (rembourser d'abord le plus petit solde — la victoire la
  plus rapide), ajoutez un paiement mensuel supplémentaire facultatif, et voyez
  votre date de libération, le total des intérêts, et combien de temps et
  d'intérêts vous économisez par rapport aux paiements minimums seuls. Chaque
  dette indique le mois où elle est remboursée. Si vos paiements ne suivent pas
  les intérêts, le plan le signale au lieu de deviner.
- **Report de budget.** Tout budget peut désormais reporter son montant
  inutilisé au mois suivant — cochez **Reporter le montant inutilisé au mois
  suivant** lors de l'ajout ou de la modification d'un budget. Le dépassement
  est aussi reporté (comme moins de marge le mois suivant). Le report
  s'accumule sur les mois consécutifs et est intégré à la barre de progression
  et aux alertes du budget.

## [2.7.0] - 2026-07-07

### Ajouté
- **« Se souvenir de moi » sur l'écran de connexion.** Cochez la case et votre
  courriel et votre mot de passe sont enregistrés sur cet ordinateur : au
  prochain lancement, les champs sont pré-remplis — il ne reste qu'à cliquer sur
  Se connecter. Le mot de passe est chiffré au repos avec Windows DPAPI (lié à
  votre compte Windows, jamais stocké en clair et illisible par d'autres
  utilisateurs ou sur une autre machine) ; si le chiffrement n'est pas
  disponible, seul le courriel est conservé. Décocher la case puis se connecter
  efface les identifiants enregistrés, et **Paramètres ▸ Sécurité ▸ Connexion
  enregistrée** permet de les oublier à tout moment.

### Modifié
- **Journal d'activité lisible.** Le journal d'activité s'affiche désormais en
  langage clair plutôt qu'en données brutes : horodatages conviviaux
  (« Jul 7, 2026, 15:59 »), noms d'éléments simples (« Profil », « Élément
  récurrent ») et un résumé lisible de chaque changement
  (« Épicerie · Montant : -52.40 · Date : 2026-07-07 ») à la place de
  l'instantané JSON. Les identifiants internes de la base sont masqués (la
  colonne ID distincte a disparu). Le détail complet reste disponible via
  **Exporter**.
- **Nouveautés localisées.** Le journal des modifications dans Paramètres ▸ À
  propos suit désormais la langue de l'application, affichant une traduction
  française complète lorsque l'application est en français et basculant en direct
  quand vous changez de langue.

## [2.6.0] - 2026-07-07

### Ajouté
- **Nouveautés dans À propos.** Paramètres ▸ À propos affiche maintenant le
  journal des modifications complet dans un panneau défilant, afin qu'après une
  mise à jour vous voyiez exactement ce que chaque version a ajouté. Rendu à
  partir du fichier `CHANGELOG.md` fourni (une source unique de vérité, livrée
  avec les versions portable et installée).

## [2.5.0] - 2026-07-05

### Ajouté
- **Quatre nouveaux thèmes.** **Nord** (bleu-gris apaisant avec un accent
  givré), **Dracula** (le classique violet-et-rose sur ardoise), **Contraste
  élevé** (noir pur, bordures marquées, accent bleu vif — une option
  d'accessibilité) et **Sakura** (un thème clair fleur de cerisier tout en
  douceur avec un accent rosé), portant le registre à onze thèmes plus Auto.

## [2.4.0] - 2026-07-05

### Ajouté
- **Règles de catégorisation automatique.** Paramètres ▸ Règles associe des
  motifs de description à des catégories (« NETFLIX » → Abonnements, sous-chaîne
  insensible à la casse ; le motif le plus long l'emporte). Les règles
  s'appliquent en direct pendant la saisie d'une nouvelle transaction (sans
  jamais remplacer une catégorie choisie manuellement) et aux imports CSV/Excel
  pour les lignes sans catégorie.
- **Recherche globale.** Ctrl+F ouvre une boîte de recherche qui trouve une
  description, des notes ou un montant exact (insensible au signe) dans tous les
  comptes et toutes les dates. Un double-clic ou Entrée saute au panneau
  Transactions avec la requête appliquée et les filtres élargis.
- **Thème automatique.** Un nouveau thème « Auto (suivre Windows) » suit le
  réglage clair/sombre du système et se réactualise en direct quand Windows
  change de mode. Disponible dans Paramètres ▸ Apparence et via `--theme auto`.

### Sécurité
- **Mises à jour vérifiées.** Chaque version publie désormais `SHA256SUMS.txt`,
  et le programme de mise à jour intégré vérifie la taille et le SHA-256 de
  l'installateur avant de le lancer — un téléchargement corrompu ou altéré est
  supprimé et signalé au lieu d'être exécuté. Les versions sans sommes de
  contrôle (antérieures à 2.4.0) se mettent à jour avec la seule vérification de
  taille.

### Interne
- Les tests hachent les mots de passe bcrypt au coût minimal (4 tours), réduisant
  la suite d'authentification de ~28 s à ~1 s sans changer ce qui est testé.

## [2.3.0] - 2026-07-04

### Ajouté
- **Codes de récupération de mot de passe.** Paramètres ▸ Sécurité peut
  maintenant générer 8 codes de récupération à usage unique (affichés une seule
  fois, avec Copier / Enregistrer dans un fichier). Un nouveau flux **Mot de
  passe oublié ?** sur l'écran de connexion accepte votre courriel, un code
  inutilisé et un nouveau mot de passe. Les codes sont stockés uniquement sous
  forme de hachages bcrypt, chacun ne fonctionne qu'une fois, en régénérer
  remplace l'ancien lot, et le flux de réinitialisation renvoie la même erreur
  générique pour un courriel erroné ou un code erroné afin que les comptes ne
  puissent pas être sondés. Entièrement hors ligne — rien n'est envoyé nulle
  part.

## [2.2.0] - 2026-07-04

### Ajouté
- **Icône de l'application.** Budget Manager a enfin sa propre icône — un carré
  arrondi à dégradé violet avec un glyphe dollar (généré par
  `scripts/make_icon.py`, versionné sous `assets/icon.ico`). Elle apparaît dans
  la barre de titre de la fenêtre, la barre des tâches Windows (avec son propre
  AppUserModelID), l'exe lui-même, l'assistant d'installation et les raccourcis
  du menu Démarrer/bureau.
- **La barre de titre native suit le thème.** Sous Windows, les thèmes sombres
  (Dark, Midnight, Ocean, Forest, Sunset) obtiennent désormais une barre de
  titre sombre au lieu de la blanche par défaut — sur chaque fenêtre, y compris
  les boîtes de dialogue et de message.
- **Surbrillance au survol des tableaux.** Les cellules des tableaux se mettent
  subtilement en surbrillance sous le curseur dans tous les thèmes (la sélection
  reste prioritaire).
- **Pastilles de couleur de catégorie.** Le tableau des Transactions et les
  Transactions récentes du tableau de bord marquent maintenant chaque catégorie
  d'une petite pastille de sa couleur, étendant le système de couleurs de
  catégorie au-delà des graphiques.
- **Peaufinage des graphiques.** Tous les graphiques utilisent maintenant la
  police d'interface de l'application (Segoe UI) au lieu de celle par défaut de
  matplotlib, les axes monétaires affichent des graduations compactes (`1.5k`,
  `2.5M`) au lieu de nombres bruts, et l'anneau des dépenses étiquette chaque
  part avec son pourcentage (les parts sous 4 % restent sans étiquette pour
  éviter l'encombrement).
- **Écarts au tableau de bord.** Les cartes de synthèse montrent maintenant
  l'évolution de chaque chiffre par rapport au mois dernier — « ▲ 12 % vs mois
  dernier » en vert/rouge (des dépenses en hausse sont lues en rouge, des
  revenus en hausse en vert ; le taux d'épargne affiche l'écart en points). Les
  cartes restent sobres quand il n'y a pas de mois précédent à comparer.
- **De vrais états vides.** Les panneaux vides affichent maintenant une icône,
  un message et — sur Comptes, Transactions et Récurrents — un bouton d'action
  qui ouvre la boîte d'ajout correspondante. Le bouton se masque quand les
  lignes sont simplement filtrées.
- **Notifications éphémères (toasts).** Les actions se confirment désormais par
  une petite pastille qui apparaît en fondu en bas de la fenêtre puis
  disparaît (« Transaction ajoutée », « Virement créé », « Compte supprimé »,
  éléments récurrents publiés au lancement, « Taux de change mis à jour » après
  une actualisation FX en arrière-plan) — remplaçant les messages faciles à
  manquer de la barre d'état.
- **Police Inter incluse.** L'application livre maintenant la police Inter (sous
  licence OFL, fichier de licence inclus) et l'utilise partout — interface et
  graphiques — pour un rendu identique sur chaque machine. Les chiffres
  utilisent des chiffres tabulaires, si bien que les montants s'alignent en
  colonnes parfaites. Repli sur Segoe UI si les fichiers fournis sont manquants.
- **Réglage de taille de police.** Paramètres ▸ Apparence gagne un sélecteur de
  taille de police (90 % / 100 % / 110 % / 125 %) qui s'applique immédiatement à
  toute l'application et est enregistré par utilisateur (`users.font_scale`,
  migration v1.0.10).
- **Couleur d'accent personnalisée.** Choisissez n'importe quelle couleur
  d'accent (Paramètres ▸ Apparence) et chaque thème se recolore autour d'elle —
  boutons, surbrillance de navigation, sélections, anneaux de focus et accents
  des graphiques dérivent tous de la seule couleur choisie ; Réinitialiser
  revient à l'accent propre du thème. Enregistré par utilisateur
  (`users.accent`).

## [2.1.0] - 2026-07-04

### Ajouté
- **Cinq nouveaux thèmes d'interface.** En plus de Dark et Light : **Midnight**
  (noir pur OLED), **Ocean** (bleu marine profond, accent cyan), **Forest**
  (vert foncé), **Sunset** (prune chaud, accent rose→ambre) et **Sand** (thème
  clair type papier chaud, accent bronze). Choisissez-en un dans Paramètres ▸
  Apparence ; les graphiques se recolorent pour correspondre, le choix est
  enregistré par utilisateur, et `--theme <nom>` le remplace toujours pour une
  seule exécution. Le moteur de thèmes est désormais basé sur un registre
  (`views/theme.py THEMES`) — un nouveau thème est un seul dictionnaire de
  palette, et chaque palette est vérifiée pour sa complétude par les tests.

## [2.0.0] - 2026-07-02

### Ajouté
- **Comptes multidevises.** Chaque compte a désormais sa propre devise, choisie
  à la création du compte (et modifiable ensuite — la modification ré-étiquette ;
  les montants ne sont jamais convertis en silence). Les soldes et transactions
  s'affichent dans la devise du compte partout dans l'application.
- **Conversion en devise principale partout.** Les totaux du tableau de bord, la
  tendance de valeur nette, les graphiques mensuels revenus/dépenses, les
  rapports, les dépenses budgétaires, les résumés d'épargne et la prévision de
  trésorerie convertissent tous les montants en devise étrangère vers votre
  devise principale, afin que les chiffres de l'application restent pertinents.
  Les totaux mixtes sont marqués d'un ≈.
- **Cache des taux de change avec repli hors ligne.** Les taux proviennent des
  mêmes fournisseurs sans clé que le panneau Marchés (Stooq, repli Yahoo) et
  sont mis en cache dans une nouvelle table `fx_rates` — dans les deux sens.
  L'application actualise discrètement les taux périmés (>24 h) en arrière-plan
  au lancement et continue de fonctionner hors ligne avec le dernier taux
  connu (ou 1:1 si un taux n'a jamais été récupéré). Un nouvel onglet
  **Paramètres ▸ Devise** montre les taux en cache et propose une actualisation
  manuelle.
- **Virements entre devises.** Un virement entre comptes de devises différentes
  demande le **Montant reçu**, pré-estimé à partir du taux en cache et modifiable
  pour correspondre à ce que la banque a réellement crédité. Chaque volet
  conserve sa propre devise ; supprimer le virement annule correctement les deux.
  Les virements récurrents entre devises se convertissent automatiquement au taux
  en cache le jour de la publication.
- Les exports de transactions (CSV/Excel) gagnent une colonne `currency` ; le
  rapport PDF étiquette chaque transaction avec la devise de son compte.

### Modifié
- **Pourquoi 2.0.0:** le schéma de la base change de façon notable (colonne
  `currency` par compte — migration v1.0.9 — plus la nouvelle table `fx_rates`),
  et chaque chiffre agrégé de l'application est désormais défini en fonction de
  la devise principale. Les bases existantes se mettent à jour automatiquement et
  sans perte : les comptes héritent de la devise principale de leur
  propriétaire, si bien que tous les chiffres restent exactement identiques
  jusqu'à ce que vous optiez pour un compte en devise étrangère.

## [1.11.0] - 2026-07-01

### Ajouté
- **Mise à jour en un clic (version installée).** Quand une version plus récente
  est trouvée, Paramètres ▸ À propos propose désormais **⤓ Mettre à jour
  maintenant** : cela télécharge l'installateur avec une barre de progression,
  l'exécute silencieusement et ferme l'application pour qu'elle se mette à jour
  sur place et se relance sur la nouvelle version — sans
  téléchargement/réinstallation manuels. Les données utilisateur dans
  `%APPDATA%\BudgetManager` restent intactes. Les exécutions depuis les sources
  et l'exe portable en un seul fichier conservent le lien de téléchargement
  simple (la mise à jour automatique est limitée à la version installée, qui peut
  se remplacer sans risque). L'étape de relance de l'installateur s'exécute
  maintenant lors des installations silencieuses (`skipifsilent` retiré de
  `installer.iss`).

## [1.10.0] - 2026-07-01

### Ajouté
- **Visionneuse du journal d'activité intégrée.** La piste d'audit (auparavant
  réservée à l'export) a désormais son propre panneau **Activité** : un tableau
  en lecture seule et filtrable de chaque création/modification/suppression, avec
  des filtres d'action et d'élément, une recherche en texte libre et le même
  export CSV que dans Paramètres.
- **« Factures à venir » sur le tableau de bord.** Une carte liste les éléments
  récurrents actifs dus dans les 7 prochains jours (les éléments en retard
  restent visibles), de sorte que l'échéancier sert de rappel sans ouvrir le
  panneau Récurrents.
- **Suspendre / reprendre les règles récurrentes.** Une règle peut être
  suspendue (nouvel indicateur `is_active`, migration v1.0.8) pour cesser de
  publier — et être exclue de la prévision et des factures à venir — sans la
  supprimer ni perdre ses réglages. Le tableau des Récurrents affiche une colonne
  **Statut** ; un bouton Suspendre/Reprendre bascule l'état.
- **Copier les budgets du mois dernier.** Un bouton **Copier le mois dernier**
  sur le panneau Budgets copie les lignes de budget du mois précédent dans le
  mois courant, en ignorant les catégories déjà budgétées.
- **Dupliquer une transaction.** Un bouton **Dupliquer** ouvre la boîte d'ajout
  pré-remplie à partir de la transaction sélectionnée (virements exclus).

## [1.9.0] - 2026-06-30

### Ajouté
- **Date de fin pour les transactions récurrentes.** Un élément récurrent
  (transaction ou virement) peut maintenant avoir une date de fin facultative.
  Dans la boîte Ajouter/Modifier, cochez **Se termine le** et choisissez une
  date ; dès que la prochaine occurrence de l'échéancier dépasse cette date, il
  cesse de générer des transactions automatiquement. Les éléments sans date de
  fin continuent indéfiniment, exactement comme avant. Le tableau des Récurrents
  affiche une colonne **Fin**, et la prévision de trésorerie respecte aussi la
  date de fin. La table `recurring_transactions` gagne une colonne `end_date`
  nullable (migration v1.0.7). Nouveaux tests inclus.

## [1.8.0] - 2026-06-27

### Ajouté
- **Journal d'activité (piste d'audit).** Chaque création, modification et
  suppression effectuée par l'application — transactions, virements, comptes,
  catégories, budgets, objectifs, éléments récurrents, liste de suivi et
  changements de profil/paramètres — est enregistrée dans une nouvelle table
  `audit_log` en ajout seul, avec un horodatage et un instantané JSON.
  Exportable en CSV depuis **Paramètres ▸ Sauvegarde et restauration ▸ Exporter
  le journal d'activité**. Les effets de bord internes bruyants (mises à jour du
  solde courant, actualisations des prix du marché) ne sont volontairement pas
  journalisés, et les hachages de mots de passe ne sont jamais enregistrés —
  seulement qu'un changement a eu lieu. Pas de visionneuse intégrée ; export
  seulement. Nouveaux tests inclus.

### Corrigé
- **L'argent ne dérive plus de fractions de centime.** Les montants sont
  désormais arrondis au centime entier lors de leur stockage, et chaque mise à
  jour de solde de compte est fixée avec `ROUND(..., 2)` en SQL. Cela met fin aux
  petits écarts (<1 $) entre le solde d'un compte et la somme de ses
  transactions, qui provenaient du stockage de l'argent en virgule flottante
  binaire — valeurs sous le centime entrant via l'import CSV/Excel ou les écarts
  d'intérêt, plus une petite erreur d'accumulation dans le solde courant.
  S'applique à l'avenir ; les soldes existants se recalent au centime exact à
  leur prochaine transaction. Couvert par de nouveaux tests.

## [1.7.0] - 2026-06-23

### Ajouté
- **Prévision de trésorerie** — un nouveau panneau Prévision projette votre solde
  de comptes combiné (3 / 6 / 12 mois) à partir des revenus et dépenses
  récurrents, avec des cartes de synthèse, un graphique de solde projeté et un
  tableau de l'activité à venir qui signale tout découvert projeté. Bâti
  entièrement sur les données existantes (les virements entre vos propres comptes
  sont exclus) ; la logique est dans `RecurringService.forecast()` avec de
  nouveaux tests. Localisé anglais/français.
- **Exporter les transactions** depuis le panneau Transactions : un nouveau
  bouton ⤓ Exporter enregistre la liste *actuellement filtrée* (plage de dates,
  catégorie, compte, recherche) en CSV ou Excel. Localisé anglais/français ;
  couvert par de nouveaux tests.

## [1.6.0] - 2026-06-21

### Ajouté
- **Raccourcis clavier** sur les tableaux de données : appuyez sur `Suppr` pour
  retirer la ligne sélectionnée et `Entrée` pour la modifier (comme le
  double-clic), dans Transactions, Comptes, Récurrents et Marchés (Marchés ne
  gère que `Suppr`). Les raccourcis ne se déclenchent que lorsque le tableau a le
  focus.
- **Messages d'état vide** pour les tableaux Transactions, Comptes, Récurrents,
  Épargne (historique des intérêts) et tableau de bord (transactions récentes) :
  au lieu d'une grille vide, une liste vide affiche maintenant une invite
  conviviale, et le libellé des tableaux CRUD s'adapte (« rien pour l'instant »
  vs « rien ne correspond à vos filtres »). Localisé anglais/français.
- **Indices de raccourcis** dans les infobulles des boutons
  Modifier/Supprimer/Retirer (p. ex. « Supprimer la sélection (Suppr) ») pour que
  les nouveaux raccourcis clavier soient repérables.
- **La fenêtre se souvient de sa taille, sa position et le dernier panneau
  ouvert** entre les lancements (stocké via `QSettings`).

### Corrigé
- **Le choix de thème persiste maintenant entre les redémarrages.** La préférence
  sombre/clair est enregistrée par utilisateur (nouvelle colonne `theme`,
  migration v1.0.6) tout comme la langue, au lieu de revenir à sombre à chaque
  lancement. Un indicateur `--theme` explicite remplace toujours la valeur
  enregistrée pour cette exécution.

### Modifié
- `.claude/settings.local.json` est désormais ignoré par git et non suivi, si
  bien que les réglages Claude Code propres à la machine n'atterrissent plus dans
  les commits et les tags.

## [1.5.0] - 2026-06-20

### Ajouté
- **Colonnes de tableau triables au clic** dans chaque panneau (Transactions,
  Comptes, Récurrents, Marchés, Paramètres ▸ Catégories, Épargne et les
  transactions récentes du tableau de bord). Cliquez sur un en-tête de colonne
  pour trier en ordre croissant, cliquez à nouveau pour décroissant. Les colonnes
  de devise et de pourcentage se trient selon leur nombre sous-jacent (ainsi
  `1 000 $` vient après `200 $`, pas avant), via un nouvel utilitaire
  `views/sortable.py`.

## [1.4.0] - 2026-06-16

### Ajouté
- **Changer le mot de passe** dans Paramètres ▸ Sécurité : vérifie le mot de
  passe actuel, impose un minimum de 6 caractères et exige que le nouveau mot de
  passe diffère de l'ancien. Soutenu par `AuthService.change_password()` /
  `DatabaseManager.update_user_password()`. Localisé anglais/français.

### Modifié
- Épinglé toutes les dépendances de `requirements.txt` à des versions exactes
  pour des builds de release reproductibles, et déclaré `python-dateutil`
  explicitement (auparavant présent seulement de façon transitive via
  pandas/matplotlib).

## [1.3.1] - 2026-06-16

### Corrigé
- L'export du rapport PDF échouait toujours :
  `PDFReportGenerator.generate_monthly_report()` appelait `get_budgets()` avec
  les mauvais arguments (`month, year` au lieu de `user_id, month, year`),
  déclenchant une `TypeError` avant l'écriture du fichier. Ajout de tests de
  non-régression couvrant tout le parcours du rapport, y compris la section
  d'état du budget.

## [1.3.0] - 2026-06-13

### Ajouté
- **Alertes de budget** sur le tableau de bord : une carte listant les catégories
  ayant atteint 90 % ou plus de leur budget mensuel, marquées « Proche de la
  limite » (ambre) ou « Dépassé » (rouge) et triées du pire au meilleur. Soutenu
  par `DatabaseManager.get_budget_alerts()`. Localisé anglais/français.

## [1.2.0] - 2026-06-13

### Ajouté
- **Tendance de valeur nette** sur le tableau de bord : un graphique linéaire de
  la valeur nette totale sur les 12 derniers mois. Les points historiques sont
  reconstruits à partir des soldes de comptes actuels en rembobinant le flux de
  transactions de chaque mois (aucun changement de schéma requis). Soutenu par
  `DatabaseManager.get_net_worth_history()`.

## [1.1.0] - 2026-06-11

### Ajouté
- Index de base de données sur les chemins critiques des requêtes de
  transactions (`transactions(account_id, date)`, `transactions(category_id)`,
  `transactions(transfer_id)`, `accounts(user_id)`,
  `recurring_transactions(user_id)`, `financial_goals(user_id)`). Le schéma
  n'avait auparavant aucun index, si bien que la liste principale des
  transactions était un balayage complet de table ; le planificateur de requêtes
  utilise désormais des recherches indexées.

### Modifié
- `--seed` est maintenant idempotent : si l'utilisateur de démonstration a déjà
  des données, l'amorçage est ignoré au lieu de dupliquer comptes, transactions,
  objectifs et entrées récurrentes.

### Corrigé
- `--seed` plantait avec une `TypeError` car `upsert_budget()` était appelé sans
  son argument `user_id`.
- `--seed` plantait avec une `UnicodeEncodeError` sur la console Windows (cp1252)
  lors de l'affichage du message de fin, empêchant le lancement de l'application.

## [1.0.1] - antérieur

### Ajouté
- Installateur Windows (Inno Setup), joint aux versions GitHub à côté de
  l'exécutable portable.

## [1.0.0] - antérieur

- Première version publique (exécutable portable uniquement).

[Non publié]: https://github.com/LoloAbdo/budget_app/compare/v2.7.0...HEAD
[2.7.0]: https://github.com/LoloAbdo/budget_app/compare/v2.6.0...v2.7.0
[2.6.0]: https://github.com/LoloAbdo/budget_app/compare/v2.5.0...v2.6.0
[1.4.0]: https://github.com/LoloAbdo/budget_app/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/LoloAbdo/budget_app/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/LoloAbdo/budget_app/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/LoloAbdo/budget_app/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/LoloAbdo/budget_app/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/LoloAbdo/budget_app/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/LoloAbdo/budget_app/releases/tag/v1.0.0
