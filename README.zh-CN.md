# ClawTrade

> 为 AI agent 打造的安全多券商交易中间件
>
> [English](README.md)

---

## 什么是 ClawTrade？

ClawTrade 是一个独立的安全中间件，让 AI agent（如 [OpenClaw](https://openclaw.ai)）能够安全地操作你的券商账户。它是一个**独立运行的微服务**，通过受控的 HTTP API 暴露交易功能，并在每个操作上执行硬编码的安全护栏。

项目同时提供一个轻量的 OpenClaw Skill 文件，作为 OpenClaw 与 ClawTrade 之间的桥梁。

### 为什么不直接用 OpenClaw 交易 Skill？

普通的 OpenClaw Skill 运行在**与 AI agent 相同的进程中**——这意味着 agent 可以完全访问你的券商凭证，可以随时修改安全规则，可以不受限制地执行任何操作。一旦 agent 产生幻觉或被 prompt 注入攻击，没有任何防线。

ClawTrade 采用了根本不同的方法：

| | OpenClaw Skill（直连） | ClawTrade |
|---|---|---|
| 凭证访问 | Agent 可以从环境变量/内存中读取 API 密钥 | 凭证仅存在于 agent 无法访问的 Docker 容器内 |
| 安全规则 | Agent 可以修改或忽略 | 硬编码在独立进程中；修改需要重建容器 |
| 操作范围 | 不受限——agent 可以调用任何券商 API | 仅允许白名单操作；危险操作（全部平仓、资金转出）被永久禁止 |
| 大额交易 | 立即执行 | 超过阈值时暂停，等待人工确认 |
| 审计日志 | 可选，由 agent 控制 | 强制记录，防篡改（容器内日志） |
| 券商支持 | 每个券商需要单独的 Skill | 统一 API 支持 IBKR、Alpaca、长桥、老虎 |

**简而言之：** ClawTrade 将你的 AI agent 视为不可信客户端。它赋予 agent 足够的能力来完成有用的工作，同时从结构上确保即使 agent 被攻破，也不可能造成灾难性损失。

### 支持的券商

| 券商 | 市场 | 认证方式 | 需要网关 |
|------|------|---------|---------|
| **Interactive Brokers** | 美股、港股、欧洲、亚太 | 用户名/密码 + 2FA | 是（Java 容器） |
| **Alpaca** | 美股 | API Key/Secret | 否 |
| **长桥 (Longbridge)** | 美股、港股、A 股 | App Key/Secret + Token | 否 |
| **老虎证券 (Tiger)** | 美股、港股、A 股、新加坡 | Tiger ID + RSA 密钥 | 否 |

### 核心安全理念

- **AI agent 永远不直接接触券商**——所有操作经过 ClawTrade 过滤
- **护栏硬编码**——AI 无法修改金额上限、频率限制等规则
- **ClawTrade 运行在 Docker 容器内**——即使 AI agent 以 root 运行，也无法读取容器内的券商凭证或修改配置
- **大额操作需要人工确认**——超过阈值的交易暂停等待你在聊天中确认

### 架构总览

```
你 (WhatsApp / Telegram / WebChat)
        │
        ▼
┌──────────────────────────┐
│  OpenClaw Gateway        │  宿主机运行
│  + ClawTrade Skill       │
└────────────┬─────────────┘
             │  HTTP → localhost:5100
             ▼
┌─────────────────────────────────────────────────┐
│  Docker                                         │
│  ┌─────────────────────┐  ┌───────────────────┐ │
│  │  ClawTrade          │  │  IBKR Gateway     │ │
│  │  (Python/Flask)     │←→│  (仅 IBKR)        │ │
│  │  端口 5100           │  │  端口 5000        │  │ 
│  │                     │  │  (仅容器内可见)     │  │
│  │  • 券商适配层         │  └───────────────────┘ │
│  │  • 安全护栏          │                        │
│  │  • 人工确认队列       │  Alpaca / 长桥 /       │
│  │  • 审计日志          │  老虎: 直连 API         │
│  └─────────────────────┘  (无需网关)             │
└─────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yuxuan-lou/clawtrade.git
cd clawtrade
```

### 2. 运行安装脚本

```bash
./install.sh
```

如果 ClawTrade 已经在运行，只想配置 OpenClaw Skill，可执行：

```bash
./install.sh --openclaw-only
```

安装脚本会：
1. 让你**选择券商**（IBKR、Alpaca、长桥或老虎证券）
2. 收集对应的凭证信息
3. 生成 ClawTrade API 密钥
4. 构建 Docker 镜像并启动服务
5. （可选）自动安装 OpenClaw Skill 并更新 `~/.openclaw/openclaw.json`

默认情况下，安装脚本会将敏感凭证写入宿主机 `~/.clawtrade/secrets`（目录权限 `700`，文件权限 `600`）；`.env` 仅保存非敏感配置和 `*_FILE` 引用。

> **IBKR 用户：** 首次启动需要在 2 分钟内在手机 IBKR Key 上确认推送通知。

### 3. 验证部署

```bash
# 健康检查（不需要密钥）
curl http://localhost:5100/api/health
# 预期: {"status":"ok","service":"clawtrade","broker":"ibkr"}

# 认证检查（需要密钥）
CT_SECRET=$(cat ~/.clawtrade/secrets/clawtrade_secret)
curl -H "X-ClawTrade-Token: $CT_SECRET" http://localhost:5100/api/status
```

### 4. 配置 OpenClaw Skill

`install.sh` 现在会提示是否自动配置 OpenClaw。选择 **Yes** 时，脚本会：

- 复制 `openclaw-skill/SKILL.md` 到 `~/.openclaw/skills/clawtrade/SKILL.md`
- 备份已有的 `~/.openclaw/openclaw.json`（如果存在）
- 设置 `skills.entries.clawtrade.enabled=true`
- 设置 `skills.entries.clawtrade.env.CLAWTRADE_SECRET` 为安装时生成的密钥
- 在重启时注入 `CLAWTRADE_SECRET` 到 gateway 运行环境（兼容兜底）
- 尝试重启 OpenClaw gateway

说明：多数环境下只配置 skill 级别（`skills.entries.clawtrade.env`）即可。安装脚本同时会注入 gateway 运行环境，作为兼容兜底。

如果你选择 **No**（或自动配置失败），请按下面手动步骤执行：

```bash
mkdir -p ~/.openclaw/skills/clawtrade
cp openclaw-skill/SKILL.md ~/.openclaw/skills/clawtrade/
```

在 `~/.openclaw/openclaw.json` 中添加条目：

```json
{
  "skills": {
    "entries": {
      "clawtrade": {
        "enabled": true,
        "env": {
          "CLAWTRADE_SECRET": "这里填入你的密钥"
        }
      }
    }
  }
}
```

然后重启 OpenClaw：

```bash
openclaw gateway restart
```

---

## 默认护栏参数（Paper Trading）

| 参数 | 默认值 |
|------|--------|
| 单笔交易上限 | $5,000 |
| 单笔股数上限 | 100 |
| 每日最大交易笔数 | 20 |
| 人工确认阈值 | $1,000 |
| 允许的标的类型 | STK（股票） |

修改护栏参数后需重建容器：

```bash
nano clawtrade/config.py
docker compose up -d --build clawtrade
```

---

## API 参考

除 `/api/health` 外，所有端点需要请求头：

```
X-ClawTrade-Token: 你的CLAWTRADE密钥
```

### 只读操作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查（无需认证） |
| `/api/status` | GET | 券商连接状态 |
| `/api/accounts` | GET | 列出账户 |
| `/api/portfolio/{account_id}` | GET | 投资组合摘要 |
| `/api/positions/{account_id}` | GET | 当前持仓 |
| `/api/search?symbol=AAPL` | GET | 搜索标的 |
| `/api/quote?symbols=AAPL,MSFT` | GET | 行情快照 |
| `/api/orders/{account_id}` | GET | 当前订单 |
| `/api/guardrails` | GET | 护栏配置 |
| `/api/pending` | GET | 待确认列表 |

### 写操作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/order/{account_id}` | POST | 下单（护栏检查） |
| `/api/confirm/{confirm_id}` | POST | 确认或拒绝待处理订单 |
| `/api/cancel_order/{account_id}/{order_id}` | DELETE | 取消订单 |

### 下单请求体

```json
{
  "symbol": "AAPL",
  "side": "BUY",
  "quantity": 10,
  "order_type": "LMT",
  "price": 150.00,
  "sec_type": "STK",
  "estimated_price": 150.00,
  "tif": "DAY"
}
```

API 是**券商无关的**——相同的请求格式适用于所有支持的券商。ClawTrade 负责转换为各券商的原生 API。

---

## 日常运维

```bash
# 启动服务
docker compose up -d                          # 非 IBKR 券商
docker compose --profile ibkr up -d           # IBKR（包含网关）

# 停止服务
docker compose down

# 查看日志
docker compose logs -f clawtrade

# 重新认证 IBKR（需手机确认）
docker compose exec ibkr-gateway python3 -m ibeam.ibeam_starter --authenticate

# 查看审计日志
docker compose exec clawtrade cat /app/logs/clawtrade_audit.jsonl
```

---

## 切换券商

1. 停止服务：`docker compose down`
2. 重新运行 `./install.sh` 并选择不同的券商
3. 如果密钥变更，更新 `~/.openclaw/openclaw.json` 中的 `CLAWTRADE_SECRET`

---

## 从 Paper Trading 切换到 Live

1. 更新 `~/.clawtrade/secrets` 中的券商凭证为真实账户
2. 降低护栏参数（编辑 `clawtrade/config.py`）：

```python
MAX_ORDER_VALUE_USD = 1000
MAX_ORDER_QUANTITY = 20
MAX_DAILY_TRADES = 5
CONFIRM_THRESHOLD_USD = 200
```

3. 重建：`docker compose up -d --build`
4. 先手动执行几笔小额交易，观察审计日志

---

## 常见问题

**Q: ClawTrade 会影响我已有的 OpenClaw 配置吗？**
不会。你只需要在 `openclaw.json` 的 `skills.entries` 中添加一个条目，不需要修改其他任何配置，不会影响你已安装的其他 Skill。

**Q: 我已经安装了其他交易相关的 Skill 怎么办？**
建议禁用其他直接连接券商的 Skill（如 ClawHub 上的 ibkr-trader），避免绕过 ClawTrade 的安全层。但这不是强制的——ClawTrade 的安全不依赖于此。

**Q: IBKR Gateway 认证过期怎么办？**
运行 `docker compose exec ibkr-gateway python3 -m ibeam.ibeam_starter --authenticate`，然后在手机上确认 IBKR Key 推送。保活脚本会尽量延长 session，但大约 24 小时后仍需重新认证。

**Q: 如何查看所有历史操作？**
`docker compose exec clawtrade cat /app/logs/clawtrade_audit.jsonl`。每行一个 JSON 对象，包含时间戳、操作类型、参数、结果、是否被拦截及原因。

**Q: 如果我想支持期权交易怎么办？**
编辑 `clawtrade/config.py`，在 `ALLOWED_SEC_TYPES` 列表中添加 `"OPT"`，然后 `docker compose up -d --build clawtrade`。建议同时降低金额上限。

**Q: ClawTrade 密钥泄露了怎么办？**
1. `docker compose down`
2. 生成新密钥：`openssl rand -hex 32`
3. 用新密钥覆盖 `~/.clawtrade/secrets/clawtrade_secret`
4. 如果你手动配置过 `skills.entries.clawtrade.env.CLAWTRADE_SECRET`，同步更新 `~/.openclaw/openclaw.json`
5. `docker compose up -d`

**Q: 哪些券商支持 A 股交易？**
长桥和老虎证券都通过沪港通/深港通支持 A 股。IBKR 也提供部分港股和上海上市证券的交易通道。

**Q: 我能添加一个还不支持的券商吗？**
可以。在 `clawtrade/brokers/` 目录下新建一个文件，实现 `BaseBroker` 接口（参考 `clawtrade/brokers/base.py`），在 `clawtrade/brokers/__init__.py` 中注册它，并在 `clawtrade/config.py` 中添加所需的配置项。欢迎提交 Pull Request。

---

## 项目结构

```
clawtrade/
├── README.md                   ← English documentation
├── README.zh-CN.md             ← 中文文档（你在这里）
├── LICENSE
├── install.sh                  ← 交互式安装（券商选择）
├── docker-compose.yml          ← 容器编排（支持 profiles）
├── .gitignore
│
├── clawtrade/                  ← 核心中间件
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                  ← Flask REST API
│   ├── config.py               ← 护栏 + 券商配置
│   ├── guardrails.py           ← 安全检查
│   ├── confirmation.py         ← 人工确认队列
│   ├── audit.py                ← JSONL 审计日志
│   └── brokers/                ← 券商抽象层
│       ├── base.py             ← BaseBroker 接口
│       ├── __init__.py         ← 券商工厂
│       ├── ibkr.py             ← Interactive Brokers
│       ├── alpaca_broker.py    ← Alpaca
│       ├── longbridge_broker.py← 长桥
│       └── tiger_broker.py     ← 老虎证券
│
├── gateways/                   ← 券商专用网关容器
│   └── ibkr/                   ← IBKR Client Portal Gateway + IBeam
│       ├── Dockerfile
│       ├── start.sh
│       └── keepalive.py
│
└── openclaw-skill/             ← OpenClaw 集成
    └── SKILL.md
```

---

## 许可证

MIT

---

## 关于作者

由 [Yuxuan Lou](https://yuxuanlou.info) 开发 —— 欢迎访问个人主页了解更多项目。
