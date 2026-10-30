# portefeuille-ia

Simulation d'un mois de gestion d'un compte-titres ordinaire **virtuel** de 2 500 € par un gérant IA. Aucun ordre réel.

- `SESSION.md` : procédure suivie par chaque session planifiée (9h15 et 21h30, heure de Paris, du lundi au vendredi).
- `state/portfolio.json` : liquidités et positions.
- `state/transactions.csv` : opérations (prix, frais, taux de change, justification).
- `state/history.csv` : valeur du portefeuille et du benchmark à chaque session.
- `state/prices.csv` : chaque cours utilisé, avec source et horodatage.
- `reports/` : un rapport par session, plus le rapport final.
- `tools/pf.py` : calculs et contrôles (frais, change, PRU, valorisation, horaires) à partir des cours relevés sur le web.
