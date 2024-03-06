from typing import Dict, Literal

from web3 import Web3


class web3Node():
    def __init__(self, network:Literal['mainnet', 'gnosis']='mainnet') -> None:
        self.network: Literal['mainnet', 'gnosis'] = network
        if self.network == 'gnosis':
            rpc_url = 'https://rpc.ankr.com/gnosis'
        else:
            rpc_url = 'https://eth.llamarpc.com'
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))

    @classmethod
    def getTransaction(cls, tx_hash) -> Dict:
        return cls.web3.eth.getTransaction(tx_hash)

    def wei2eth(self, amount) -> float:
        return self.web3.fromWei(amount, 'ether')


class SmartContract(web3Node):
    def __init__(self, address, abi) -> None:
        self.contract = self.web3.eth.contract(abi=abi,
                                               address=address)
