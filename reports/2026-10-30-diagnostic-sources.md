# Diagnostic des sources de cours — 2026-10-30

Lancé à 22:13 UTC (lecture seule, requêtes simples et espacées).

## Yahoo Finance (chart, 1m/1d)

| Tour | Symbole | HTTP | Prix | Horodatage (UTC) |
|---|---|---|---|---|
| 1 | MC.PA | 200 | 387.0 | 2026-10-30 16:36:29Z |
| 1 | AAPL | 200 | 344.63 | 2026-10-30 20:00:01Z |
| 1 | 7203.T | 200 | 3070.0 | 2026-10-30 06:30:00Z |
| 1 | EURUSD=X | 200 | 1.1166 | 2026-10-30 21:29:43Z |
| 1 | EUNL.DE | 200 | 129.685 | 2026-10-30 16:35:53Z |
| 2 | MC.PA | 200 | 387.0 | 2026-10-30 16:36:29Z |
| 2 | AAPL | 200 | 344.63 | 2026-10-30 20:00:01Z |
| 2 | 7203.T | 200 | 3070.0 | 2026-10-30 06:30:00Z |
| 2 | EURUSD=X | 200 | 1.1166 | 2026-10-30 21:29:43Z |
| 2 | EUNL.DE | 200 | 129.685 | 2026-10-30 16:35:53Z |
| 3 | MC.PA | 200 | 387.0 | 2026-10-30 16:36:29Z |
| 3 | AAPL | 200 | 344.63 | 2026-10-30 20:00:01Z |
| 3 | 7203.T | 200 | 3070.0 | 2026-10-30 06:30:00Z |
| 3 | EURUSD=X | 200 | 1.1166 | 2026-10-30 21:29:43Z |
| 3 | EUNL.DE | 200 | 129.685 | 2026-10-30 16:35:53Z |
| 4 | MC.PA | 200 | 387.0 | 2026-10-30 16:36:29Z |
| 4 | AAPL | 200 | 344.63 | 2026-10-30 20:00:01Z |
| 4 | 7203.T | 200 | 3070.0 | 2026-10-30 06:30:00Z |
| 4 | EURUSD=X | 200 | 1.1166 | 2026-10-30 21:29:43Z |
| 4 | EUNL.DE | 200 | 129.685 | 2026-10-30 16:35:53Z |

### Taux de réussite Yahoo

| Symbole | T1 | T2 | T3 | T4 | Total |
|---|---|---|---|---|---|
| MC.PA | OK | OK | OK | OK | 4/4 |
| AAPL | OK | OK | OK | OK | 4/4 |
| 7203.T | OK | OK | OK | OK | 4/4 |
| EURUSD=X | OK | OK | OK | OK | 4/4 |
| EUNL.DE | OK | OK | OK | OK | 4/4 |

## Stooq

| Symbole | HTTP | Réponse | Erreur curl |
|---|---|---|---|
| mc.fr | 000 | - | curl: (35) Recv failure: Connection reset by peer  |
| aapl.us | 000 | - | curl: (35) Recv failure: Connection reset by peer  |
| 7203.jp | 000 | - | curl: (35) Recv failure: Connection reset by peer  |
| eunl.de | 000 | - | curl: (35) Recv failure: Connection reset by peer  |
| eurusd | 000 | - | curl: (35) Recv failure: Connection reset by peer  |

## Frankfurter

| HTTP | Réponse |
|---|---|
| 200 | `{"amount":1.0,"base":"EUR","date":"2026-10-30","rates":{"GBP":0.8338,"JPY":175.68,"USD":1.1172}}` |
