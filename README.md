# Meyrin CTT · documents du personnel

Petite application Flask pour créer deux PDF professionnels depuis un téléphone ou un ordinateur :

- bulletins de paye, avec calcul du salaire brut, des retenues et du salaire net ;
- factures de collaborateurs ou prestataires, avec lignes de prestations, TVA facultative et coordonnées de paiement.
- profils du personnel réutilisables, enregistrés localement dans le navigateur pour préremplir les coordonnées.

Les calculs du bulletin reprennent le fichier Excel de référence. La rémunération peut être saisie avec un tarif horaire global ou détaillée en plusieurs activités datées (par exemple nettoyage, entraînement et formations). Chaque ligne horaire peut être incluse dans les charges ou exclue individuellement, et les cotisations et retenues peuvent aussi être désactivées pour le bulletin entier. Les rémunérations exonérées facultatives restent hors de leur base de calcul, et chaque retenue active est arrondie individuellement au centime. Un champ de notes facultatif permet d'ajouter des informations complémentaires au bulletin. Les profils sont sauvegardés uniquement dans le stockage local du navigateur utilisé. Ils ne sont ni envoyés au serveur ni ajoutés au dépôt Git.

## Lancer localement

Avec Python 3.11 ou plus récent :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Ouvrir ensuite <http://127.0.0.1:5000>.

## Protéger l'application

Les données de salaire sont sensibles. En local, l'application démarre sans mot de passe. Pour un déploiement public, définir les variables suivantes :

```text
APP_USERNAME=admin
APP_PASSWORD=un-mot-de-passe-long-et-unique
```

Le navigateur demandera ces identifiants avant d'afficher les formulaires.

## Déployer sur Railway

Depuis ce dossier :

```powershell
railway up
```

Le fichier `railway.json` configure le démarrage et la vérification de santé. Dans Railway, ajouter `APP_USERNAME` et `APP_PASSWORD` dans les variables du service avant de créer un domaine public.

Si la commande `railway` n'est pas encore installée sous Windows, l'installer une fois avec `npm i -g @railway/cli`, puis relancer `railway up`.

## Vérifier

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

Le logo provient du site officiel du [Meyrin CTT](https://www.meyrinctt.ch/). Les données personnelles des documents de référence ne sont pas incluses dans le dépôt.
