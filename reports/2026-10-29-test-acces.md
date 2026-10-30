# Test d'accès aux cours — 2026-10-29
_Simulation : portefeuille virtuel, aucun ordre réel. Test lancé le 2026-10-29 vers 11:02 Paris (10:02 UTC)._

## Résultat : ÉCHEC — aucun cours accessible depuis cet environnement

Les 4 symboles ont échoué. La première session (étape C) n'a **pas** été exécutée : aucun ordre, aucune ligne d'historique, aucun cours enregistré. Aucun contournement n'a été tenté.

## 1. `python3 tools/pf.py check` (code de sortie 1)

```
ECHEC MC.PA : MC.PA : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC AAPL : AAPL : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC 7203.T : 7203.T : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC EURUSD=X : EURUSD=X : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
```

## 2. `curl -sS -m 20 -A 'Mozilla/5.0' 'https://query1.finance.yahoo.com/v8/finance/chart/AAPL'` (code de sortie 56)

```
curl: (56) CONNECT tunnel failed, response 403
```

Journal du proxy sortant de l'environnement (`$HTTPS_PROXY/__agentproxy/status`, extrait) :

```
"kind": "connect_rejected",
"detail": "gateway answered 403 to CONNECT (policy denial or upstream failure)",
"host": "query1.finance.yahoo.com:443"   (idem pour query2.finance.yahoo.com:443)
```

## 3. WebFetch de https://finance.yahoo.com/quote/AAPL

```
getaddrinfo ENOTFOUND finance.yahoo.com
```

(Le domaine ne se résout pas : il est hors des domaines réseau autorisés de la session.)

## Diagnostic et action requise

La politique réseau de l'environnement cloud bloque les domaines Yahoo Finance. Pour que les sessions fonctionnent, il faut autoriser dans les paramètres réseau de l'environnement (https://code.claude.com/docs/en/claude-code-on-the-web) au minimum :
- `query1.finance.yahoo.com`
- `query2.finance.yahoo.com`
- (optionnel, pour WebFetch) `finance.yahoo.com`

Il faudra aussi vérifier que WebSearch/WebFetch vers les sites d'actualité sont permis pour l'étape d'analyse.

## Nouveau test après ouverture du réseau

- Horodatage : 2026-10-29T10:39:51Z (11:39:51 heure de Paris, CET)
- Commandes : `git checkout main && git pull origin main` (« Already up to date », HEAD 2fd1c41), puis `python3 tools/pf.py check` (code de sortie 1)

Sortie brute :

```
ECHEC MC.PA : MC.PA : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC AAPL : AAPL : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC 7203.T : 7203.T : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC EURUSD=X : EURUSD=X : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
```

Diagnostic du proxy de l'environnement (`/__agentproxy/status`) : `connect_rejected` — « gateway answered 403 to CONNECT (policy denial or upstream failure) » pour `query1.finance.yahoo.com:443` et `query2.finance.yahoo.com:443`.

Conclusion : les 4 symboles échouent toujours pour une raison réseau (le proxy refuse toujours Yahoo Finance ; la politique réseau ne semble pas appliquée à cette session, ou les hôtes `query1/query2.finance.yahoo.com` ne sont pas autorisés). Aucune session exécutée, aucun ordre virtuel passé, aucun contournement tenté.

## Test du 2026-10-30 après enregistrement du réseau

- Horodatage : 2026-10-30T20:55:24Z (21:55:24 heure de Paris, CET)
- Commandes : `git fetch origin main && git checkout -B main origin/main`, puis `python3 tools/pf.py check` (code de sortie 1)

Sortie brute :

```
ECHEC MC.PA : MC.PA : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC AAPL : AAPL : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC 7203.T : 7203.T : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
ECHEC EURUSD=X : EURUSD=X : aucun cours fiable (<urlopen error Tunnel connection failed: 403 Forbidden>)
```

Diagnostic du proxy (`/__agentproxy/status`, `"selective": false`) : `connect_rejected` — « gateway answered 403 to CONNECT (policy denial or upstream failure) » pour `query1.finance.yahoo.com:443` et `query2.finance.yahoo.com:443` à 20:55:24Z. Contrôle `curl https://query1.finance.yahoo.com/...` : `CONNECT tunnel failed, response 403`.

Conclusion : les 4 symboles échouent encore, même erreur qu'hier. Le changement de politique réseau n'est pas effectif dans cette session (ou Yahoo Finance reste refusé par la passerelle). Étapes 2 et 3 non exécutées : SESSION.md et state/portfolio.json inchangés, aucune session, aucun ordre virtuel, aucun contournement.

## Test du 2026-10-30 après enregistrement du réseau (2e essai, réseau ouvert)

- Horodatage : 2026-10-30T22:03:01Z (23:03:01 heure de Paris, CET)
- Commandes : `git fetch origin main && git checkout -B main origin/main`, puis `python3 tools/pf.py check` (code de sortie 1)

Sortie brute :

```
ECHEC MC.PA : MC.PA : aucun cours fiable (HTTP Error 429: Too Many Requests)
OK  AAPL           344.6300 USD  cours du 2026-10-30T20:00:01Z  ouvert=False  (NasdaqGS)
ECHEC 7203.T : 7203.T : aucun cours fiable (HTTP Error 429: Too Many Requests)
ECHEC EURUSD=X : EURUSD=X : aucun cours fiable (HTTP Error 429: Too Many Requests)
```

Conclusion : le réseau est désormais ouvert (plus de 403 du proxy, AAPL répond), mais Yahoo Finance limite le débit : 3 symboles sur 4 échouent avec `HTTP Error 429: Too Many Requests`. Conformément à la consigne, arrêt ici : étapes 2 et 3 non exécutées, SESSION.md et state/portfolio.json inchangés, aucune session, aucun ordre virtuel, aucun contournement.

## Test après espacement des requêtes

- Horodatage : lancé à 2026-10-30T22:25:40Z (23:25:40 heure de Paris, CET), terminé vers 22:49 UTC (≈ 24 min, du fait des pauses de reprise)
- Modification de `tools/pf.py` : `urllib.error` importé ; `http_json` attend 3 s avant chaque requête et, sur HTTP 429, réessaie jusqu'à 4 fois par hôte avec des pauses de 30, 60 puis 90 s (soit jusqu'à 8 tentatives par symbole via query1 puis query2).
- Commandes : `git fetch origin main && git checkout -B main origin/main`, puis `python3 tools/pf.py check`

Sortie brute :

```
ECHEC MC.PA : MC.PA : aucun cours fiable (HTTP Error 429: Too Many Requests)
OK  AAPL           344.6300 USD  cours du 2026-10-30T20:00:01Z  ouvert=False  (NasdaqGS)
ECHEC 7203.T : 7203.T : aucun cours fiable (HTTP Error 429: Too Many Requests)
ECHEC EURUSD=X : EURUSD=X : aucun cours fiable (HTTP Error 429: Too Many Requests)
```

Erreur exacte (MC.PA, 7203.T, EURUSD=X) : `HTTP Error 429: Too Many Requests`, renvoyée par Yahoo Finance sur query1 et query2 à chacune des tentatives, y compris après 30, 60 et 90 s d'attente. Seul AAPL répond.

Conclusion : l'espacement des requêtes (3 s) et les reprises avec pause ne suffisent pas depuis cet environnement : 3 symboles sur 4 restent en 429. Le 429 semble lié à l'adresse sortante (ou à l'absence de cookie/crumb Yahoo) plutôt qu'aux seules rafales. Conformément à la consigne, arrêt ici : étapes 2 et 3 non exécutées, SESSION.md et state/portfolio.json inchangés, aucune session, aucun ordre virtuel, aucun contournement. Seuls `tools/pf.py` (modification demandée) et ce rapport sont modifiés.
