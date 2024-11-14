import logging
from config import Config

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def is_valid_solana_address(address: str) -> bool:
    """验证 Solana 地址格式"""
    if not address:
        return False
    return len(address) == 44 or len(address) == 43

def filter_address(address: str) -> bool:
    """检查地址是否需要被过滤"""
    return address in Config.FILTER_ADDRESSES 