"""Unseen test: new questions that were not used to tune the prompt."""
import csv
import sys
import time

from src.sql_agent import ask

sys.stdout.reconfigure(encoding="utf-8")

CASES = [
    ("Which employee manages the most people?", "multi-step",
     "Uses ReportsTo and names one employee with a count"),
    ("How much did customers from Brazil spend in total?", "simple",
     "Sums invoice totals for Brazil"),
    ("Which customers have never bought anything?", "empty result",
     "Says there are none (or lists them), without inventing"),
    ("What is the most expensive album?", "ambiguous",
     "Says how album price was measured (albums have no price column)"),
    ("What is the profit margin of each genre?", "unanswerable",
     "Says there is no cost or profit data"),
    ("List the customers who are unhappy with us.", "unanswerable",
     "Says there is no satisfaction data"),
    ("Compare total sales in 2011 and 2012.", "simple",
     "Gives both totals"),
    ("Who composed the most tracks?", "NULL trap",
     "Ignores tracks with no composer, does not report 'NULL' as the top"),
]

rows = []
for q, kind, good in CASES:
    print("=" * 70)
    print("Q:", q, f"[{kind}]")
    try:
        res = ask(q)
        sql, answer, err = res["sql"], res["answer"], res["error"]
        n = len(res["rows"])
    except Exception as e:
        sql, answer, err, n = "", "", str(e), 0
    print("SQL   :", sql)
    print("ROWS  :", n)
    print("ANSWER:", answer or err)
    print("GOOD  :", good)
    rows.append([q, kind, good, sql, n, answer, err, ""])
    time.sleep(5)

with open("reports/unseen_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["question", "kind", "good_behavior", "generated_sql",
                "rows", "answer", "error", "verdict"])
    w.writerows(rows)
print("\nSaved reports/unseen_results.csv")