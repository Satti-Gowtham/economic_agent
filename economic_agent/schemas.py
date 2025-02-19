import uuid
import logging
from eth_account import Account
from pydantic import BaseModel, Field
from typing import Union, Dict, Any, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class InputSchema(BaseModel):
    """Schema for agent input parameters"""
    func_name: str
    func_input_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]], str]] = None

class BaseWallet(BaseModel):
    chain: str
    address: Optional[str] = None
    private_key: Optional[str] = None

    def ensure_valid_wallet(self) -> None:
        if not self.private_key:
            account = Account.create()
            self.private_key = account.key.hex()
            self.address = account.address

    def sign_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "signed": True,
            "chain": self.chain,
            "address": self.address,
            "tx_data": tx_data
        }

class AgentWallet(BaseWallet):
    chain: str = "ethereum"

    def format_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a transaction for the Ethereum chain"""
        return {
            "from": self.address,
            "to": tx_data.get("to"),
            "value": tx_data.get("value", 0),
            "data": tx_data.get("data", "0x"),
            "chainId": 1,  # Mainnet
            "nonce": tx_data.get("nonce", 0),
            "gas": tx_data.get("gas", 21000),
            "maxFeePerGas": tx_data.get("maxFeePerGas", 20000000000),
            "maxPriorityFeePerGas": tx_data.get("maxPriorityFeePerGas", 1500000000)
        }
    
    def sign_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format and 'sign' an Ethereum transaction"""
        formatted_tx = self.format_transaction(tx_data)
        return {
            "signed": True,
            "chain": self.chain,
            "address": self.address,
            "tx_data": formatted_tx,
            "network": "ethereum",
            "chainId": 1,
            "status": "signed"
        }

class Transaction(BaseModel):
    """Model for a transaction record"""
    type: str
    symbol: str
    amount: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseHoldings(BaseModel):
    def record_transaction(self, tx: Dict[str, Any]) -> None:
        pass

    def get_total_value(
        self, 
        price_feeds: Optional[Dict[str, float]] = None,
        default_price: float = 0.0
    ) -> float:
        return 0.0

class Portfolio(BaseHoldings):
    token_balances: Dict[str, float] = Field(default_factory=dict)
    transaction_history: List[Dict[str, Any]] = Field(default_factory=list)

    def record_transaction(self, tx: Dict[str, Any]) -> None:
        # Record the transaction in history
        self.transaction_history.append(tx)
        
        # Update balances if symbol and amount are provided
        if "symbol" in tx and "amount" in tx:
            self.adjust_token_balance(tx["symbol"], float(tx["amount"]))

    def get_token_balance(self, symbol: str) -> float:
        return self.token_balances.get(symbol, 0.0)

    def adjust_token_balance(self, symbol: str, delta: float) -> None:
        current = self.token_balances.get(symbol, 0.0)
        self.token_balances[symbol] = current + delta

    def get_total_value(
        self,
        price_feeds: Optional[Dict[str, float]] = None,
        default_price: float = 0.0
    ) -> float:
        if not price_feeds:
            price_feeds = {}
        return sum(
            balance * price_feeds.get(symbol, default_price)
            for symbol, balance in self.token_balances.items()
        )

class EconomicAgent(BaseModel):
    """Economic agent that manages wallet, holdings, and rewards"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rewards: List[float] = Field(default_factory=list)
    total_reward: float = 0.0
    wallet: Optional[AgentWallet] = None
    holdings: Optional[Portfolio] = None

    def __init__(self, generate_wallet: bool = False, initial_holdings: Optional[Dict[str, float]] = None, **data):
        super().__init__(**data)
        if generate_wallet:
            self.wallet = AgentWallet(chain="ethereum")
            self.wallet.ensure_valid_wallet()
            self.holdings = Portfolio(token_balances=initial_holdings or {})

    def add_reward(self, reward: float) -> None:
        """Add a reward to the agent"""
        reward = float(reward)
        self.rewards.append(reward)
        self.total_reward += reward

    def add_transaction(self, tx: Dict[str, Any]) -> None:
        """Record a transaction in the agent's holdings"""
        if not self.holdings:
            return
        self.holdings.record_transaction(tx)
    
    def get_token_balance(self, symbol: str) -> float:
        """Get balance of a specific token"""
        if not self.holdings:
            return 0.0
        return self.holdings.get_token_balance(symbol)

    def get_portfolio_value(
        self, 
        price_feeds: Optional[Dict[str, float]] = None, 
        default_price: float = 0.0
    ) -> float:
        """Get total portfolio value"""
        if not self.holdings:
            return 0.0
        return self.holdings.get_total_value(price_feeds, default_price)

    def sign_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sign a transaction with the agent's wallet"""
        if not self.wallet:
            return {}
        return self.wallet.sign_transaction(tx_data)
