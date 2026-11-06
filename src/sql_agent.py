"""Natural language to SQL agent for a SQLite database."""
import re
import sqlite3
import time

from src.llm import generate

DB_PATH = "data/chinook.sqlite"
MAX_ROWS = 100
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b",
    re.IGNORECASE,
)


def _connect(db_path):
    """Open the database in read-only mode."""
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def get_schema(db_path=DB_PATH):
    """Return the CREATE TABLE statements, so the model knows the tables."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return "\n\n".join(r[0] for r in rows if r[0])


def get_data_note(db_path=DB_PATH):
    """Describe the date range of the data, so 'last year' is not read as today's year."""
    conn = _connect(db_path)
    try:
        lo, hi = conn.execute("SELECT MIN(InvoiceDate), MAX(InvoiceDate) FROM Invoice").fetchone()
    finally:
        conn.close()
    return (
        f"Invoice dates in this database run from {lo[:10]} to {hi[:10]}. "
        "This is historical data, not today's date."
    )


def clean_sql(text):
    """Remove code fences and a trailing semicolon from the model's reply."""
    text = re.sub(r"^```(?:sql)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return text.rstrip(";").strip()


def validate_sql(sql):
    """Allow a single read-only SELECT query and nothing else."""
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")
    without_text = re.sub(r"'[^']*'", "''", sql)
    if ";" in without_text:
        raise ValueError("Only one statement is allowed.")
    if FORBIDDEN.search(without_text):
        raise ValueError("The query contains a forbidden keyword.")


def run_query(sql, db_path=DB_PATH, timeout_s=5):
    """Run the query read-only, with a time limit and a row limit."""
    conn = _connect(db_path)
    start = time.time()
    conn.set_progress_handler(lambda: 1 if time.time() - start > timeout_s else 0, 10000)
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS)
        return columns, rows
    finally:
        conn.close()


def generate_sql(question, schema, bad_sql=None, error=None, data_note=""):
    """Ask the model for a SQL query (and a fixed one if the last one failed)."""
    prompt = (
        "You write SQLite queries for the database schema below.\n"
        "Rules:\n"
        "1. Return ONE read-only SELECT statement (a WITH clause is allowed), using only "
        "tables and columns from the schema. Add LIMIT 50 unless the query is an "
        "aggregate. Return only the SQL, with no explanation.\n"
        "2. If the question cannot be answered from this schema because the data does "
        "not exist (for example weather, ratings, resignations), do NOT guess and do NOT "
        "substitute a different column. Instead return exactly: "
        "CANNOT_ANSWER: <one short reason>\n"
        "3. If the question is vague (for example 'best customers' or 'popular tracks'), "
        "choose the most reasonable measure from the schema (total money spent, units "
        "sold) and, when ranking, add the name as a second ORDER BY so ties are stable.\n"
        "4. Relative dates such as 'last year' or 'this month' must NOT use today's "
        "date. Use the most recent period that exists in the data.\n"
        "5. If the question uses a singular noun (for example 'the longest track' or "
        "'which genre has the most'), use LIMIT 1. If it uses a plural (for example "
        "'tracks', 'customers'), return a ranked list: use the number the user gave, "
        "otherwise LIMIT 10.\n\n"
        "date. Use the most recent period that exists in the data.\n\n"
        f"Data note: {data_note}\n\n"
        f"Schema:\n{schema}\n\n"
        f"Question: {question}\n"
    )
    if bad_sql:
        prompt += (
            f"\nYour previous query failed.\nQuery: {bad_sql}\nError: {error}\n"
            "Write a corrected query.\n"
        )
    prompt += "SQL:"
    return clean_sql(generate(prompt))


def explain(question, columns, rows, sql="", data_note=""):
    """Turn the query result into a short plain-English answer."""
    uses_dates = any(w in sql.lower() for w in ("date", "strftime", "year"))
    if not rows or all(v is None for r in rows for v in r):
        note = f" {data_note}" if uses_dates else ""
        return f"The query ran, but no matching rows were found.{note}"
    preview = [dict(zip(columns, r)) for r in rows[:20]]
    prompt = (
        "Answer the question in 1 to 3 plain sentences, using ONLY the query result "
        "below. Do not quote SQL. If the question was vague, say in a few words which "
        "measure the query used, using the question's own wording (for example: "
        "'Price was measured as the total of the track prices'). If several items are "
        "tied at the cutoff, mention the tie. If the question used a relative date "
        "like 'last year', say which actual year was used. If the result is a long "
        "list, summarise it and name the top items.\n\n"
        f"Data note: {data_note}\n"
        f"Query used: {sql}\n"
        f"Question: {question}\n"
        f"Result ({len(rows)} rows, first {len(preview)} shown): {preview}\n"
        "Answer:"
    )
    return generate(prompt).strip()
def ask(question, db_path=DB_PATH):
    """Question in; SQL, rows and a plain answer out."""
    schema = get_schema(db_path)
    data_note = get_data_note(db_path)
    sql, error = None, None
    for _ in range(2):
        sql = generate_sql(question, schema, sql, error, data_note)
        if sql.upper().startswith("CANNOT_ANSWER"):
            reason = sql.split(":", 1)[1].strip() if ":" in sql else "the data is not available."
            return {
                "question": question,
                "sql": "",
                "columns": [],
                "rows": [],
                "answer": f"This database can't answer that: {reason}",
                "error": None,
                "unanswerable": True,
            }
        try:
            validate_sql(sql)
            columns, rows = run_query(sql, db_path)
            return {
                "question": question,
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "answer": explain(question, columns, rows, sql, data_note),
                "error": None,
            }
        except (ValueError, sqlite3.Error) as e:
            error = str(e)
    return {
        "question": question,
        "sql": sql,
        "columns": [],
        "rows": [],
        "answer": "",
        "error": error,
    }


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "How many tracks are in the database?"
    result = ask(q)
    print("SQL:", result["sql"])
    print("Error:", result["error"])
    print("Rows:", result["rows"][:5])
    print("Answer:", result["answer"])