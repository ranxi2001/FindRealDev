import json
import pandas as pd
from typing import Dict, Optional
from utils import setup_logging
from config import Config
import requests

logger = setup_logging()

class TransactionParser:
    def __init__(self):
        self.rpc_url = Config.QUICKNODE_RPC_URL
        self.headers = {
            "Content-Type": "application/json"
        }
        if Config.QUICKNODE_API_KEY:
            self.headers["Authorization"] = f"Bearer {Config.QUICKNODE_API_KEY}"

    def _make_rpc_request(self, signature: str) -> Dict:
        """获取单个交易的详细信息"""
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
            response = requests.post(
                self.rpc_url, 
                headers=self.headers, 
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get('result', {})
        except Exception as e:
            logger.error(f"获取交易详情失败: {str(e)}")
            return {}

    def parse_transaction(self, txn: Dict) -> Optional[Dict]:
        """解析单个交易的转账信息"""
        if not txn or 'meta' not in txn:
            return None
            
        try:
            # 保存原始交易数据，方便调试
            with open('debug_single_transaction.json', 'w') as f:
                json.dump(txn, f, indent=2)
            
            # 从 token balances 中分析转账
            pre_balances = {
                b['accountIndex']: b for b in txn['meta'].get('preTokenBalances', [])
            }
            post_balances = {
                b['accountIndex']: b for b in txn['meta'].get('postTokenBalances', [])
            }
            
            transfers = []
            # 分析余额变化找到真实的接收方
            for account_index in set(pre_balances.keys()) | set(post_balances.keys()):
                pre_amount = float(pre_balances.get(account_index, {}).get('uiTokenAmount', {}).get('uiAmountString', '0') or '0')
                post_amount = float(post_balances.get(account_index, {}).get('uiTokenAmount', {}).get('uiAmountString', '0') or '0')
                
                if post_amount != pre_amount:  # 余额有变化
                    token = post_balances.get(account_index, pre_balances.get(account_index, {}))
                    transfers.append({
                        "accountIndex": account_index,
                        "token": token,
                        "amount": post_amount - pre_amount
                    })
            
            return {
                "transfers": transfers
            }
        except Exception as e:
            logger.error(f"解析交易失败: {str(e)}")
            return None 