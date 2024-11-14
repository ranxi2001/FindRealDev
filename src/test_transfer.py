import requests
import json
from config import Config
from utils import setup_logging

logger = setup_logging()

def get_transfer_info(signature: str):
    """获取单个交易的转账信息"""
    rpc_url = Config.QUICKNODE_RPC_URL
    headers = {"Content-Type": "application/json"}
    
    if Config.QUICKNODE_API_KEY:
        headers["Authorization"] = f"Bearer {Config.QUICKNODE_API_KEY}"
        
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0
            }
        ]
    }
    
    try:
        response = requests.post(rpc_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json().get('result', {})
        
        if not result or 'meta' not in result:
            print("未找到交易记录")
            return
            
        # 分析代币余额变化
        pre_balances = result['meta'].get('preTokenBalances', [])
        post_balances = result['meta'].get('postTokenBalances', [])
        
        if not pre_balances and not post_balances:
            print("该交易没有代币转账")
            return
            
        print("\n转账详情:")
        print("-" * 50)
        
        # 打印转账前余额
        for balance in pre_balances:
            print(f"转账前:")
            print(f"代币: {balance['mint']}")
            print(f"地址: {balance['owner']}")
            print(f"余额: {balance['uiTokenAmount']['uiAmountString']}")
            print()
            
        # 打印转账后余额
        for balance in post_balances:
            print(f"转账后:")
            print(f"代币: {balance['mint']}")
            print(f"地址: {balance['owner']}")
            print(f"余额: {balance['uiTokenAmount']['uiAmountString']}")
            print()
            
    except Exception as e:
        print(f"获取交易详情失败: {str(e)}")

if __name__ == "__main__":
    # 在这里输入要查询的签名
    signature = "4eLiHLXJWQA5YupP3XvwMuMPtc19jE2AhF2PKF7D9DdZVjgb1NsJ8aoD7o1tQYgXwsRvW8RE9MYUSxce9rMvDcAi"
    get_transfer_info(signature) 