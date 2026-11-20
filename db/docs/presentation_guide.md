# Presentation and demonstration guide

The presentation is **individual** (40 marks): every member must be able to run
queries and explain every part. Practise the whole flow on your own laptop.
Remember the dress code in the brief (official and black; no jeans, T-shirts or
sleeveless tops) and that **all members must attend**.

## Suggested order (about 10 minutes each person can repeat any step)

| Step | What to show | File |
|---|---|---|
| 1 | The system in one sentence and the physical model | `docs/physical_model.png` |
| 2 | Normalization: from one flat form to 7 tables | `docs/normalization.md` |
| 3 | Tables and constraints: try to insert a bad phone number | `psql ... -c "\d permits"` |
| 4 | Basic queries: select, join, update, delete (inside ROLLBACK) | `queries/08_crud_queries.sql` |
| 5 | Analysis: GROUP BY/HAVING, subquery, CTE, window function | `queries/09_analysis_queries.sql` |
| 6 | Views | `SELECT * FROM v_expiring_soon;` |
| 7 | Indexes: before and after | `tests/index_demo.sql` |
| 8 | Functions and procedures: `CALL sp_decide_permit(...)` | `sql/04_...sql` |
| 9 | Triggers: show the refusals | `queries/triggers_demo.sql` |
| 10 | Transactions: ROLLBACK, COMMIT, SAVEPOINT | `queries/10_transactions_demo.sql` |
| 11 | The PyQt6 application: approve a permit, press History | `python main.py` |
| 12 | Run all tests | `tests/run_tests.sql` |

## Live examples you can type
```sql
-- how many permits in each status?
SELECT * FROM v_status_summary;

-- a bad change is refused by the trigger
UPDATE permits SET status = 'Under Review' WHERE permit_id = 'PRM-004';

-- an office decision using a stored procedure
CALL sp_decide_permit('PRM-013', 'Business Licensing Unit', 'approve');
SELECT permit_id, status, issue_date, expiry_date FROM permits WHERE permit_id = 'PRM-013';
SELECT note FROM permit_history WHERE permit_id = 'PRM-013' ORDER BY history_id;
```

## Questions you may be asked (and short answers)
* **Why 3NF?** Each fact is stored once, so a change (a fee, a phone number) is made in
  one place and cannot become inconsistent.
* **Why a junction table `office_permit_types`?** One office can handle several permit
  types and one type can be handled by several offices (many-to-many).
* **Why use triggers when Python already checks the rules?** The database protects the
  data even if a different program, or a person using `psql`, changes it.
* **What does `ON DELETE RESTRICT` do?** It refuses to delete an applicant who still
  has permits.
* **What is a partial index?** An index on only some rows (approved permits), so it is
  smaller and faster for the expiry query.
* **What does ROLLBACK do?** Cancels every change made since BEGIN, like pressing undo.
* **Function or procedure?** A function returns a value and can be used inside a query;
  a procedure is run with CALL and is used for actions (it can have OUT parameters).
* **How does Python connect?** `psycopg2` in `database.py`, with parameterised queries
  (`%s`) against SQL injection, and the password from environment variables.
