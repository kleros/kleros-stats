import pandas as pd
import numpy as np


def getTimeSerieActiveJurors(df: pd.DataFrame)-> pd.DataFrame:
    """from the setSakes dataframe (subgraph.getAllStakeSets()) add a column
    with the count of active jurors.
    
    inputs:
     - df: AllStakeSets dataframe
    outputs:
     - df: the iput dataframe with an extra column called activeJurors
    """
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
    df.sort_values(by="timestamp", inplace=True)
    start_timestamp= df["timestamp"].min().replace(hour=0, second=0, minute=0)
    end_timestamp= df["timestamp"].max().replace(hour=0, second=0, minute=0)
    
    daily_dates: pd.DatetimeIndex = pd.date_range(
        start=start_timestamp,
        end=end_timestamp,
        freq='D',
    )

    active_juros = []
    for i, date in enumerate(daily_dates):
        # get the last newTotalStake by address and count only those who are > 0.
        # print(date)
        # print(df.loc[df["timestamp"] < date][['address', 'newTotalStake']])

        active_juros.append(
            df.loc[df["timestamp"] < date].groupby(by="address")["newTotalStake"].last().astype(bool).sum(axis=0)
        )
        # print(active_juros[-1])
    return pd.DataFrame(data={'active_jurors': active_juros}, index=daily_dates)



def getTimeSeriePNKStaked(df: pd.DataFrame, freq='M')-> pd.DataFrame:
    """from the setSakes dataframe (subgraph.getAllStakeSets()) generate
    a time serie with the total PNK staked.
    
    inputs:
     - df: AllStakeSets dataframe
    outputs:
     - df: a column of total_staked by time in frequency
    """
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
    df.sort_values(by="timestamp", inplace=True)
    start_timestamp= df["timestamp"].min().replace(hour=0, second=0, minute=0)
    end_timestamp= df["timestamp"].max().replace(hour=0, second=0, minute=0)
    
    dates: pd.DatetimeIndex = pd.date_range(
        start=start_timestamp,
        end=end_timestamp,
        freq=freq,
    )

    total_pnk = []
    for date in dates:
        # get the last newTotalStake by address and sum them
        total_pnk.append(
            df.loc[df["timestamp"] < date].groupby(by="address")["newTotalStake"].last().sum()
        )
        # print(active_juros[-1])

    return pd.DataFrame(data={'total_staked': total_pnk}, index=dates)


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
        return (np.sum(cumxw[1:] * cumw[:-1] - cumxw[:-1] * cumw[1:]) / 
                (cumxw[-1] * cumw[-1]))
    else:
        sorted_x = np.sort(x)
        n = len(x)
        cumx = np.cumsum(sorted_x, dtype=float)
        # The above formula, with all weights equal to 1 simplifies to:
        return (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n