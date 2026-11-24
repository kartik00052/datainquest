from datetime import datetime

from airflow.sdk import dag, task
from _common.callbacks import notify_failure


@dag(
    dag_id="demo_import_error", schedule=None, start_date=datetime(2025, 1, 1), catchup=False,
    default_args={"retries": 0, "on_failure_callback": notify_failure}, tags=["daginquest-demo"],
)
def demo_import_error():
    @task
    def transform():
        import pandas_extras  # noqa: F401  (intentionally missing module)

    transform()


demo_import_error()
