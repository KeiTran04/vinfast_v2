import os
from blocks._runner import run_cli
def main(batch_date: str):
    base_url = os.environ.get("MB_BASE_URL", "http://metabase:3000")
    run_cli(["python", "metabase/setup_dashboards.py", "--base-url", base_url],
            batch_date, "b07_refresh", timeout_s=600)
