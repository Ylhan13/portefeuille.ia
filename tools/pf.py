#!/usr/bin/env python3
"""Calculs du portefeuille VIRTUEL (simulation, aucun ordre reel). Python 3, stdlib. Aucun acces reseau.

Les cours sont releves par le gerant sur le web et ecrits dans un fichier JSON :
  {"MC.PA": {"prix": 387.0, "devise": "EUR", "horodatage": "2026-11-02T08:20:00Z", "source": "Boursorama", "url": "https://...",
             "nom": "LVMH", "place": "EUROPE"},
   "EUR/USD": {"prix": 1.1166, "devise": "USD", "horodatage": "...", "source": "...", "url": "..."}}

  python3 tools/pf.py trade buy|sell SYM QTE --cours F --session S --reason "..." [--dry-run]
  python3 tools/pf.py value --cours F --session S [--dry-run]
"""
import argparse, csv, json, os, sys
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PF = os.path.join(ROOT, "state", "portfolio.json")
TX = os.path.join(ROOT, "state", "transactions.csv")
HIST = os.path.join(ROOT, "state", "history.csv")
PRICES = os.path.join(ROOT, "state", "prices.csv")

FEE_RATE, FEE_MIN, FX_FEE = 0.001, 1.0, 0.0025
MAX_AGE_ORDRE_MIN = 60  # un cours plus vieux n'est pas exploitable pour un ordre
MAX_AGE_CHANGE_H = 24
PLACES = {"EUROPE": ("Europe/Paris", (9, 0), (17, 30)), "LONDRES": ("Europe/London", (8, 0), (16, 30)),
          "NEWYORK": ("America/New_York", (9, 30), (16, 0)), "TORONTO": ("America/Toronto", (9, 30), (16, 0)),
          "TOKYO": ("Asia/Tokyo", (9, 0), (15, 30)), "HONGKONG": ("Asia/Hong_Kong", (9, 30), (16, 0)),
          "SHANGHAI": ("Asia/Shanghai", (9, 30), (15, 0)), "SEOUL": ("Asia/Seoul", (9, 0), (15, 30)),
          "INDE": ("Asia/Kolkata", (9, 15), (15, 30)), "SYDNEY": ("Australia/Sydney", (10, 0), (16, 0))}


def now():
    return datetime.now(timezone.utc)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_cours(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get(cours, sym):
    """Cours releve et verifie. Sans cours complet : aucun ordre."""
    q = cours.get(sym)
    if not q:
        sys.exit(f"REFUS : aucun cours releve pour {sym}")
    for k in ("prix", "devise", "horodatage", "source", "url"):
        if not q.get(k):
            sys.exit(f"REFUS : {sym} sans {k}")
    if float(q["prix"]) <= 0:
        sys.exit(f"REFUS : prix invalide pour {sym}")
    t = datetime.fromisoformat(q["horodatage"].replace("Z", "+00:00"))
    if t.tzinfo is None:
        sys.exit(f"REFUS : horodatage de {sym} sans fuseau")
    age = (now() - t).total_seconds() / 60
    if age < -5:
        sys.exit(f"REFUS : horodatage futur pour {sym}")
    return dict(q, symbole=sym, prix=float(q["prix"]), age_min=age)


def fx(cours, cur):
    """Taux EUR/devise (1 EUR = x devise)."""
    if cur == "EUR":
        return {"symbole": "EUR", "prix": 1.0, "horodatage": iso(now()), "source": "identite", "url": "", "devise": "EUR", "age_min": 0}
    r = get(cours, f"EUR/{cur}")
    if r["age_min"] > MAX_AGE_CHANGE_H * 60:
        sys.exit(f"REFUS : taux EUR/{cur} trop ancien ({r['horodatage']})")
    return r


def ouvert(place):
    if place not in PLACES:
        sys.exit(f"REFUS : place inconnue {place} (choix : {', '.join(PLACES)})")
    tz, a, b = PLACES[place]
    t = now().astimezone(ZoneInfo(tz))
    return t.weekday() < 5 and dtime(*a) <= t.time() < dtime(*b)


def log_price(session, usage, q, ouv=""):
    with open(PRICES, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([iso(now()), session, usage, q["symbole"], q.get("place", ""), q["devise"],
                                f"{q['prix']:.6f}", q["horodatage"], ouv, q["source"], q["url"]])


def load():
    with open(PF, encoding="utf-8") as f:
        return json.load(f)


def save(pf):
    with open(PF, "w", encoding="utf-8") as f:
        json.dump(pf, f, ensure_ascii=False, indent=2)
        f.write("\n")


def cmd_trade(a):
    if a.qty <= 0:
        sys.exit("quantite entiere strictement positive requise")
    pf = load()
    cours = load_cours(a.cours)
    q = get(cours, a.symbol)
    place = q.get("place", "")
    if not ouvert(place):
        sys.exit(f"REFUS : place {place} fermee")
    if q["age_min"] > MAX_AGE_ORDRE_MIN:
        sys.exit(f"REFUS : cours de {a.symbol} trop ancien ({q['horodatage']})")
    r = fx(cours, q["devise"])
    rate = r["prix"]
    gross = a.qty * q["prix"] / rate
    fx_fee = round(gross * FX_FEE, 2) if q["devise"] != "EUR" else 0.0
    fee = max(FEE_MIN, round(gross * FEE_RATE, 2))
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
            pf["positions"].append({"ticker": a.symbol, "nom": q.get("nom", a.symbol), "place": place, "devise": q["devise"],
                                    "quantite": a.qty, "pru_eur": round(net / a.qty, 4), "date_achat": iso(now())[:10]})
    else:
        if not pos or pos["quantite"] < a.qty:
            sys.exit("REFUS : quantite detenue insuffisante (pas de vente a decouvert)")
        net = round(gross - fee - fx_fee, 2)
        pv = round(net - a.qty * pos["pru_eur"], 2)
        cash = round(pf["liquidites_eur"] + net, 2)
        pos["quantite"] -= a.qty
        if pos["quantite"] == 0:
            pf["positions"].remove(pos)
    sens = "ACHAT" if a.side == "buy" else "VENTE"
    summary = (f"{sens} {a.qty} {a.symbol} @ {q['prix']:.4f} {q['devise']} (cours du {q['horodatage']}, {q['source']}) | "
               f"taux 1 EUR = {rate:.6f} {q['devise']} | brut {gross:.2f} EUR | courtage {fee:.2f} | change {fx_fee:.2f} | "
               f"net {net:.2f} EUR | liquidites apres {cash:.2f} EUR" + (f" | PV realisee {pv:.2f} EUR" if pv != "" else ""))
    if a.dry_run:
        print("SIMULATION (rien n'est ecrit) : " + summary)
        return
    pf["liquidites_eur"] = cash
    save(pf)
    log_price(a.session, "ordre", q, True)
    if q["devise"] != "EUR":
        log_price(a.session, "change ordre", r)
    with open(TX, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([iso(now()), a.session, sens, a.symbol, q.get("nom", a.symbol), place, q["devise"], a.qty,
                                f"{q['prix']:.4f}", q["horodatage"], q["source"], f"{rate:.6f}", r["source"], f"{gross:.2f}",
                                f"{fee:.2f}", f"{fx_fee:.2f}", f"{net:.2f}", pv, f"{cash:.2f}", a.reason])
    print("EXECUTE : " + summary)


def cmd_value(a):
    pf = load()
    cours = load_cours(a.cours)
    rates, rows, titres = {}, [], 0.0
    for p in pf["positions"]:
        q = get(cours, p["ticker"])
        if q["devise"] not in rates:
            rates[q["devise"]] = fx(cours, q["devise"])
        val = p["quantite"] * q["prix"] / rates[q["devise"]]["prix"]
        titres += val
        rows.append((p, q, val, val - p["quantite"] * p["pru_eur"]))
    cash = pf["liquidites_eur"]
    total = cash + titres
    cap = pf["capital_initial_eur"]
    bm = pf["benchmark"]
    bq = get(cours, bm["ticker"])
    if bm["cours_depart"] is None:
        bm["cours_depart"], bm["date_depart"] = bq["prix"], bq["horodatage"]
    bm_val = cap * bq["prix"] / bm["cours_depart"]
    with open(HIST, encoding="utf-8") as f:
        hist = list(csv.DictReader(f))
    prev = float(hist[-1]["valeur_totale_eur"]) if hist else None
    var = total - prev if prev is not None else 0.0
    print("## Valeur\n")
    print("| Indicateur | Valeur |\n|---|---|")
    print(f"| Valeur totale | {total:,.2f} EUR |")
    print(f"| Liquidites | {cash:,.2f} EUR ({cash / total * 100:.1f} %) |")
    print(f"| Performance depuis le debut | {total - cap:+,.2f} EUR ({(total / cap - 1) * 100:+.2f} %) |")
    print(f"| Variation depuis la session precedente | {var:+,.2f} EUR ({(var / prev * 100) if prev else 0:+.2f} %) |")
    print(f"| Benchmark {bm['ticker']} (base {cap:,.0f} EUR) | {bm_val:,.2f} EUR ({(bm_val / cap - 1) * 100:+.2f} %), cours {bq['prix']:.4f} du {bq['horodatage']} ({bq['source']}) |")
    print(f"| Ecart vs benchmark | {(total - bm_val) / cap * 100:+.2f} points |\n")
    print("## Positions\n")
    if rows:
        print("| Titre | Place | Qte | Cours | Cours du (UTC) | Source | Valeur EUR | PRU EUR | +/- latente EUR | +/- % | Poids |")
        print("|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|")
        for p, q, val, pnl in rows:
            cost = p["quantite"] * p["pru_eur"]
            print(f"| {p['ticker']} {p['nom']} | {p['place']} | {p['quantite']} | {q['prix']:.4f} {q['devise']} | {q['horodatage']} | {q['source']} | "
                  f"{val:,.2f} | {p['pru_eur']:.4f} | {pnl:+,.2f} | {pnl / cost * 100:+.2f} % | {val / total * 100:.1f} % |")
    else:
        print("Aucune position : 100 % liquidites.")
    if a.dry_run:
        return
    for p, q, _, _ in rows:
        log_price(a.session, "valorisation", q)
    for c, r in rates.items():
        if c != "EUR":
            log_price(a.session, "change valorisation", r)
    log_price(a.session, "benchmark", bq)
    pf["derniere_session"] = a.session
    save(pf)
    with open(HIST, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([iso(now()), a.session, f"{total:.2f}", f"{cash:.2f}", f"{titres:.2f}", f"{total - cap:.2f}",
                                f"{(total / cap - 1) * 100:.4f}", f"{var:.2f}", f"{(var / prev * 100) if prev else 0:.4f}",
                                bm["ticker"], f"{bq['prix']:.4f}", f"{bm_val:.2f}", f"{(bm_val / cap - 1) * 100:.4f}"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("trade")
    p.add_argument("side", choices=["buy", "sell"]); p.add_argument("symbol"); p.add_argument("qty", type=int)
    p.add_argument("--cours", required=True); p.add_argument("--session", required=True); p.add_argument("--reason", required=True)
    p.add_argument("--dry-run", action="store_true"); p.set_defaults(fn=cmd_trade)
    p = sp.add_parser("value")
    p.add_argument("--cours", required=True); p.add_argument("--session", required=True)
    p.add_argument("--dry-run", action="store_true"); p.set_defaults(fn=cmd_value)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
