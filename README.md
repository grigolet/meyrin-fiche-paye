# Meyrin CTT · documents entraîneurs

Petite application Flask pour créer deux PDF professionnels depuis un téléphone ou un ordinateur :

- bulletins de paye, avec calcul du salaire brut, des retenues et du salaire net ;
- factures d'entraîneur, avec lignes de prestations, TVA facultative et coordonnées de paiement.
- profils d'entraîneurs réutilisables, enregistrés localement dans le navigateur pour préremplir les coordonnées.

Les calculs du bulletin reprennent le fichier Excel de référence : rémunération horaire + rémunération journalière, rémunérations exonérées facultatives, puis retenues calculées sur la seule base soumise aux cotisations et arrondies individuellement au centime. Les profils sont sauvegardés uniquement dans le stockage local du navigateur utilisé. Ils ne sont ni envoyés au serveur ni ajoutés au dépôt Git.

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
