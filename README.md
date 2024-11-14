# Solana 链上开发者钱包追踪工具

## 项目简介
这是一个用于追踪 Solana 链上代币开发者钱包地址的分析工具。通过分析链上交易数据,帮助识别和追踪代币开发者的资金流向。

## 功能特性
- 追踪指定钱包地址的资金流向
- 分析代币合约(CA)相关交易
- 过滤常见的 DEX 和协议地址
- 基于 QuickNode RPC 接口实现
- ### 主要功能

  1. 查询钱包最近100条交易记录
  2. 解析代币转账信息
  3. 过滤常见协议地址（Raydium、Pump、JitoTip等）
  4. 支持批量处理交易签名
  5. 导出CSV格式的转账记录

## 使用方法

### 输入参数
- 主钱包地址: 需要追踪的目标钱包地址
- 代币合约地址(CA): 需要分析的代币合约地址

### 输出结果
工具将输出以下格式的交易记录:
| From | To | Token |
|------|-----|-------|
| 主钱包 | 目标钱包 | CA |
| 主钱包 | 目标钱包 | SOL |

### 过滤规则
自动过滤以下地址:
- Raydium 相关地址
- Pump bonding curve 地址
- Pump fee account 地址
- JitoTip 相关地址

## 技术实现
- 使用 QuickNode RPC 接口获取交易数据
- 支持解析 SPL Token 的 transfer 和 transferChecked 指令
- 通过分析 preTokenBalances 和 postTokenBalances 识别真实转账
- 支持代理配置和超时重试

## 使用方法

### 配置文件
在 `.env` 文件中设置：
```env
QUICKNODE_RPC_URL=你的RPC地址
QUICKNODE_API_KEY=你的API密钥
USE_PROXY=false
HTTP_PROXY=
HTTPS_PROXY=
```

### 添加追踪地址
在 `addresses.py` 中配置：
```python
WALLET_ADDRESSES = [
    "要追踪的钱包地址",
]

TOKEN_ADDRESSES = [
    "要追踪的代币地址",
]
```

### 运行程序

#### 安装依赖

```
pip install -r requirements.txt --user
```

#### 运行主程序

```bash
python src/main.py
```

#### 输出格式
生成的CSV文件包含以下字段：
- timestamp: 交易时间戳
- from_address: 发送方地址
- to_address: 接收方地址
- token: 代币合约地址
- amount: 转账金额

## 代码结构
```
src/
├── main.py          # 程序入口
├── tracker.py       # 核心追踪逻辑
├── addresses.py     # 地址配置
├── config.py        # 配置管理
└── utils.py         # 工具函数
```

## 开发计划
- [ ] 添加更多协议地址过滤
- [ ] 支持自定义查询时间范围
- [ ] 添加转账金额阈值过滤
- [ ] 优化RPC请求速率限制
- [ ] 添加详细的交易类型分析

## 注意事项
1. 请确保RPC节点的稳定性和请求限制
2. 大量交易数据的处理可能需要较长时间
3. 建议先用少量地址测试程序功能

## 主要改进

1. 更清晰地描述了技术实现细节
2. 添加了具体的配置和使用说明
3. 列出了后续的开发计划
4. 补充了重要的注意事项