import os
from dotenv import load_dotenv
import json

load_dotenv()

class Config:
    QUICKNODE_RPC_URL = os.getenv("QUICKNODE_RPC_URL", "https://api.mainnet-beta.solana.com")
    QUICKNODE_API_KEY = os.getenv("QUICKNODE_API_KEY", "")
    MAX_TRANSACTIONS = int(os.getenv("MAX_TRANSACTIONS", 1000))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 50))
    
    # 过滤地址列表
    FILTER_ADDRESSES = json.loads(os.getenv("FILTER_ADDRESSES", "[]"))
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "wallet_tracker.log")
    
    USE_PROXY = os.getenv("USE_PROXY", "false").lower() == "true"
    HTTP_PROXY = os.getenv("HTTP_PROXY")
    HTTPS_PROXY = os.getenv("HTTPS_PROXY")
    
    @classmethod
    def validate(cls):
        """验证必要的配置是否存在"""
        if not cls.QUICKNODE_RPC_URL:
            raise ValueError("Missing QUICKNODE_RPC_URL in .env")