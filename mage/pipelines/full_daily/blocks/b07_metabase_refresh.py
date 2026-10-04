from blocks._runner import run_cli
def main(batch_date: str):
    run_cli(["python","metabase/setup_dashboards.py","--refresh-only"],
            batch_date, "b07_refresh", timeout_s=600)
