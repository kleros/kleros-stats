from flask import Flask, jsonify, request, Response
from flask_swagger_ui import get_swaggerui_blueprint
import pandas as pd

from utils.subgraph import KlerosBoardSubgraph
from utils.utils import getTimeSerieActiveJurors, chain_names, getTimeSeriePNKStakedPercentage
from utils.oracles import CoinGecko
from datetime import datetime, timedelta

app = Flask(import_name=__name__)
SWAGGER_URL = "/doc"
API_URL = "/static/swagger.yml"

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL, API_URL, config={"app_name": "Kleros Stats"}
)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)


@app.route("/status")
def home() -> Response:
    return jsonify({"Message": "API up and running"})


@app.route("/counters/<int:chainId>", methods=["GET"])
def get_counters(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    kb = KlerosBoardSubgraph(chain)
    counters = kb.getKlerosCounters()
    return jsonify({"data": counters})

@app.route("/history/active-jurors/<int:chainId>", methods=["GET"])
def get_history_active_jurors(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    active_jurors: pd.DataFrame = getTimeSerieActiveJurors()
    return jsonify({"data": active_jurors.to_json()})


@app.route("/history/growth-active-jurors/<int:chainId>", methods=["GET"])
def get_history_growth_active_jurors(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    freq: str = request.args.get(key='freq', default='M')

    active_jurors: pd.DataFrame = getTimeSerieActiveJurors(chain=chain)
    growth: pd.DataFrame = active_jurors.diff()
    growth = growth.resample(freq).sum()

    return jsonify({"data": growth.to_json()})


@app.route("/history/transactions/<int:chainId>", methods=["GET"])
def get_history_transactions(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    freq: str = request.args.get(key='freq', default='M')

    kb = KlerosBoardSubgraph(chain)
    txs: pd.DataFrame = kb.getAllTransactions()
    resampled_txs = txs.resample(freq, on='timestamp').count()

    return jsonify({"data": resampled_txs.to_json()})

@app.route("/history/fees/<int:chainId>", methods=["GET"])
def get_history_fees(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    freq: str = request.args.get(key='freq', default='M')

    # Get all paymens to jurors
    kb = KlerosBoardSubgraph(chain)
    transfers = pd.DataFrame(kb.getAllTransfers())
    transfers['timestamp'] = pd.to_datetime(transfers.timestamp, unit='s')
    transfers.sort_values('timestamp', inplace=True)
    # get ETH price
    days_before = (datetime.now() - transfers.timestamp.min()).days
    eth_price = CoinGecko().getETHhistoricPrice(days_before)
    eth_price = pd.DataFrame(eth_price, columns=['timestamp', 'price'])
    eth_price['timestamp'] = pd.to_datetime(eth_price['timestamp'], unit='ms')
    transfers_eth_price = pd.merge_asof(
        left=transfers, right=eth_price,
        on='timestamp', direction='forward', tolerance=timedelta(hours=23)
    )
    transfers_eth_price['ETHAmount_usd'] = transfers_eth_price['ETHAmount'] * transfers_eth_price['price']

    if freq != 'D':
        transfers_eth_price = transfers_eth_price.resample('M', on='timestamp')['ETHAmount_usd', 'ETHAmount'].sum()

    return jsonify({"data": transfers_eth_price.to_json()})


@app.route("/history/cases/<int:chainId>", methods=["GET"])
def get_history_cases(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    freq: str = request.args.get(key='freq', default='M')

    kb = KlerosBoardSubgraph(chain)
    df_disputes = pd.DataFrame(data=kb.getAllDisputes())
    df_disputes['startTime'] = pd.to_datetime(df_disputes['startTime'], unit='s')
    df_disputes.sort_values(by='startTime', ascending=True, inplace=True)
    df_disputes: pd.DataFrame = df_disputes[['id', 'startTime']].resample(rule=freq, on='startTime').count()
    df_disputes.rename(columns={'id': 'cases'}, inplace=True)
    return jsonify({"data": df_disputes.to_json()})


@app.route("/history/staked-percentage/<int:chainId>", methods=["GET"])
def get_history_staked_percentage(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    freq: str = request.args.get(key='freq', default='M')

    df: pd.DataFrame = getTimeSeriePNKStakedPercentage(chain, freq)
    return jsonify({"data": df.to_json()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
