from typing import Dict, Literal

from web3 import Web3


class web3Node():
    def __init__(self, network: Literal['mainnet', 'gnosis'] = 'mainnet') -> None:
        self.network: Literal['mainnet', 'gnosis'] = network
        if self.network == 'gnosis':
            rpc_url = 'https://rpc.gnosischain.com'
        else:
            rpc_url = 'https://1rpc.io/eth'
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))

    def getTransaction(self, tx_hash) -> Dict:
        return self.web3.eth.get_transaction(tx_hash)

    def wei2eth(self, amount) -> float:
        return self.web3.from_wei(amount, 'ether')


class SmartContract(web3Node):
    def __init__(self, address, abi) -> None:
        super().__init__()
        self.contract = self.web3.eth.contract(abi=abi,
                                               address=address)
