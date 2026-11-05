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


def generate_sql(question, schema, bad_sql=None, error=None):
    """Ask the model for a SQL query (and a fixed one if the last one failed)."""
    prompt = (
        "You write SQLite queries for the database schema below.\n"
        "Rules: return ONE read-only SELECT statement (a WITH clause is allowed); "
        "use only tables and columns from the schema; add LIMIT 50 unless the query "
        "is an aggregate; return only the SQL, with no explanation.\n\n"
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


def explain(question, columns, rows):
    """Turn the query result into a short plain-English answer."""
    if not rows:
        return "The query ran, but it returned no rows."
    preview = [dict(zip(columns, r)) for r in rows[:20]]
    prompt = (
        "Answer the question in 1 to 3 plain sentences, using ONLY the query result "
        "below. Do not mention SQL. If the result is a long list, summarise it and "
        "name the top items.\n\n"
        f"Question: {question}\n"
        f"Result ({len(rows)} rows, first {len(preview)} shown): {preview}\n"
        "Answer:"
    )
    return generate(prompt).strip()


def ask(question, db_path=DB_PATH):
    """Question in; SQL, rows and a plain answer out."""
    schema = get_schema(db_path)
    sql, error = None, None
    for _ in range(2):
        sql = generate_sql(question, schema, sql, error)
        try:
            validate_sql(sql)
            columns, rows = run_query(sql, db_path)
            return {
                "question": question,
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "answer": explain(question, columns, rows),
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