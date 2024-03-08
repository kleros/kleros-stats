from datetime import datetime, timedelta
from typing import Union, List, Literal, Dict
import pandas as pd
import numpy as np
from app.utils.oracles import CoinGecko

from app.utils.subgraph import KlerosBoardSubgraph

chain_names: Dict[int, str] = {1: "mainnet", 100: "gnosis"}

# https://etherscan.io/advanced-filter?tkn=0x93ed3fbe21207ec2e8f2d3c3de6e058cb73bc04d&txntype=2&fadd=0x0000000000000000000000000000000000000000
minting_events: List[Dict[str, Union[datetime, float]]] = [
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=53, second=7), 'amount': 80_000_000},
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=53, second=59), 'amount': 40_000_000},
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=54, second=28), 'amount': 20_000_000},
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=55, second=39), 'amount': 10_000_000},
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=55, second=39), 'amount': 15_000_000},
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=56, second=26), 'amount': 5_000_000},
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=56, second=56), 'amount': 5_000_000},
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=57, second=14), 'amount': 3_000_000},
    {'timestamp': datetime(year=2018, month=3, day=15, hour=16, minute=58, second=32), 'amount': 2_000_000},
    {'timestamp': datetime(year=2018, month=4, day=6, hour=14, minute=14, second=46), 'amount': 1_000_000},
    {'timestamp': datetime(year=2018, month=5, day=9, hour=3, minute=39, second=30), 'amount': 15_000_000},
    {'timestamp': datetime(year=2018, month=5, day=14, hour=4, minute=30, second=9), 'amount': 160_000_000},
    {'timestamp': datetime(year=2018, month=5, day=18, hour=18, minute=15, second=6), 'amount': 5_000_000},
    {'timestamp': datetime(year=2018, month=7, day=16, hour=17, minute=13, second=4), 'amount': 230_208},
    {'timestamp': datetime(year=2018, month=7, day=16, hour=17, minute=20, second=29), 'amount': 3_110_000},
    {'timestamp': datetime(year=2018, month=7, day=17, hour=17, minute=21, second=15), 'amount': 19_621},
    {'timestamp': datetime(year=2018, month=7, day=28, hour=22, minute=46, second=54), 'amount': 256_875},
    {'timestamp': datetime(year=2018, month=8, day=2, hour=20, minute=35, second=21), 'amount': 10_000},
    {'timestamp': datetime(year=2018, month=11, day=12, hour=20, minute=28, second=12), 'amount': 10_000_000},
    {'timestamp': datetime(year=2019, month=3, day=26, hour=17, minute=26, second=38), 'amount': 25_000_000},
    {'timestamp': datetime(year=2020, month=1, day=10, hour=14, minute=21, second=0), 'amount': 150_000_000},
    {'timestamp': datetime(year=2020, month=2, day=2, hour=14, minute=54, second=36), 'amount': 50_000_000},
    {'timestamp': datetime(year=2020, month=6, day=10, hour=16, minute=2, second=31), 'amount': 200_000_000},
    {'timestamp': datetime(year=2024, month=2, day=22, hour=13, minute=33, second=47), 'amount': 12_000_000},
]

# https://etherscan.io/advanced-filter?tkn=0x93ed3fbe21207ec2e8f2d3c3de6e058cb73bc04d&txntype=2&tadd=0x0000000000000000000000000000000000000000
burning_events: List[Dict[str, Union[datetime, float]]] = [
    {'timestamp': datetime(year=2018, month=5, day=6, hour=16, minute=10, second=34), 'amount': -15_000_000},
    {'timestamp': datetime(year=2018, month=5, day=7, hour=22, minute=22, second=34), 'amount': -15_000_000},
    {'timestamp': datetime(year=2018, month=5, day=18, hour=18, minute=13, second=59), 'amount': -5_000_000},
]

def getTotalSupplyTimeSerie(freq: Literal['D', 'W', 'M']) -> pd.DataFrame:
    minting_events.extend(burning_events)
    df = pd.DataFrame(data=minting_events)
    df.sort_values(by='timestamp', ascending=True, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['total_supply'] = df['amount'].cumsum()
    resampled: pd.DataFrame = df.resample(rule=freq, on='timestamp')['total_supply'].last().fillna(method='ffill')
    start_date = resampled.index.min()
    end_date = datetime.now()
    t_index = pd.DatetimeIndex(pd.date_range(start=start_date, end=end_date, freq=freq))
    return resampled.reindex(t_index).fillna(method='ffill')


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

    total_supply = getTotalSupplyTimeSerie(freq=freq)
    pnk_staked['total_supply'] = total_supply.reindex(pnk_staked.index).fillna(method='ffill')

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


def getHistoryFees(chain: Literal['mainnet', 'gnosis'], freq: Literal['D', 'W', 'M'] = 'M') -> pd.DataFrame:
    # Get all paymens to jurors
    kb = KlerosBoardSubgraph(network=chain)
    transfers = pd.DataFrame(kb.getAllTransfers())
    transfers['timestamp'] = pd.to_datetime(transfers.timestamp, unit='s')
    transfers.sort_values('timestamp', inplace=True)
    transfers = transfers.resample(rule='D', on='timestamp')['ETHAmount'].sum()
    if chain == 'mainnet':
        # get ETH price
        days_before = (datetime.now() - transfers.index.min()).days
        eth_price = CoinGecko().getETHhistoricPrice(days_before)
        eth_price = pd.DataFrame(eth_price, columns=['timestamp', 'price'])
        eth_price['timestamp'] = pd.to_datetime(eth_price['timestamp'], unit='ms')
        transfers_eth_price = pd.merge_asof(
            left=transfers, right=eth_price,
            left_index=True, right_on='timestamp',
            direction='forward', tolerance=timedelta(hours=23)
        )
        transfers_eth_price['ETHAmount_usd'] = transfers_eth_price['ETHAmount'] * transfers_eth_price['price']
    elif chain == 'gnosis':
        # xDAI is already in USD.
        transfers_eth_price = pd.DataFrame(transfers)
        transfers_eth_price['ETHAmount_usd'] = transfers_eth_price['ETHAmount']
    transfers_eth_price = transfers_eth_price.resample(rule=freq)['ETHAmount_usd', 'ETHAmount'].sum()
    return transfers_eth_price