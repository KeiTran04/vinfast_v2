from blocks._runner import run_cli  # delegates to subprocess via run_cli
def main(batch_date: str):
    run_cli(["python","-m","src.pipeline.cli","run","--source","telemetry",
             "--source","charging_internal","--date",batch_date],
            batch_date, "b03_telemetry", timeout_s=2700)
