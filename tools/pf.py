#!/usr/bin/env python3
"""Outil du portefeuille VIRTUEL (simulation, aucun ordre reel). Python 3, stdlib uniquement.

  python3 tools/pf.py check                         test reseau : 3 actions + EUR/USD
  python3 tools/pf.py quote SYM [SYM...]            cours (sans enregistrement)
  python3 tools/pf.py fx USD [GBP ...]              taux EUR/devise (1 EUR = x devise)
  python3 tools/pf.py trade buy|sell SYM QTE --session S --reason "..." [--dry-run]
  python3 tools/pf.py value --session S [--dry-run] valorisation + history.csv + tableaux markdown

Symboles au format Yahoo Finance : MC.PA, SAP.DE, AAPL, 7203.T, 0700.HK, RELIANCE.NS, ...
"""
import argparse, csv, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PF = os.path.join(ROOT, "state", "portfolio.json")
TX = os.path.join(ROOT, "state", "transactions.csv")
HIST = os.path.join(ROOT, "state", "history.csv")
PRICES = os.path.join(ROOT, "state", "prices.csv")

FEE_RATE, FEE_MIN, FX_FEE = 0.001, 1.0, 0.0025
MAX_AGE_OPEN = 60 * 60  # un cours plus vieux qu'une heure n'est pas exploitable pour un ordre
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SUBUNITS = {"GBp": ("GBP", 100), "GBX": ("GBP", 100), "ZAc": ("ZAR", 100), "ILA": ("ILS", 100)}


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso():
    return iso(time.time())


def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def quote(symbol):
    """Dernier cours reel. Leve une exception si aucun cours fiable : alors, aucun ordre."""
    err = None
    for host in ("query1", "query2"):
        url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1m&range=1d"
        try:
            m = http_json(url)["chart"]["result"][0]["meta"]
        except Exception as e:
            err = e
            continue
        p, t = m.get("regularMarketPrice"), m.get("regularMarketTime")
        if p is None or t is None:
            err = ValueError("reponse sans cours")
            continue
        cur = m.get("currency")
        if cur in SUBUNITS:
            cur, div = SUBUNITS[cur]
            p = p / div
        reg = (m.get("currentTradingPeriod") or {}).get("regular") or {}
        now = time.time()
        is_open = bool(reg) and reg["start"] <= now < reg["end"] and now - t < MAX_AGE_OPEN
        return {"symbole": symbol, "prix": float(p), "devise": cur,
                "place": m.get("fullExchangeName") or m.get("exchangeName"),
                "nom": m.get("longName") or m.get("shortName") or symbol,
                "horodatage_cours": iso(t), "age_min": round((now - t) / 60, 1),
                "marche_ouvert": is_open,
                "seance_utc": f"{iso(reg['start'])} -> {iso(reg['end'])}" if reg else None,
                "source": "Yahoo Finance chart API", "url": url}
    raise RuntimeError(f"{symbol} : aucun cours fiable ({err})")


def fx(cur):
    """Taux EUR/devise du moment (1 EUR = x devise)."""
    if cur == "EUR":
        return {"symbole": "EUR", "prix": 1.0, "horodatage_cours": now_iso(), "source": "identite", "url": ""}
    q = quote(f"EUR{cur}=X")
    if q["age_min"] > 24 * 60:
        raise RuntimeError(f"taux EUR{cur} trop ancien ({q['horodatage_cours']})")
    return q


def log_price(session, usage, q, devise=None):
    with open(PRICES, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([now_iso(), session, usage, q["symbole"], q.get("place", ""),
                                devise or q.get("devise", ""), f"{q['prix']:.6f}", q["horodatage_cours"],
                                q.get("marche_ouvert", ""), q["source"], q["url"]])


def load():
    with open(PF, encoding="utf-8") as f:
        return json.load(f)


def save(pf):
    with open(PF, "w", encoding="utf-8") as f:
        json.dump(pf, f, ensure_ascii=False, indent=2)
        f.write("\n")


def broker_fee(amount_eur):
    return max(FEE_MIN, round(amount_eur * FEE_RATE, 2))


def cmd_check(_):
    ok = True
    for s in ("MC.PA", "AAPL", "7203.T", "EURUSD=X"):
        try:
            q = quote(s)
            print(f"OK  {s:10} {q['prix']:>12.4f} {q['devise']}  cours du {q['horodatage_cours']}  ouvert={q['marche_ouvert']}  ({q['place']})")
        except Exception as e:
            ok = False
            print(f"ECHEC {s} : {e}")
    sys.exit(0 if ok else 1)


def cmd_quote(a):
    for s in a.symbols:
        try:
            print(json.dumps(quote(s), ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"symbole": s, "erreur": str(e)}, ensure_ascii=False))


def cmd_fx(a):
    for c in a.currencies:
        q = fx(c)
        print(f"1 EUR = {q['prix']:.6f} {c}  (cours du {q['horodatage_cours']}, {q['source']})")


def cmd_trade(a):
    if a.qty <= 0:
        sys.exit("quantite entiere strictement positive requise")
    pf = load()
    q = quote(a.symbol)
    if not q["marche_ouvert"]:
        sys.exit(f"REFUS : marche ferme ou cours non frais pour {a.symbol} (cours du {q['horodatage_cours']}, seance {q['seance_utc']})")
    r = fx(q["devise"])
    rate = r["prix"]
    gross = a.qty * q["prix"] / rate
    fx_fee = round(gross * FX_FEE, 2) if q["devise"] != "EUR" else 0.0
    fee = broker_fee(gross)
    pos = next((p for p in pf["positions"] if p["ticker"] == a.symbol), None)
    pv = ""
    if a.side == "buy":
        net = round(gross + fee + fx_fee, 2)
        if net > pf["liquidites_eur"] + 1e-9:
            sys.exit(f"REFUS : liquidites insuffisantes ({pf['liquidites_eur']:.2f} EUR < {net:.2f} EUR)")
        cash = round(pf["liquidites_eur"] - net, 2)
        if pos:
            pos["pru_eur"] = round((pos["quantite"] * pos["pru_eur"] + net) / (pos["quantite"] + a.qty), 4)
            pos["quantite"] += a.qty
        else:
            pos = {"ticker": a.symbol, "nom": q["nom"], "place": q["place"], "devise": q["devise"],
                   "quantite": a.qty, "pru_eur": round(net / a.qty, 4), "date_achat": q["horodatage_cours"][:10]}
            pf["positions"].append(pos)
    else:
        if not pos or pos["quantite"] < a.qty:
            sys.exit("REFUS : quantite detenue insuffisante (pas de vente a decouvert)")
        net = round(gross - fee - fx_fee, 2)
        pv = round(net - a.qty * pos["pru_eur"], 2)
        cash = round(pf["liquidites_eur"] + net, 2)
        pos["quantite"] -= a.qty
        if pos["quantite"] == 0:
            pf["positions"].remove(pos)
    summary = (f"{'ACHAT' if a.side == 'buy' else 'VENTE'} {a.qty} {a.symbol} @ {q['prix']:.4f} {q['devise']} "
               f"(cours du {q['horodatage_cours']}) | taux 1 EUR = {rate:.6f} {q['devise']} | brut {gross:.2f} EUR | "
               f"courtage {fee:.2f} | change {fx_fee:.2f} | net {net:.2f} EUR | liquidites apres {cash:.2f} EUR"
               + (f" | PV realisee {pv:.2f} EUR" if pv != "" else ""))
    if a.dry_run:
        print("SIMULATION (rien n'est ecrit) : " + summary)
        return
    pf["liquidites_eur"] = cash
    save(pf)
    log_price(a.session, "ordre", q)
    if q["devise"] != "EUR":
        log_price(a.session, "change ordre", r, q["devise"])
    with open(TX, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([now_iso(), a.session, "ACHAT" if a.side == "buy" else "VENTE", a.symbol, q["nom"],
                                q["place"], q["devise"], a.qty, f"{q['prix']:.4f}", q["horodatage_cours"], q["source"],
                                f"{rate:.6f}", r["source"], f"{gross:.2f}", f"{fee:.2f}", f"{fx_fee:.2f}", f"{net:.2f}",
                                pv, f"{cash:.2f}", a.reason])
    print("EXECUTE : " + summary)


def cmd_value(a):
    pf = load()
    rates, rows, titres = {}, [], 0.0
    for p in pf["positions"]:
        q = quote(p["ticker"])
        if q["devise"] not in rates:
            rates[q["devise"]] = fx(q["devise"])
        rate = rates[q["devise"]]["prix"]
        val = p["quantite"] * q["prix"] / rate
        titres += val
        rows.append((p, q, val, val - p["quantite"] * p["pru_eur"]))
        if not a.dry_run:
            log_price(a.session, "valorisation", q)
    if not a.dry_run:
        for c, r in rates.items():
            if c != "EUR":
                log_price(a.session, "change valorisation", r, c)
    cash = pf["liquidites_eur"]
    total = cash + titres
    cap = pf["capital_initial_eur"]

    bm = pf["benchmark"]
    bq = quote(bm["ticker"])
    if bm["cours_depart"] is None:
        bm["cours_depart"], bm["date_depart"] = bq["prix"], bq["horodatage_cours"]
    bm_val = cap * bq["prix"] / bm["cours_depart"]

    prev = None
    if os.path.exists(HIST):
        with open(HIST, encoding="utf-8") as f:
            hist = list(csv.DictReader(f))
        prev = float(hist[-1]["valeur_totale_eur"]) if hist else None
    var = total - prev if prev is not None else 0.0

    print(f"## Valeur\n")
    print(f"| Indicateur | Valeur |\n|---|---|")
    print(f"| Valeur totale | {total:,.2f} EUR |")
    print(f"| Liquidites | {cash:,.2f} EUR ({cash / total * 100:.1f} %) |")
    print(f"| Performance depuis le debut | {total - cap:+,.2f} EUR ({(total / cap - 1) * 100:+.2f} %) |")
    print(f"| Variation depuis la session precedente | {var:+,.2f} EUR ({(var / prev * 100) if prev else 0:+.2f} %) |")
    print(f"| Benchmark {bm['ticker']} (base {cap:,.0f} EUR) | {bm_val:,.2f} EUR ({(bm_val / cap - 1) * 100:+.2f} %), cours {bq['prix']:.4f} du {bq['horodatage_cours']} |")
    print(f"| Ecart vs benchmark | {(total / cap - bm_val / cap) * 100:+.2f} points |\n")
    print("## Positions\n")
    if rows:
        print("| Titre | Place | Qte | Cours | Cours du (UTC) | Valeur EUR | PRU EUR | +/- latente EUR | +/- % | Poids |")
        print("|---|---|---:|---:|---|---:|---:|---:|---:|---:|")
        for p, q, val, pnl in rows:
            cost = p["quantite"] * p["pru_eur"]
            print(f"| {p['ticker']} {p['nom']} | {p['place']} | {p['quantite']} | {q['prix']:.4f} {q['devise']} | {q['horodatage_cours']} | "
                  f"{val:,.2f} | {p['pru_eur']:.4f} | {pnl:+,.2f} | {pnl / cost * 100:+.2f} % | {val / total * 100:.1f} % |")
        for c, r in rates.items():
            if c != "EUR":
                print(f"\nTaux utilise : 1 EUR = {r['prix']:.6f} {c} (cours du {r['horodatage_cours']}, {r['source']}). Valorisation au taux moyen, hors frais de sortie.")
    else:
        print("Aucune position : 100 % liquidites.")

    if a.dry_run:
        return
    log_price(a.session, "benchmark", bq)
    pf["derniere_session"] = a.session
    save(pf)
    with open(HIST, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([now_iso(), a.session, f"{total:.2f}", f"{cash:.2f}", f"{titres:.2f}",
                                f"{total - cap:.2f}", f"{(total / cap - 1) * 100:.4f}", f"{var:.2f}",
                                f"{(var / prev * 100) if prev else 0:.4f}", bm["ticker"], f"{bq['prix']:.4f}",
                                f"{bm_val:.2f}", f"{(bm_val / cap - 1) * 100:.4f}"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("check").set_defaults(fn=cmd_check)
    p = sp.add_parser("quote"); p.add_argument("symbols", nargs="+"); p.set_defaults(fn=cmd_quote)
    p = sp.add_parser("fx"); p.add_argument("currencies", nargs="+"); p.set_defaults(fn=cmd_fx)
    p = sp.add_parser("trade")
    p.add_argument("side", choices=["buy", "sell"]); p.add_argument("symbol"); p.add_argument("qty", type=int)
    p.add_argument("--session", required=True); p.add_argument("--reason", required=True)
    p.add_argument("--dry-run", action="store_true"); p.set_defaults(fn=cmd_trade)
    p = sp.add_parser("value")
    p.add_argument("--session", required=True); p.add_argument("--dry-run", action="store_true"); p.set_defaults(fn=cmd_value)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
