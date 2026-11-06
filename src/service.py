"""Ask the SQL agent and log every call."""
import re
import time

from src.db import log_query
from src.sql_agent import ask

# Requests that try to change data are refused before reaching the LLM.
WRITE_INTENT = re.compile(
    r"^\s*(?:(?:please|kindly|can you|could you|would you)\s+)*"
    r"(delete|drop|remove|update|insert|alter|truncate|erase|modify)\b",
    re.IGNORECASE,
)


def ask_and_log(question):
    start = time.time()
    if WRITE_INTENT.match(question):
        result = {
            "question": question,
            "sql": "",
            "columns": [],
            "rows": [],
            "answer": "",
            "error": None,
            "blocked": True,
        }
        log_query(question, "", 0, "blocked: write request", round(time.time() - start, 2))
        return result

    result = ask(question)
    log_query(
        question,
        result["sql"],
        len(result["rows"]),
        result["error"],
        round(time.time() - start, 2),
    )
    return result