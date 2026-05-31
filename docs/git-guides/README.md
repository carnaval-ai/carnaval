# Documentation du Projet Carnaval et Procédures Git / Push

Ce document présente l'architecture du projet Carnaval et les méthodes pour valider les modifications et les pousser proprement vers le dépôt distant, y compris les cas exceptionnels de désinfection d'historique.

---

## 1. Présentation du Projet Carnaval

**Carnaval** est une bibliothèque Python professionnelle conçue pour détecter, masquer (anonymiser) et réinjecter les données personnelles (PII - Personally Identifiable Information) dans des documents textuels, JSON, XML ou HTML.

### Architecture Principale
- `src/carnaval/core` : Logique centrale (gestion des `Span` de texte, du coffre-fort chiffré `Vault` et du pipeline d'anonymisation).
- `src/carnaval/recognizers` : Détecteurs modulaires basés sur des expressions régulières (Regex) ou des modèles d'intelligence artificielle (GLiNER).
- `docs/` : Site web statique intégrant un **simulateur interactif** en temps réel et un benchmark de performances comparatives.
- `tests/` : Suite complète de tests unitaires et d'intégration.

---

## 2. Validation Locale (Tests)

Avant de pousser toute modification sur le dépôt distant, il est crucial de s'assurer que la suite de tests est entièrement verte.

Pour exécuter les tests avec `pytest` depuis la racine du projet :
```bash
# Activation de l'environnement virtuel et lancement des tests
.venv/Scripts/pytest
```

---

## 3. Méthodes de Push Git Standards

Pour pousser des développements classiques sur les branches du dépôt :

```bash
# 1. Suivi des modifications
git add .

# 2. Enregistrement des modifications
git commit -m "Description claire et concise de l'apport"

# 3. Pousser vers le dépôt distant (exemples pour master ou main)
git push origin master
git push origin main
```

---

## 4. Procédure Exceptionnelle de Désinfection et de Push Forcé (Purge d'historique)

Dans le cas exceptionnel où des données sensibles ou confidentielles auraient été validées par erreur dans l'historique des commits, suivez scrupuleusement cette procédure pour purger définitivement le dépôt local et distant :

### Étape A : Remplacement dans les fichiers locaux
Appliquer les modifications de correction ou exécuter un script de remplacement sur les fichiers du répertoire de travail, puis valider le commit de correction :
```bash
git add .
git commit -m "Anonymize simulator bank details with valid mock ones"
```

### Étape B : Filtrage de tout l'historique Git
Pour réécrire l'historique de toutes les branches locales à l'aide d'un script de nettoyage python (ici nommé `clean_script.py`) :
```bash
# (Optionnel sous Windows pour masquer l'avertissement de filter-branch)
set FILTER_BRANCH_SQUELCH_WARNING=1

# Lancement de la réécriture sur toutes les branches
git filter-branch --tree-filter "python path/to/clean_script.py" --force -- --all
```

### Étape C : Purge des sauvegardes Git et Garbage Collection
Git conserve par défaut les anciennes versions dans `refs/original/` et dans les reflogs. Pour les détruire définitivement de votre base de données locale :
```bash
# Suppression des références originales créées par filter-branch
git update-ref -d refs/original/refs/heads/master
git update-ref -d refs/original/refs/heads/main
git update-ref -d refs/original/refs/heads/v0.2.0-bilingual-publishable

# Expiration immédiate des reflogs
git reflog expire --expire=now --all

# Lancement d'un nettoyage agressif de la base Git
git gc --prune=now --aggressive
```

### Étape D : Push forcé sur le dépôt distant
Une fois l'historique local réécrit et purgé, forcez la mise à jour sur le serveur distant pour écraser les anciennes branches contenant les fuites :
```bash
git push origin master --force
git push origin main --force
git push origin v0.2.0-bilingual-publishable --force
```
