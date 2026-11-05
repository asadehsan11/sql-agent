"""Accuracy test: compare agent's result with a hand-written correct query."""
import csv
from itertools import permutations
import time

from src.sql_agent import ask, run_query

TESTS = [
    ("How many tracks are there?",
     "SELECT COUNT(*) FROM Track"),
    ("How many customers are there?",
     "SELECT COUNT(*) FROM Customer"),
    ("Which genre has the most tracks?",
     "SELECT g.Name FROM Genre g JOIN Track t ON t.GenreId=g.GenreId "
     "GROUP BY g.GenreId ORDER BY COUNT(*) DESC LIMIT 1"),
    ("Which 5 artists have the most albums?",
     "SELECT ar.Name FROM Artist ar JOIN Album al ON al.ArtistId=ar.ArtistId "
     "GROUP BY ar.ArtistId ORDER BY COUNT(*) DESC, ar.Name LIMIT 5"),
    ("What is the total sales amount of all invoices?",
     "SELECT ROUND(SUM(Total),2) FROM Invoice"),
    ("Which country has the highest total sales?",
     "SELECT BillingCountry FROM Invoice GROUP BY BillingCountry "
     "ORDER BY SUM(Total) DESC LIMIT 1"),
    ("How many invoices were issued in 2010?",
     "SELECT COUNT(*) FROM Invoice WHERE strftime('%Y', InvoiceDate)='2010'"),
    ("What is the longest track by duration? Give its name.",
     "SELECT Name FROM Track ORDER BY Milliseconds DESC LIMIT 1"),
    ("How many employees are there?",
     "SELECT COUNT(*) FROM Employee"),
    ("How many albums does the artist Led Zeppelin have?",
     "SELECT COUNT(*) FROM Album al JOIN Artist ar ON ar.ArtistId=al.ArtistId "
     "WHERE ar.Name='Led Zeppelin'"),
]


def norm(rows):
    """Compare values only, ignoring column names and float noise."""
    out = []
    for r in rows:
        out.append(tuple(round(v, 2) if isinstance(v, float) else v for v in r))
    return out

def matches(got, gold):
    """True if the gold columns appear (in order of rows) among the agent's columns."""
    if not gold:
        return got == gold
    k = len(gold[0])
    if not got or len(got[0]) < k or len(got) != len(gold):
        return False
    for cols in permutations(range(len(got[0])), k):
        if [tuple(r[c] for c in cols) for r in got] == gold:
            return True
    return False

results = []
for q, gold_sql in TESTS:
    gold = norm(run_query(gold_sql)[1])
    t = time.time()
    res = ask(q)
    took = round(time.time() - t, 1)
    got = norm(res["rows"]) if not res["error"] else []
    ok = matches(got, gold)
    print(("PASS" if ok else "FAIL"), "|", q, f"({took}s)")
    if not ok:
        print("   expected:", gold[:5])
        print("   got     :", got[:5], res["error"] or "")
        print("   sql     :", res["sql"])
    results.append((q, ok, took, res["sql"]))
    time.sleep(5)  # stay under the free-tier rate limit

passed = sum(r[1] for r in results)
print(f"\nAccuracy: {passed}/{len(results)} = {passed/len(results):.0%}")

with open("reports/eval_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["question", "correct", "seconds", "generated_sql"])
    w.writerows(results)