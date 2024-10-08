import argparse
import logging
import os
import multiprocessing
from typing import cast
from zappai.zappai.utils.common import convert_nc_file_to_dataframe
from zappai import logging_conf

print(os.path.abspath(os.curdir))

def process_file(file_path: str, limit: int | None):
    csv_path = file_path + ".csv"
    logging.info(f"Converting {csv_path}")
    df = convert_nc_file_to_dataframe(source_file_path=file_path, limit=limit)
    df.to_csv(csv_path, index=False)

def main():
    # Create the ArgumentParser object
    parser = argparse.ArgumentParser(
        description="Process a file path and an optional limit."
    )

    # Add the file path argument
    parser.add_argument("--path", type=str, help="The path to the file.")

    # Add the limit argument
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        required=False,
        help="An optional limit on the number of items.",
    )

    # Parse the arguments
    args = parser.parse_args()

    path = cast(str, args.path)
    limit = cast(int | None, args.limit)

    files_to_process: list[str] = []

    if os.path.isdir(path):
        for file in os.listdir(path):
            if file.endswith(".nc"):
                full_path = os.path.join(path, file)
                files_to_process.append(full_path)
    else:
        files_to_process.append(path)

    num_cores = multiprocessing.cpu_count()
    with multiprocessing.Pool(processes=num_cores) as pool:
        pool.starmap(process_file, [(file, limit) for file in files_to_process])

if __name__ == "__main__":
    logging_conf.create_logger(config=logging_conf.get_default_conf())
    main()
