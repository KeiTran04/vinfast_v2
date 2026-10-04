from blocks._runner import run_cli  # delegates to subprocess via run_cli


def main(batch_date: str):
    run_cli(["python","-m","src.pipeline.cli","run","--source","entities","--date",batch_date],
            batch_date, "b02_entities", timeout_s=1800)
