# The Horse Farm — réservations

Version finale : réservation en ligne sans paiement en ligne.

## Tarifs
- 1 heure : 30 € / cavalier
- 2 heures : 50 € / cavalier
- Maximum : 3 cavaliers
- Acompte indicatif : 10 € / cavalier pour 1 h, 20 € / cavalier pour 2 h
- Solde payé sur place

## Fonctionnement
Le client choisit la durée, la date, l'heure et le nombre de cavaliers, puis renseigne ses coordonnées.
Le site calcule le total, l'acompte et le solde. Le client clique sur « Demander ma réservation ».
Aucun paiement n'est effectué en ligne. La demande apparaît dans l'administration et doit être confirmée manuellement.

## Lancer
```bash
pip install -r requirements.txt
python app.py
```

Puis ouvrir http://127.0.0.1:5000

## Administration
Ouvrir `/admin`.
Mot de passe par défaut : `admin123`.
Pour un vrai hébergement, définir `ADMIN_PASSWORD` et `SECRET_KEY` dans les variables d'environnement.

## Remarque
La base SQLite est créée automatiquement. Avant une mise en production, prévoir une sauvegarde régulière de `reservations.db`.
