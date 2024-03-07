from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
import pandas as pd

from app.utils.subgraph import KlerosBoardSubgraph
from app.utils.utils import getHistoryFees, getTimeSerieActiveJurors, chain_names, getTimeSeriePNKStakedPercentage

app = Flask(import_name=__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

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
    active_jurors: pd.DataFrame = getTimeSerieActiveJurors(chain=chain)
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

    kb = KlerosBoardSubgraph(network=chain)
    txs: pd.DataFrame = kb.getAllTransactions()
    resampled_txs = txs.resample(freq, on='timestamp').count()

    return jsonify({"data": resampled_txs.to_json()})

@app.route("/history/fees/<int:chainId>", methods=["GET"])
def get_history_fees(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    freq: str = request.args.get(key='freq', default='M')

    df: pd.DataFrame = getHistoryFees(chain, freq)
    return jsonify({"data": df.to_json()})


@app.route("/history/cases/<int:chainId>", methods=["GET"])
def get_history_cases(chainId: int) -> Response:
    chain: str = chain_names.get(chainId, None)
    if chain is None:
        return 'Chain not found', 400
    freq: str = request.args.get(key='freq', default='M')

    kb = KlerosBoardSubgraph(network=chain)
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
