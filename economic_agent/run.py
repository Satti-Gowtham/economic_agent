from typing import Dict, Any
from naptha_sdk.schemas import AgentRunInput, AgentDeployment
from naptha_sdk.utils import get_logger
from economic_agent.schemas import (
    InputSchema,
    EconomicAgent
)

logger = get_logger(__name__)

class EconomicAgentModule:
    """Economic Agent module that interfaces with the agent through naptha-sdk"""
    
    def __init__(self, deployment: AgentDeployment, consumer_id: str):
        self.deployment = deployment
        self.consumer_id = consumer_id
        self.agent = EconomicAgent(generate_wallet=True)
    
    async def create(self, initial_holdings: Dict[str, float] = None) -> Dict[str, Any]:
        """Create and initialize the economic agent"""

        if initial_holdings:
            self.agent.holdings.token_balances.update(initial_holdings)
        return {
            "status": "success",
            "agent_id": self.agent.id,
            "wallet": self.agent.wallet.model_dump() if self.agent.wallet else None,
            "holdings": self.agent.holdings.model_dump() if self.agent.holdings else None
        }
    
    async def add_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """Record a transaction in the agent's holdings"""

        if not self.agent:
            return {"status": "error", "message": "Agent not initialized. Call create first."}
        
        if not tx or not isinstance(tx, dict) or not all(k in tx for k in ["type", "symbol", "amount"]):
            return {"status": "error", "message": "Invalid transaction data - must include type, symbol and amount"}
        
        if tx.get("type") not in ["withdraw", "reward", "deposit", "trade"]:
            return {
                "status": "error", 
                "message": "Invalid transaction type - only withdraw and deposit allowed",
                "transaction": tx
            }

        # Check if it's a withdrawal/trade and verify sufficient balance
        if tx.get("type") in ["withdraw", "trade"] and tx.get("amount", 0) < 0:
            symbol = tx.get("symbol")
            amount = abs(tx.get("amount", 0))
            current_balance = self.agent.get_token_balance(symbol)
            
            if current_balance < amount:
                return {
                    "status": "error",
                    "message": f"Insufficient {symbol} balance. Have {current_balance}, need {amount}",
                    "transaction": tx
                }
                
        self.agent.add_transaction(tx)
        return {"status": "success", "transaction": tx}
    
    async def get_token_balance(self, symbol: str) -> Dict[str, Any]:
        """Get balance of a specific token"""

        if not self.agent:
            return {"status": "error", "message": "Agent not initialized. Call create first."}
        
        balance = self.agent.get_token_balance(symbol)
        return {"status": "success", "symbol": symbol, "balance": balance}
    
    async def get_portfolio_value(
        self,
        price_feeds: Dict[str, float] = None,
        default_price: float = 0.0
    ) -> Dict[str, Any]:
        """Get total portfolio value"""

        if not self.agent:
            return {"status": "error", "message": "Agent not initialized. Call create first."}
        
        value = self.agent.get_portfolio_value(price_feeds, default_price)
        return {"status": "success", "value": value}
    
    async def sign_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sign a transaction with the agent's wallet"""

        if not self.agent:
            return {"status": "error", "message": "Agent not initialized. Call create first."}
        
        signed_tx = self.agent.sign_transaction(tx_data)
        if not signed_tx:
            return {"status": "error", "message": "Failed to sign transaction"}
        
        return {"status": "success", **signed_tx}

async def run(module_run: Dict[str, Any]) -> Dict[str, Any]:
    """Run the Economic Agent deployment"""
    
    try:
        module_run = AgentRunInput(**module_run)
        module_run.inputs = InputSchema(**module_run.inputs)
        
        # Use a class variable to store agent instances. Necessary for Naptha to handle state persistence
        if not hasattr(run, '_agents'):
            run._agents = {}
        
        # Get or create agent instance using consumer_id as key
        agent_key = module_run.consumer_id
        if agent_key not in run._agents:
            agent_module = EconomicAgentModule(module_run.deployment, module_run.consumer_id)
            run._agents[agent_key] = agent_module
        else:
            agent_module = run._agents[agent_key]
        
        method = getattr(agent_module, module_run.inputs.func_name)
        if not method:
            return {"status": "error", "message": f"Invalid function name: {module_run.inputs.func_name}"}
        
        func_input = module_run.inputs.func_input_data or {}
        
        match module_run.inputs.func_name:
            case "create":
                result = await method(func_input.get("initial_holdings"))
            case "add_transaction":
                result = await method(func_input)
            case "get_token_balance":
                result = await method(func_input.get("symbol"))
            case "get_portfolio_value":
                result = await method(
                    price_feeds=func_input.get("price_feeds"),
                    default_price=float(func_input.get("default_price", 0.0))
                )
            case _:
                result = await method(func_input)
            
        return result
    except Exception as e:
        logger.error(f"Error running economic agent: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import asyncio
    from tests.test_economic_agent import test_agent
    asyncio.run(test_agent())