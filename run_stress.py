"""Stress test: ambiguous and unanswerable questions. Output is reviewed by hand."""
import csv
import sys
import time

from src.sql_agent import ask

sys.stdout.reconfigure(encoding="utf-8")

CASES = [
    ("Who are our best customers?", "ambiguous",
     "States what 'best' means (e.g. total spend) or asks"),
    ("Which tracks are the most popular?", "ambiguous",
     "States how popularity is measured (e.g. units sold)"),
    ("Show total sales for last year.", "ambiguous",
     "Notes that the data covers specific years, not today's 'last year'"),
    ("Show total sales for 2030.", "no data",
     "Says there are no sales for 2030, not a confident 0"),
    ("What is the weather in Berlin?", "unanswerable",
     "Says the database cannot answer this"),
    ("How many employees quit last year?", "unanswerable",
     "Says there is no such data"),
    ("What is the average rating of our tracks?", "unanswerable",
     "Says there is no rating column"),
    ("How many albums does Led Zep have?", "fuzzy name",
     "Finds Led Zeppelin (14 albums) or says the name was not found"),
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

with open("reports/stress_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["question", "kind", "good_behavior", "generated_sql",
                "rows", "answer", "error", "verdict"])
    w.writerows(rows)
print("\nSaved reports/stress_results.csv")