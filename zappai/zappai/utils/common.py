import asyncio
import logging
from multiprocessing import Process
import multiprocessing
import random
import traceback
from typing import Any, Callable, TypeVar
import pandas as pd
import os

from io import BytesIO
import joblib
import time

# Policoro
EXAMPLE_LOCATION_COUNTRY = "Italy"
EXAMPLE_LOCATION_NAME = "Policoro"
EXAMPLE_LONGITUDE = 16.678341
EXAMPLE_LATITUDE = 40.212971

T = TypeVar("T")

def retry_on_error(max_retries: int, wait_time: float):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        raise e
                    logging.error(e)
                    logging.error(traceback.format_exc())
                    time.sleep(wait_time)
        return wrapper
    return decorator

def create_stats_dataframe(df: pd.DataFrame, ignore: list[str]) -> pd.DataFrame:
    stats = ["mean", "std", "min", "max"]
    original_columns = list(df.columns)
    climate_data_stats = df.agg(
        {column: stats for column in original_columns},  # type: ignore
        axis=0,
    )  # type: ignore
    result_df = pd.DataFrame()
    for column in original_columns:
        if column in ignore:
            continue
        for stat in stats:
            result_df[f"{column}_{stat}"] = [
                climate_data_stats.loc[stat][column]
            ]
    return result_df


def bytes_to_object(bts: bytes) -> Any:
    bytes_io = BytesIO(initial_bytes=bts)
    return joblib.load(filename=bytes_io)


def object_to_bytes(obj: Any) -> bytes:
    bytes_io = BytesIO()
    joblib.dump(value=obj, filename=bytes_io)
    bytes_io.seek(0)
    return bytes_io.read()


def calc_months_delta(
    start_year: int, start_month: int, end_year: int, end_month: int
) -> int:
    result = (end_year - start_year) * 12
    result += end_month - start_month
    return result


def get_next_n_months(n: int, year: int, month: int) -> tuple[int, int]:
    """_summary_

    Args:
        n (int):
        year (int):
        month (int):

    Raises:
        ValueError:

    Returns:
        tuple[int, int]: year, month
    """
    if n < 1:
        raise ValueError(f"n can't be less than 1")

    result_month, result_year = month, year

    for _ in range(n):
        if result_month == 12:
            result_month = 1
            result_year += 1
            continue
        result_month += 1

    return result_year, result_month


def get_previous_n_months(n: int, month: int, year: int) -> tuple[int, int]:
    if n < 1:
        raise ValueError(f"n can't be less than 1")

    result_month, result_year = month, year

    for _ in range(n):
        if result_month == 1:
            result_month = 12
            result_year -= 1
            continue
        result_month -= 1

    return result_month, result_year


def coordinates_to_well_known_text(longitude: float, latitude: float) -> str:
    return f"POINT({longitude} {latitude})"

def convert_callback(source_file_path: str, limit: int | None):
    import xarray
    with xarray.open_dataset(source_file_path, mode="r") as ds:
        for name, index in ds.indexes.items():
            if isinstance(index, xarray.CFTimeIndex):
                ds[name] = index.to_datetimeindex()
        df = ds.to_dataframe()
    if limit is not None:
        df = df[:limit]
    df = df.reset_index()
    return df

def convert_nc_file_to_dataframe(
    source_file_path: str, limit: int | None
) -> pd.DataFrame:
    
    df = convert_callback(source_file_path=source_file_path, limit=limit)

    return df


def process_copernicus_climate_data(
    df: pd.DataFrame, is_cmip5_data: bool, columns_mappings: dict[str, str]
) -> pd.DataFrame:
    
    DATE_FORMAT = "mixed" if is_cmip5_data else "%Y%m%d"
    
    df = df.dropna()

    # Renaming columns
    df = df.rename(columns=columns_mappings)

    # Converting and extracting date parts
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], format=DATE_FORMAT)
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df = df.drop(columns=["date"])
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], format=DATE_FORMAT)
        df["year"] = df["time"].dt.year
        df["month"] = df["time"].dt.month
        df = df.drop(columns=["time"])
    else:
        raise KeyError("No time column found")

    # Resetting and setting index
    df = df.reset_index(drop=True)
    df = df.set_index(keys=["year", "month"])

    # Sorting index
    df = df.sort_index(ascending=[True, True])
    if "expver" in df.columns:

        df_expver1 = df[(df["expver"] == "0001") | (df["expver"] == 1)].drop(columns=["expver"])
        df_expver5 = df[(df["expver"] == "0005") | (df["expver"] == 5)].drop(columns=["expver"])
    
        df = df_expver1.combine_first(df_expver5)

    return df
