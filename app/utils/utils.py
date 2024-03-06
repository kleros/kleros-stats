from datetime import datetime
from typing import List, Literal, Dict
import pandas as pd
import numpy as np

from app.utils.subgraph import KlerosBoardSubgraph

chain_names: Dict[int, str] = {1: "mainnet", 100: "gnosis"}


def getActiveJurorsFromStakes(df: pd.DataFrame) -> pd.DataFrame:
    """from the setSakes dataframe (subgraph.getAllStakeSets()) get the list of
    all the active jurors

    inputs:
     - df: AllStakeSets dataframe
    outputs:
     - df: with the address, newTotalStake, timestamp of the last stake
    """
    # Get the last SetStake from each juror.
    active_jurors = df.groupby(by="address").last()
    # Drop the jurors who unstake
    active_jurors = active_jurors.loc[
        active_jurors["newTotalStake"] > 0, ["newTotalStake", "subcourtID", "timestamp"]
    ]
    return active_jurors


def getTimeSerieActiveJurorsFromStakes(df: pd.DataFrame) -> pd.DataFrame:
    """from the setSakes dataframe (subgraph.getAllStakeSets()) add a column
    with the count of active jurors.

    inputs:
     - df: AllStakeSets dataframe
    outputs:
     - df: the iput dataframe with an extra column called activeJurors
    """
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df.sort_values(by="timestamp", inplace=True)
    start_timestamp = df["timestamp"].min().replace(hour=0, second=0, minute=0)
    end_timestamp = df["timestamp"].max().replace(hour=0, second=0, minute=0)

    daily_dates: pd.DatetimeIndex = pd.date_range(
        start=start_timestamp,
        end=end_timestamp,
        freq="D",
    )

    active_juros: List = []
    for i, date in enumerate(daily_dates):
        # get the last newTotalStake by address and count only those who are > 0.
        # print(date)
        # print(df.loc[df["timestamp"] < date][['address', 'newTotalStake']])

        active_juros.append(
            df.loc[df["timestamp"] < date]
            .groupby(by="address")["newTotalStake"]
            .last()
            .astype(bool)
            .sum(axis=0)
        )
        # print(active_juros[-1])
    return pd.DataFrame(data={"active_jurors": active_juros}, index=daily_dates)


def getTimeSerieActiveJurors(
    chain: Literal["mainnet", "gnosis"] = "mainnet", freq: Literal["D", "W", "M"] = "D"
) -> pd.DataFrame:
    """Get the time serie of active jurors count"""
    kb = KlerosBoardSubgraph(network=chain)
    stakes: List = kb.getAllStakeSets()
    df_stakes = pd.DataFrame(stakes)
    active_jurors: pd.DataFrame = getTimeSerieActiveJurorsFromStakes(df_stakes)
    return active_jurors


def getTimeSeriePNKStakedFromStakes(df: pd.DataFrame, freq="M") -> pd.DataFrame:
    """from the setSakes dataframe (subgraph.getAllStakeSets()) generate
    a time serie with the total PNK staked.

    inputs:
     - df: AllStakeSets dataframe
    outputs:
     - df: a column of total_staked by time in frequency
    """
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df.sort_values(by="timestamp", inplace=True)
    start_timestamp = df["timestamp"].min().replace(hour=0, second=0, minute=0)
    end_timestamp = df["timestamp"].max().replace(hour=0, second=0, minute=0)

    dates: pd.DatetimeIndex = pd.date_range(
        start=start_timestamp,
        end=end_timestamp,
        freq=freq,
    )

    total_pnk = []
    for date in dates:
        # get the last newTotalStake by address and sum them
        total_pnk.append(
            df.loc[df["timestamp"] < date]
            .groupby(by="address")["newTotalStake"]
            .last()
            .sum()
        )
        # print(active_juros[-1])

    return pd.DataFrame(data={"total_staked": total_pnk}, index=dates)


def getTimeSeriePNKStaked(
    chain: Literal["mainnet", "gnosis"] = "mainnet", freq="M"
) -> pd.DataFrame:
    """a time serie with the total PNK staked.

    inputs:
     - df: AllStakeSets dataframe
    outputs:
     - df: a column of total_staked by time in frequency
    """
    kb = KlerosBoardSubgraph(network=chain)
    df = pd.DataFrame(data=kb.getAllStakeSets())
    return getTimeSeriePNKStakedFromStakes(df=df, freq=freq)


def getTimeSeriePNKStakedPercentage(
    chain: Literal["mainnet", "gnosis"] = "mainnet", freq="M"
) -> pd.DataFrame:
    """a time serie with the total PNK staked and percentage wrt to total supply

    inputs:
     - chain: string with mainnet or gnosis.
     - freq: string with D, W or M.
    outputs:
     - df: a dataframe with of total_staked, total_supply
           and percentege by time in frequency specified.
    """
    pnk_staked: pd.DataFrame = getTimeSeriePNKStaked(chain, freq)
    # TODO: Check history of total supply.
    pnk_staked["total_supply"] = 776626704
    pnk_staked.loc[
        pnk_staked.index < datetime(year=2024, month=1, day=20), "total_supply"
    ] -= 12000000  # mint kip66
    pnk_staked.loc[
        pnk_staked.index < datetime(year=2019, month=12, day=30), "total_supply"
    ] -= 200000000  # mint second token sale

    pnk_staked["percentage"] = pnk_staked["total_staked"] / pnk_staked["total_supply"]
    return pnk_staked


def gini(x, w=None) -> float:
    # The rest of the code requires numpy arrays.
    x = np.asarray(x)
    if w is not None:
        w = np.asarray(w)
        sorted_indices = np.argsort(x)
        sorted_x = x[sorted_indices]
        sorted_w = w[sorted_indices]
        # Force float dtype to avoid overflows
        cumw = np.cumsum(sorted_w, dtype=float)
        cumxw = np.cumsum(sorted_x * sorted_w, dtype=float)
        return np.sum(cumxw[1:] * cumw[:-1] - cumxw[:-1] * cumw[1:]) / (
            cumxw[-1] * cumw[-1]
        )
    else:
        sorted_x = np.sort(x)
        n = len(x)
        cumx = np.cumsum(sorted_x, dtype=float)
        # The above formula, with all weights equal to 1 simplifies to:
        return (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n
