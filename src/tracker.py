import requests
import json
import pandas as pd
from typing import List, Dict, Optional
from utils import is_valid_solana_address, setup_logging
from config import Config

logger = setup_logging()

class WalletTracker:
    def __init__(self):
        self.rpc_url = Config.QUICKNODE_RPC_URL
        self.headers = {
            "Content-Type": "application/json"
        }
        if Config.QUICKNODE_API_KEY:
            self.headers["Authorization"] = f"Bearer {Config.QUICKNODE_API_KEY}"

    def _make_rpc_request(self, method: str, params: List) -> Dict:
        """发送 RPC 请求到 Solana 节点"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        logger.info(f"发送 RPC 请求: {method}")
        logger.debug(f"请求参数: {json.dumps(params, indent=2)}")
        
        proxies = None
        if Config.USE_PROXY:
            proxies = {
                "http": Config.HTTP_PROXY,
                "https": Config.HTTPS_PROXY
            }
        
        try:
            response = requests.post(
                self.rpc_url, 
                headers=self.headers, 
                json=payload,
                proxies=proxies,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logger.debug(f"RPC 响应: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"RPC 请求失败: {str(e)}")
            raise

    def _get_transaction_signatures(self, wallet_address: str) -> List[str]:
        """获取地址的交易签名列表"""
        params = [
            wallet_address,
            {
                "limit": 100  # 调试阶段只获取最近100条
            }
        ]
        
        try:
            result = self._make_rpc_request("getSignaturesForAddress", params)
            signatures = []
            if 'result' in result:
                for item in result['result']:
                    sig = item.get('signature')
                    signatures.append(sig)
                    logger.info(f"获取到签名: {sig}")
            return signatures
        except Exception as e:
            logger.error(f"获取交易签名失败: {str(e)}")
            return []

    def _batch_signatures(self, signatures: List[str], batch_size: int = 50) -> List[List[str]]:
        """将签名列表分批"""
        return [signatures[i:i + batch_size] for i in range(0, len(signatures), batch_size)]

    def _get_parsed_transactions(self, signatures: List[str]) -> List[Dict]:
        """获取交易的详细信息"""
        transactions = []
        for signature in signatures:
            params = [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0
                }
            ]
            try:
                result = self._make_rpc_request("getTransaction", params)
                if 'result' in result:
                    transactions.append(result['result'])
                    logger.info(f"成功获取交易 {signature} 的详情")
            except Exception as e:
                logger.error(f"获取交易 {signature} 详情失败: {str(e)}")
                continue
        
        return transactions

    def _parse_transaction(self, txn: Dict, wallet_address: str, token_address: str) -> Optional[Dict]:
        """解析交易信息，提取转账详情"""
        if not txn or 'meta' not in txn:
            return None
        
        try:
            # 检查是否包含代币转账
            instructions = txn['transaction']['message']['instructions']
            for ix in instructions:
                if ix.get('program') != 'spl-token':
                    continue
                    
                # 检查是否是转账操作
                if ix['parsed']['type'] not in ['transfer', 'transferChecked']:
                    continue
                    
                info = ix['parsed']['info']
                    
                # 检查是否是目标代币
                if info.get('mint') != token_address:
                    continue
                    
                # 过滤协议地址
                if self._is_protocol_address(info.get('source')) or self._is_protocol_address(info.get('destination')):
                    continue
                    
                # 构造转账记录
                return {
                    'timestamp': txn.get('blockTime'),
                    'from_address': info.get('source'),
                    'to_address': info.get('destination'),
                    'token': token_address,
                    'amount': float(info.get('tokenAmount', {}).get('uiAmountString', 0))
                }
                    
        except Exception as e:
            logger.error(f"解析交易失败: {str(e)}")
            return None
        
        return None

    def _is_protocol_address(self, address: str) -> bool:
        """检查是否是协议地址"""
        PROTOCOL_ADDRESSES = {
            # Raydium 相关地址
            'RaydiumProtocolv2': '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
            'RaydiumLiquidityPool': '58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2',
            
            # Pump 相关地址
            'PumpBondingCurve': 'PumpbondingCurveAuthority11111111111111111',
            'PumpFeeAccount': 'PumpFeeAccount111111111111111111111111111',
            
            # JitoTip 相关地址
            'JitoTipAccount': 'JitoTipAccount11111111111111111111111111111'
        }
        
        return address in PROTOCOL_ADDRESSES.values()

    def get_token_transfers(self, wallet_address: str, token_address: str) -> pd.DataFrame:
        """获取指定钱包和代币的转账记录"""
        if not is_valid_solana_address(wallet_address) or not is_valid_solana_address(token_address):
            raise ValueError("无效的钱包地址或代币地址")
        
        # 获取签名列表
        logger.info(f"正在获取钱包 {wallet_address} 的最近100条交易签名...")
        try:
            signatures = self._get_transaction_signatures(wallet_address)
            logger.info(f"找到 {len(signatures)} 条交易记录")
            for i, sig in enumerate(signatures, 1):
                logger.info(f"第 {i} 条签名: {sig}")
        except Exception as e:
            logger.error(f"获取交易签名失败: {str(e)}")
            return pd.DataFrame()
        
        # 解析交易
        transfers = []
        raw_transactions = []  # 保存原始交易数据
        
        for sig_batch in self._batch_signatures(signatures):
            logger.info(f"正在解析一批 {len(sig_batch)} 条交易...")
            try:
                txns = self._get_parsed_transactions(sig_batch)
                raw_transactions.extend(txns)  # 收集原始交易数据
                
                for txn in txns:
                    try:
                        transfer = self._parse_transaction(txn, wallet_address, token_address)
                        if transfer:
                            logger.info(f"找到一笔转账: {transfer}")
                            transfers.append(transfer)
                    except Exception as e:
                        logger.error(f"解析单笔交易失败: {str(e)}")
                        continue
                    
            except Exception as e:
                logger.error(f"获取交易详情失败: {str(e)}")
                continue
        
        # 保存原始交易数据到文件
        with open(f"debug_transactions_{wallet_address[:8]}.json", 'w') as f:
            json.dump(raw_transactions, f, indent=2)
        logger.info(f"已保存原始交易数据到 debug_transactions_{wallet_address[:8]}.json")
        
        logger.info(f"解析完成，找到 {len(transfers)} 条转账记录")
        
        if transfers:
            df = pd.DataFrame(transfers)
            return df[['timestamp', 'from_address', 'to_address', 'token', 'amount']]
        return pd.DataFrame() 