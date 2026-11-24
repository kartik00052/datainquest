# Airflow demo DAGs

Each DAG in `dags/` fails on purpose and calls `_common/callbacks.py`, which posts to the
DagInquest API. Grow this folder into the 25-30 case failure-injection suite and add a
matching JSON case under `backend/src/daginquest/eval/cases/`.
