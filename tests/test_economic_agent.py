import os
import json
import asyncio
from dotenv import load_dotenv
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.configs import setup_module_deployment
from naptha_sdk.user import sign_consumer_id
from economic_agent.run import run

load_dotenv()

naptha = Naptha()

def print_section(title):
    print("\n" + "-"*80)
    print(f"🔍 {title}".center(80))
    print("-"*80)

def print_result(title, result):
    print(f"\n📋 {title}:")
    print(json.dumps(result, indent=2))

async def setup_deployment():
    try:
        return await setup_module_deployment(
            "agent",
            "economic_agent/configs/deployment.json",
            node_url=os.getenv("NODE_URL")
        )
    except Exception as e:
        print("❌ Deployment Error:", str(e))
        return None

async def test_create_agent(deployment):
    print_section("Testing Agent Creation")
    create_input = {
        "inputs": {
            "func_name": "create",
            "func_input_data": {
                "initial_holdings": {
                    "ETH": 1.0,
                    "NAPTHA": 100.0,
                    "USDC": 1000.0,
                    "WBTC": 0.5
                }
            }
        },
        "deployment": deployment,
        "consumer_id": naptha.user.id,
        "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    }
    result = await run(create_input)
    print_result("Agent Creation Result", result)
    return result

async def test_rewards(deployment):
    print_section("Testing Reward System")
    
    rewards = [
        {"amount": 10.0, "symbol": "NAPTHA"},
        {"amount": 25.5, "symbol": "NAPTHA"},
        {"amount": 50.0, "symbol": "NAPTHA"}
    ]
    
    for reward in rewards:
        reward_input = {
            "inputs": {
                "func_name": "add_transaction",
                "func_input_data": {
                    "type": "reward",
                    "symbol": reward["symbol"],
                    "amount": reward["amount"]
                }
            },
            "deployment": deployment,
            "consumer_id": naptha.user.id,
            "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
        }
        result = await run(reward_input)
        print_result(f"Adding reward {reward['amount']} {reward['symbol']}", result)
        assert result["status"] == "success", "Failed to add reward"

async def test_portfolio_management(deployment):
    print_section("Testing Portfolio Management")
    
    transactions = [
        {"type": "deposit", "symbol": "ETH", "amount": 2.0},
        {"type": "trade", "symbol": "NAPTHA", "amount": 50.0},
        {"type": "trade", "symbol": "USDC", "amount": -500.0},
        {"type": "reward", "symbol": "WBTC", "amount": 0.1}
    ]

    for tx in transactions:
        tx_input = {
            "inputs": {
                "func_name": "add_transaction",
                "func_input_data": tx
            },
            "deployment": deployment,
            "consumer_id": naptha.user.id,
            "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
        }
        result = await run(tx_input)
        print_result(f"Transaction: {tx['type']} {tx['amount']} {tx['symbol']}", result)

    # Check balances
    for symbol in ["ETH", "NAPTHA", "USDC", "WBTC"]:
        balance_input = {
            "inputs": {
                "func_name": "get_token_balance",
                "func_input_data": {"symbol": symbol}
            },
            "deployment": deployment,
            "consumer_id": naptha.user.id,
            "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
        }
        result = await run(balance_input)
        print_result(f"Balance for {symbol}", result)

async def test_portfolio_valuation(deployment):
    print_section("Testing Portfolio Valuation")
    
    value_input = {
        "inputs": {
            "func_name": "get_portfolio_value",
            "func_input_data": {
                "price_feeds": {
                    "ETH": 2000.0,
                    "NAPTHA": 10.0,
                    "USDC": 1.0,
                    "WBTC": 40000.0
                },
                "default_price": 0.0
            }
        },
        "deployment": deployment,
        "consumer_id": naptha.user.id,
        "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    }
    result = await run(value_input)
    print_result("Portfolio Value with Price Feeds", result)

    value_input_no_prices = {
        "inputs": {
            "func_name": "get_portfolio_value",
            "func_input_data": {
                "default_price": 1.0
            }
        },
        "deployment": deployment,
        "consumer_id": naptha.user.id,
        "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
    }
    result = await run(value_input_no_prices)
    print_result("Portfolio Value with Default Price", result)

async def test_transaction_signing(deployment):
    print_section("Testing Transaction Signing")
    
    tx_types = [
        {
            "action": "transfer",
            "to": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "amount": 0.5,
            "symbol": "ETH",
            "gas_limit": 21000
        },
        {
            "action": "approve",
            "to": "0x1234567890123456789012345678901234567890",
            "amount": 50.0,
            "symbol": "NAPTHA",
            "gas_limit": 50000
        }
    ]

    for tx in tx_types:
        sign_input = {
            "inputs": {
                "func_name": "sign_transaction",
                "func_input_data": tx
            },
            "deployment": deployment,
            "consumer_id": naptha.user.id,
            "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
        }
        result = await run(sign_input)
        print_result(f"Signing {tx['action']} transaction", result)

async def test_error_handling(deployment):
    print_section("Testing Error Handling")
    
    error_cases = [
        {
            "name": "Invalid transaction type",
            "func_name": "add_transaction",
            "func_input_data": {
                "type": "invalid",
                "symbol": "NAPTHA",
                "amount": 100.0
            }
        },
        {
            "name": "Insufficient balance withdrawal",
            "func_name": "add_transaction",
            "func_input_data": {
                "type": "withdraw",
                "symbol": "NAPTHA",
                "amount": -1000.0
            }
        },
        {
            "name": "Missing transaction fields",
            "func_name": "add_transaction",
            "func_input_data": {
                "type": "deposit"
            }
        }
    ]

    for case in error_cases:
        error_input = {
            "inputs": {
                "func_name": case["func_name"],
                "func_input_data": case["func_input_data"]
            },
            "deployment": deployment,
            "consumer_id": naptha.user.id,
            "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
        }
        result = await run(error_input)
        print_result(f"Error case: {case['name']}", result)

async def verify_final_balances(deployment):
    print_section("Verifying Final Balances")
    for symbol in ["ETH", "NAPTHA", "USDC", "WBTC"]:
        balance_input = {
            "inputs": {
                "func_name": "get_token_balance",
                "func_input_data": {"symbol": symbol}
            },
            "deployment": deployment,
            "consumer_id": naptha.user.id,
            "signature": sign_consumer_id(naptha.user.id, os.getenv("PRIVATE_KEY"))
        }
        result = await run(balance_input)
        print_result(f"Final balance for {symbol}", result)

async def test_agent():
    print("\n" + "="*80)
    print("💰 Testing Economic Agent".center(80))
    print("="*80 + "\n")

    deployment = await setup_deployment()
    if not deployment:
        return

    await test_create_agent(deployment)
    await test_rewards(deployment)
    await test_portfolio_management(deployment)
    await test_portfolio_valuation(deployment)
    await test_transaction_signing(deployment)
    await test_error_handling(deployment)
    await verify_final_balances(deployment)

    print("\n" + "="*80)
    print("✨ Test Complete".center(80))
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_agent()) 