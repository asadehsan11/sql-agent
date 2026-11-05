"""Ask the SQL agent and log every call."""
import time

from src.db import log_query
from src.sql_agent import ask


def ask_and_log(question):
    start = time.time()
    result = ask(question)
    log_query(
        question,
        result["sql"],
        len(result["rows"]),
        result["error"],
        round(time.time() - start, 2),
    )
    return result