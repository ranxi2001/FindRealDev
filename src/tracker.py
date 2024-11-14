import requests
import json
import pandas as pd
from typing import List, Dict, Optional
from utils import is_valid_solana_address, setup_logging
from config import Config
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

logger = setup_logging()

class WalletTracker:
    def __init__(self):
        self.rpc_url = Config.QUICKNODE_RPC_URL
        self.headers = {
            "Content-Type": "application/json"
        }
        if Config.QUICKNODE_API_KEY:
            self.headers["Authorization"] = f"Bearer {Config.QUICKNODE_API_KEY}"
        self._signature_cache = {}
        self._transaction_cache = {}

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
            try:
                params = [
                    signature,
                    {
                        "encoding": "jsonParsed",
                        "maxSupportedTransactionVersion": 0
                    }
                ]
                
                result = self._make_rpc_request("getTransaction", params)
                if result and 'result' in result and result['result']:
                    transactions.append(result['result'])
                    logger.debug(f"成功获取交易 {signature} 的详情")
                else:
                    logger.warning(f"交易 {signature} 返回空数据")
                    
            except Exception as e:
                logger.error(f"获取交易 {signature} 详情失败: {str(e)}")
                continue
                
        return transactions

    def _parse_token_transfers(self, txn: Dict, wallet_address: str, token_address: str) -> Optional[Dict]:
        """解析代币转账信息，只返回主钱包作为发送方的转账"""
        if not txn or 'meta' not in txn:
            logger.debug("交易数据为空或没有meta数据")
            return None
        
        try:
            pre_balances = {
                b['owner']: float(b['uiTokenAmount']['uiAmountString'])
                for b in txn['meta'].get('preTokenBalances', [])
                if b.get('mint') == token_address
            }
            
            post_balances = {
                b['owner']: float(b['uiTokenAmount']['uiAmountString'])
                for b in txn['meta'].get('postTokenBalances', [])
                if b.get('mint') == token_address
            }
            
            # 如果目标钱包不在余额变化中，直接返回
            if wallet_address not in pre_balances:
                return None
                
            # 计算目标钱包的余额变化
            pre_amount = pre_balances.get(wallet_address, 0)
            post_amount = post_balances.get(wallet_address, 0)
            
            # 只关注余额减少的情况（转出）
            if pre_amount <= post_amount:
                return None
                
            # 找到接收方地址
            recipient = self._find_recipient(pre_balances, post_balances)
            if not recipient or self._is_protocol_address(recipient):
                return None
                
            return {
                'timestamp': txn.get('blockTime'),
                'from_address': wallet_address,
                'to_address': recipient,
                'token': token_address,
                'amount': abs(post_amount - pre_amount)
            }
                
        except Exception as e:
            logger.error(f"解析代币转账失败: {str(e)}")
            return None

    def _find_recipient(self, pre_balances: Dict[str, float], post_balances: Dict[str, float]) -> Optional[str]:
        """找到转账接收方"""
        for address, post_amount in post_balances.items():
            pre_amount = pre_balances.get(address, 0)
            if post_amount > pre_amount:
                return address
        return None

    def _find_sender(self, pre_balances: Dict[str, float], post_balances: Dict[str, float]) -> Optional[str]:
        """找到转账发送方"""
        for address, pre_amount in pre_balances.items():
            post_amount = post_balances.get(address, 0)
            if post_amount < pre_amount:
                return address
        return None

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

    def _batch_rpc_requests(self, method: str, params_list: List[List]) -> List[Dict]:
        """批量发送 RPC 请求"""
        payload = [
            {
                "jsonrpc": "2.0",
                "id": i,
                "method": method,
                "params": params
            }
            for i, params in enumerate(params_list)
        ]
        
        try:
            response = requests.post(
                self.rpc_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"批量 RPC 请求失败: {str(e)}")
            raise

    @lru_cache(maxsize=1000)
    def _get_cached_transaction(self, signature: str) -> Dict:
        """缓存交易数据"""
        if signature not in self._transaction_cache:
            result = self._make_rpc_request("getTransaction", [signature, {"encoding": "jsonParsed"}])
            self._transaction_cache[signature] = result.get('result')
        return self._transaction_cache[signature]

    def _filter_signatures(self, signatures: List[str], start_time: Optional[int] = None) -> List[str]:
        """按时间过滤签名"""
        if not start_time:
            return signatures
        
        filtered = []
        for sig_batch in self._batch_signatures(signatures):
            txns = self._get_parsed_transactions(sig_batch)
            filtered.extend([
                txn['transaction']['signatures'][0]
                for txn in txns
                if txn.get('blockTime', 0) >= start_time
            ])
        return filtered

    def get_token_transfers(self, wallet_address: str, token_address: str) -> pd.DataFrame:
        """获取指定钱包和代币的转账记录"""
        try:
            # 获取交易签名
            signatures = self._get_transaction_signatures(wallet_address)
            if not signatures:
                logger.info(f"未找到钱包 {wallet_address} 的交易记录")
                return pd.DataFrame()
            
            transfers = []
            
            # 批量处理交易
            for sig_batch in self._batch_signatures(signatures):
                try:
                    txns = self._get_parsed_transactions(sig_batch)
                    
                    for txn in txns:
                        if not txn:
                            continue
                            
                        transfer = self._parse_token_transfers(txn, wallet_address, token_address)
                        if transfer:
                            transfers.append(transfer)
                            logger.info(f"找到转账记录: {transfer}")
                            
                except Exception as e:
                    logger.error(f"处理交易批次失败: {str(e)}")
                    continue
                
            if transfers:
                df = pd.DataFrame(transfers)
                # 只保留有效的转账记录
                df = df.dropna(subset=['from_address', 'to_address'], how='all')
                return df
                
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取转账记录失败: {str(e)}")
            return pd.DataFrame() 