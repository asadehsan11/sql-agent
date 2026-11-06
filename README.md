# SQL Agent: Ask Your Database in Plain English

Type a question in plain English. The agent writes the SQL, runs it **read-only**, and explains the result. The generated query is always shown, so every answer can be checked.

**Live demo:** https://chat-with-sql-asad.streamlit.app/

**Demo video (2 min):** https://youtu.be/D2Pp_uYWgZI

![App screenshot](reports/demo.PNG)
![SQL and result](reports/sql.PNG)

## Business value

Most business questions ("Which country brings the most sales?") are stuck waiting for someone who knows SQL. This agent lets non-technical staff query a database themselves, while the visible SQL keeps answers auditable.

## How it works

1. The database schema and the date range of the data are placed in the prompt.
2. Gemini turns the question into one SQLite query. If the data to answer does not exist, it says so instead of guessing.
3. A validator checks the query before it runs.
4. The query runs on a read-only connection with a timeout and a row cap.
5. If the query fails, the error is sent back to the model for one retry.
6. Gemini explains the result in plain English and states how vague terms ("best", "popular") were measured.
7. Every question is logged (question, SQL, rows, latency, error).

## Safety design

- Requests that ask to change data ("Delete all customers") are refused up front, before reaching the LLM.
- Only a single `SELECT` or `WITH` statement is allowed. Forbidden keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `PRAGMA`, `ATTACH`, ...) are blocked, and keywords inside string literals are handled correctly.
- The database is opened in read-only mode (`mode=ro`), so even a query that slipped past the validator cannot change data.
- 5-second query timeout and a 100-row result cap.
- Covered by automated tests: `python -m tests.test_safety`

## Results

Three tests, each against the real database. The first two are in `run_eval.py` and `run_stress.py`, the third in `run_unseen.py`. Raw outputs are in `reports/`.

| Test | What it checks | Result |
|---|---|---|
| Core test: 10 clear questions with known answers | Result matches a hand-written reference query | 10/10 in 4 consecutive runs of the final prompts |
| Stress test: 8 ambiguous or unanswerable questions (used to improve the prompt) | Agent states its assumption or says the data can't answer | Before fixes: 4 good, 2 partial, 2 wrong. After fixes: 7 to 8 of 8 good across runs |
| Unseen test: 8 new questions, not used to tune anything | Same, plus a NULL trap and an empty result | First run: 6 good, 2 partial (wording), 0 wrong |

What the stress test found: the first version answered "Zero employees quit last year" and returned the average *price* when asked for the average *rating*. Both were confident and wrong. Adding a "cannot answer" path and the data's date range to the prompt fixed these cases.

Results vary a little between runs because LLM output is not deterministic. In one rerun of the unseen test, the agent refused "What is the most expensive album?" even though it had answered it before.

## Limitations

- The test sets are small (26 questions in total). The stress set was used to improve the prompt, so its score is optimistic. The unseen set is the fairer number.
- Run-to-run variation: the same question can get a slightly different query or wording, and occasionally a refusal where an answer was possible.
- When several items tie for first place (for example popular tracks), the agent may show a ranked list or a single item. Check the SQL.
- Some "can't answer" messages contain awkward wording, such as a reference to a "data note".
- Built on Gemini's free tier: rate limits and occasional server overload. The app retries and falls back to other models, which can add a few seconds.
- Works on one database (Chinook, SQLite) with the schema in the prompt. Very large schemas would need schema retrieval.
- The plain-English explanation is written by an LLM; the SQL and table are the source of truth.
- The query log is stored locally and is not persistent on the free hosting.

## Run locally

```bash
git clone https://github.com/asadehsan11/sql-agent.git
cd sql-agent
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file with `GEMINI_API_KEY=your_key`, then:

```bash
streamlit run app.py
```

Run the tests:

```bash
python -m tests.test_safety
python run_eval.py
python run_stress.py
python run_unseen.py
```

## Tech stack

Python, Streamlit, Google Gemini (`google-genai`), SQLite, pandas.

## Data

[Chinook sample database](https://github.com/lerocha/chinook-database): a digital music store with artists, albums, tracks, customers and invoices.

---
Built by [Asad Ehsan](https://github.com/asadehsan11)