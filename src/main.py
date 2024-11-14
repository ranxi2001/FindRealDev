from tracker import WalletTracker
from utils import is_valid_solana_address, setup_logging
from config import Config
from addresses import WALLET_ADDRESSES, TOKEN_ADDRESSES

logger = setup_logging()

def main():
    try:
        # 验证配置
        Config.validate()
        
        # 初始化追踪器
        tracker = WalletTracker()
        
        # 遍历所有钱包和代币组合
        for wallet in WALLET_ADDRESSES:
            if not is_valid_solana_address(wallet):
                logger.error(f"错误: 无效的钱包地址 {wallet}")
                continue
                
            for token in TOKEN_ADDRESSES:
                if not is_valid_solana_address(token):
                    logger.error(f"错误: 无效的代币地址 {token}")
                    continue
                    
                output_file = f"transfers_{wallet[:8]}_{token[:8]}.csv"
                logger.info(f"正在追踪钱包 {wallet} 的 {token} 代币转账记录...")
                
                try:
                    # ransfers = tracker.get_token_transfers(wallet, token)
                    # 只获取转入的 SPL 代币转账
                    # transfers = tracker.get_token_transfers(wallet, token, direction='in', token_type='spl')
                    # 只获取转出的 SOL 转账
                    # transfers = tracker.get_token_transfers(wallet, token, direction='out', token_type='sol')
                    transfers = tracker.get_token_transfers(wallet, token, direction='out', token_type='spl')
                    if not transfers.empty:
                        transfers.to_csv(output_file, index=False)
                        logger.info(f"已找到 {len(transfers)} 条转账记录，已保存到 {output_file}")
                    else:
                        logger.info("未找到相关转账记录")
                        
                except Exception as e:
                    logger.error(f"处理钱包 {wallet} 和代币 {token} 时发生错误: {str(e)}")
                    continue
                    
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main() 