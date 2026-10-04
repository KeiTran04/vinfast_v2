from blocks._runner import run_cli  # delegates to subprocess via run_cli


def main(batch_date: str):
    run_cli(["python","-m","src.data_generator.cli","generate","--start-date",batch_date,
             "--end-date",batch_date,"--seed","42"], batch_date, "b01_generate", timeout_s=1200)
    run_cli(["python","-m","src.data_generator.cli","mock-raw","--source","all","--seed","42"],
            batch_date, "b01_mock", timeout_s=1200)
