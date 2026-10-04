from blocks._runner import run_cli  # delegates to subprocess via run_cli
def main(batch_date: str):
    run_cli(["python","-m","dbt.cli.main","deps","--profiles-dir","."],
            batch_date, "b05_dbt_deps", cwd="/home/code/dbt_project", timeout_s=600)
    run_cli(["python","-m","dbt.cli.main","run","--full-refresh","--profiles-dir","."],
            batch_date, "b05_dbt_run", cwd="/home/code/dbt_project", timeout_s=1200)
    run_cli(["python","-m","dbt.cli.main","test","--profiles-dir","."],
            batch_date, "b05_dbt_test", cwd="/home/code/dbt_project", timeout_s=1200)
