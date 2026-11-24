from datetime import datetime

from airflow.sdk import dag, task
from _common.callbacks import notify_failure


@dag(
    dag_id="demo_bad_sql", schedule=None, start_date=datetime(2025, 1, 1), catchup=False,
    default_args={"retries": 0, "on_failure_callback": notify_failure}, tags=["daginquest-demo"],
)
def demo_bad_sql():
    @task
    def daily_revenue():
        raise RuntimeError('column "amount_usd" does not exist\nLINE 1: SELECT amount_usd FROM sales')

    daily_revenue()


demo_bad_sql()
