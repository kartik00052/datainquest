from datetime import datetime

from airflow.sdk import dag, task
from _common.callbacks import notify_failure


@dag(
    dag_id="demo_timeout", schedule=None, start_date=datetime(2025, 1, 1), catchup=False,
    default_args={"retries": 0, "on_failure_callback": notify_failure}, tags=["daginquest-demo"],
)
def demo_timeout():
    @task
    def fetch_from_sftp():
        raise TimeoutError("SFTP connection timed out after 30s")

    fetch_from_sftp()


demo_timeout()
