#!/bin/bash
set -e

OPENCLAW_ONLY=0
OPENCLAW_REQUIRED=0

for arg in "$@"; do
    case "$arg" in
        --openclaw-only|--openclaw-skill-only)
            OPENCLAW_ONLY=1
            OPENCLAW_REQUIRED=1
            ;;
        -h|--help)
            cat <<'EOF'
Usage: ./install.sh [options]

Options:
  --openclaw-only, --openclaw-skill-only
      Configure OpenClaw Skill only (no broker prompts, no Docker build/start).
      Requires existing .env with CLAWTRADE_SECRET.
  -h, --help
      Show this help.
EOF
            exit 0
            ;;
        *)
            ;;
    esac
done

# ============================================================
# Language detection & message definitions
# ============================================================
detect_lang() {
    case "${LANG:-}${LC_ALL:-}${LANGUAGE:-}" in
        *zh_CN*|*zh_TW*|*zh_HK*|*zh*) echo "zh" ;;
        *) echo "en" ;;
    esac
}

DETECTED_LANG=$(detect_lang)

if [ "$DETECTED_LANG" = "zh" ]; then
    printf "语言 / Language: 1) 中文  2) English [1]: "
else
    printf "Language: 1) English  2) 中文 [1]: "
fi
read -r LANG_CHOICE

if [ "$DETECTED_LANG" = "zh" ]; then
    case "$LANG_CHOICE" in 2) L="en" ;; *) L="zh" ;; esac
else
    case "$LANG_CHOICE" in 2) L="zh" ;; *) L="en" ;; esac
fi

# ---- All user-facing strings ----
if [ "$L" = "zh" ]; then
    M_TITLE="===== ClawTrade 安装向导 ====="
    M_SUBTITLE="安全的 AI 交易中间件，内置护栏保护。"
    M_DOCKER_MISSING="Docker 未安装。"
    M_DOCKER_INSTALL_ASK="自动安装 Docker？[Y/n]: "
    M_DOCKER_INSTALL_MANUAL="请手动安装 Docker: https://docs.docker.com/engine/install/"
    M_DOCKER_INSTALLING="正在安装 Docker..."
    M_DOCKER_INSTALLED="Docker 安装成功。"
    M_DOCKER_MACOS="请安装 Docker Desktop for macOS:\n  https://www.docker.com/products/docker-desktop/\n\n安装后启动 Docker Desktop，然后重新运行此脚本。"
    M_DOCKER_NOT_RUNNING="Docker 已安装但未运行。"
    M_DOCKER_STARTING="正在启动 Docker..."
    M_DOCKER_START_FAIL="无法启动 Docker，请手动启动后重新运行此脚本。"
    M_DOCKER_MACOS_START="请启动 Docker Desktop 后重新运行此脚本。"
    M_COMPOSE_MISSING="Docker Compose 不可用。\n请安装: https://docs.docker.com/compose/install/"
    M_OPENSSL_MISSING="需要 openssl 但未安装。"
    M_OPENSSL_LINUX="运行: sudo apt install -y openssl  (或 yum install openssl)"
    M_OPENSSL_MACOS="运行: brew install openssl"
    M_DETECTED="已检测到"
    M_SELECT_BROKER="选择你的券商:"
    M_BROKER_1="  1) Interactive Brokers (IBKR)  — 美股、港股、欧洲、亚太"
    M_BROKER_2="  2) Alpaca                      — 美股"
    M_BROKER_3="  3) 长桥 (Longbridge)           — 美股、港股、A 股"
    M_BROKER_4="  4) 老虎证券 (Tiger)            — 美股、港股、A 股、新加坡"
    M_ENTER_CHOICE="请输入 [1-4]: "
    M_INVALID="无效选择"
    M_SELECTED="已选择券商: "
    M_IBKR_WARN="⚠️  强烈建议先使用 IBKR Paper Trading 账户进行测试！"
    M_IBKR_USER="IBKR 用户名: "
    M_IBKR_PASS="IBKR 密码: "
    M_ALPACA_KEYS="在此获取 API 密钥: https://app.alpaca.markets/paper/dashboard/overview"
    M_ALPACA_KEY="Alpaca API Key: "
    M_ALPACA_SECRET="Alpaca Secret Key: "
    M_ALPACA_PAPER="使用模拟交易？[Y/n]: "
    M_LB_KEYS="在此获取 API 凭证: https://open.longbridge.com/"
    M_LB_APP_KEY="长桥 App Key: "
    M_LB_APP_SECRET="长桥 App Secret: "
    M_LB_TOKEN="长桥 Access Token: "
    M_TIGER_KEYS="在此获取 API 凭证: https://quant.itigerup.com/"
    M_TIGER_ID="Tiger ID: "
    M_TIGER_ACCOUNT="Tiger 账户: "
    M_TIGER_RSA="粘贴你的 RSA 私钥（以空行结束）:"
    M_CT_SECRET="ClawTrade API 密钥（留空自动生成）: "
    M_CT_GENERATED="已生成 ClawTrade API 密钥。"
    M_CONFIG_SAVED="配置已写入 .env（权限 600）"
    M_BUILDING="正在构建 Docker 镜像..."
    M_STARTING_IBKR="正在启动服务（含 IBKR Gateway）..."
    M_STARTING="正在启动 ClawTrade..."
    M_COMPLETE="===== 安装完成 ====="
    M_RUNNING="ClawTrade 运行于: http://localhost:5100"
    M_BROKER_LABEL="券商: "
    M_YOUR_KEY="你的 ClawTrade API 密钥（配置 OpenClaw 时需要）:"
    M_SAVE_KEY="请保存此密钥，后续配置 OpenClaw Skill 时需要使用。"
    M_IBKR_2FA="⚠️  IBKR: 请在手机 IBKR Key 上确认推送通知！\n   查看认证日志: docker compose logs -f ibkr-gateway"
    M_NEXT="下一步: 配置 OpenClaw Skill（见 README.zh-CN.md）"
    M_OC_FOUND="检测到 OpenClaw。"
    M_OC_SETUP_ASK="现在自动配置 OpenClaw Skill？[Y/n]: "
    M_OC_SETUP_START="正在配置 OpenClaw Skill..."
    M_OC_SETUP_SKIP="已跳过 OpenClaw Skill 自动配置。"
    M_OC_NOT_FOUND="未检测到 openclaw 命令，跳过自动配置。"
    M_OC_SKILL_INSTALLED="已安装 Skill 文件到: ~/.openclaw/skills/clawtrade/SKILL.md"
    M_OC_CONFIG_BACKUP="已备份 OpenClaw 配置: "
    M_OC_CONFIG_UPDATED="已更新 ~/.openclaw/openclaw.json 中的 skills.entries.clawtrade。"
    M_OC_CONFIG_FAILED="自动写入 OpenClaw 配置失败，请按 README 手动配置。"
    M_OC_RESTARTING="正在重启 OpenClaw Gateway..."
    M_OC_RESTARTED="OpenClaw Gateway 重启完成。"
    M_OC_RESTART_FAILED="自动重启失败，请手动执行: openclaw gateway restart"
    M_OC_VERIFYING="正在检查 OpenClaw Skill 状态..."
    M_OC_READY="OpenClaw Skill 检查通过：clawtrade 已就绪。"
    M_OC_NOT_READY="OpenClaw Skill 还未就绪。请运行: openclaw skills check"
    M_OC_ONLY_MODE="仅执行 OpenClaw Skill 配置模式（不修改 Docker 服务）。"
    M_OC_ONLY_ENV_MISSING="未找到 .env，请先完成一次完整安装。"
    M_OC_ONLY_SECRET_MISSING=".env 中缺少 CLAWTRADE_SECRET，无法继续。"
    M_OC_ONLY_DONE="OpenClaw Skill 配置流程完成。"
else
    M_TITLE="===== ClawTrade Setup Wizard ====="
    M_SUBTITLE="Secure AI trading middleware with guardrail protection."
    M_DOCKER_MISSING="Docker is not installed."
    M_DOCKER_INSTALL_ASK="Install Docker automatically? [Y/n]: "
    M_DOCKER_INSTALL_MANUAL="Please install Docker manually: https://docs.docker.com/engine/install/"
    M_DOCKER_INSTALLING="Installing Docker..."
    M_DOCKER_INSTALLED="Docker installed successfully."
    M_DOCKER_MACOS="Please install Docker Desktop for macOS:\n  https://www.docker.com/products/docker-desktop/\n\nAfter installing, start Docker Desktop and re-run this script."
    M_DOCKER_NOT_RUNNING="Docker is installed but not running."
    M_DOCKER_STARTING="Starting Docker..."
    M_DOCKER_START_FAIL="Failed to start Docker. Please start it manually and re-run this script."
    M_DOCKER_MACOS_START="Please start Docker Desktop and re-run this script."
    M_COMPOSE_MISSING="Docker Compose is not available.\nPlease install: https://docs.docker.com/compose/install/"
    M_OPENSSL_MISSING="openssl is required but not installed."
    M_OPENSSL_LINUX="Run: sudo apt install -y openssl  (or yum install openssl)"
    M_OPENSSL_MACOS="Run: brew install openssl"
    M_DETECTED="detected"
    M_SELECT_BROKER="Select your broker:"
    M_BROKER_1="  1) Interactive Brokers (IBKR)  — US, HK, EU, APAC"
    M_BROKER_2="  2) Alpaca                      — US equities"
    M_BROKER_3="  3) Longbridge                  — US, HK, China A-shares"
    M_BROKER_4="  4) Tiger Brokers               — US, HK, China A-shares, SG"
    M_ENTER_CHOICE="Enter choice [1-4]: "
    M_INVALID="Invalid choice"
    M_SELECTED="Selected broker: "
    M_IBKR_WARN="⚠️  Strongly recommended: use an IBKR Paper Trading account first!"
    M_IBKR_USER="IBKR Username: "
    M_IBKR_PASS="IBKR Password: "
    M_ALPACA_KEYS="Get your API keys at: https://app.alpaca.markets/paper/dashboard/overview"
    M_ALPACA_KEY="Alpaca API Key: "
    M_ALPACA_SECRET="Alpaca Secret Key: "
    M_ALPACA_PAPER="Use paper trading? [Y/n]: "
    M_LB_KEYS="Get your API credentials at: https://open.longbridge.com/"
    M_LB_APP_KEY="Longbridge App Key: "
    M_LB_APP_SECRET="Longbridge App Secret: "
    M_LB_TOKEN="Longbridge Access Token: "
    M_TIGER_KEYS="Get your API credentials at: https://quant.itigerup.com/"
    M_TIGER_ID="Tiger ID: "
    M_TIGER_ACCOUNT="Tiger Account: "
    M_TIGER_RSA="Paste your RSA private key (end with an empty line):"
    M_CT_SECRET="ClawTrade API Key (leave empty to auto-generate): "
    M_CT_GENERATED="ClawTrade API key has been generated."
    M_CONFIG_SAVED="Configuration saved to .env (permissions 600)"
    M_BUILDING="Building Docker images..."
    M_STARTING_IBKR="Starting services (with IBKR Gateway)..."
    M_STARTING="Starting ClawTrade..."
    M_COMPLETE="===== Setup Complete ====="
    M_RUNNING="ClawTrade is running at: http://localhost:5100"
    M_BROKER_LABEL="Broker: "
    M_YOUR_KEY="Your ClawTrade API key (needed for OpenClaw configuration):"
    M_SAVE_KEY="Please save this key — you will need it when configuring the OpenClaw Skill."
    M_IBKR_2FA="⚠️  IBKR: Confirm the push notification on your IBKR Key mobile app!\n   View authentication logs: docker compose logs -f ibkr-gateway"
    M_NEXT="Next step: Configure the OpenClaw Skill (see README.md)"
    M_OC_FOUND="OpenClaw detected."
    M_OC_SETUP_ASK="Configure OpenClaw Skill automatically now? [Y/n]: "
    M_OC_SETUP_START="Configuring OpenClaw Skill..."
    M_OC_SETUP_SKIP="Skipped OpenClaw Skill auto-setup."
    M_OC_NOT_FOUND="openclaw command not found. Skipping automatic setup."
    M_OC_SKILL_INSTALLED="Installed Skill file at: ~/.openclaw/skills/clawtrade/SKILL.md"
    M_OC_CONFIG_BACKUP="Backed up OpenClaw config to: "
    M_OC_CONFIG_UPDATED="Updated skills.entries.clawtrade in ~/.openclaw/openclaw.json."
    M_OC_CONFIG_FAILED="Failed to update OpenClaw config automatically. Please follow README manual steps."
    M_OC_RESTARTING="Restarting OpenClaw Gateway..."
    M_OC_RESTARTED="OpenClaw Gateway restarted."
    M_OC_RESTART_FAILED="Could not restart automatically. Run: openclaw gateway restart"
    M_OC_VERIFYING="Checking OpenClaw Skill status..."
    M_OC_READY="OpenClaw Skill check passed: clawtrade is ready."
    M_OC_NOT_READY="OpenClaw Skill is not ready yet. Run: openclaw skills check"
    M_OC_ONLY_MODE="OpenClaw Skill-only mode (Docker services are not modified)."
    M_OC_ONLY_ENV_MISSING=".env not found. Please complete a full install first."
    M_OC_ONLY_SECRET_MISSING="CLAWTRADE_SECRET is missing in .env. Cannot continue."
    M_OC_ONLY_DONE="OpenClaw Skill setup flow completed."
fi

# ============================================================
# Main script
# ============================================================
echo ""
echo "$M_TITLE"
echo ""
echo "$M_SUBTITLE"
echo ""

# ---- Check prerequisites ----
check_command() {
    command -v "$1" &> /dev/null
}

verify_openclaw_skill_ready() {
    if ! check_command openclaw; then
        echo "$M_OC_NOT_READY"
        return
    fi

    echo "$M_OC_VERIFYING"
    OC_CHECK_OUTPUT="$(openclaw skills check 2>/dev/null || true)"
    OC_READY_BLOCK="$(printf "%s\n" "$OC_CHECK_OUTPUT" | awk '/Ready to use:/{flag=1;next}/Missing requirements:/{flag=0}flag')"

    case "$OC_READY_BLOCK" in
        *"clawtrade"*)
            echo "$M_OC_READY"
            ;;
        *)
            echo "$M_OC_NOT_READY"
            ;;
    esac
}

setup_openclaw_skill() {
    if ! check_command openclaw; then
        echo "$M_OC_NOT_FOUND"
        if [ "$OPENCLAW_REQUIRED" = "1" ]; then
            return 1
        fi
        return 0
    fi

    echo "$M_OC_FOUND"
    if [ "$OPENCLAW_ONLY" != "1" ]; then
        printf "%s" "$M_OC_SETUP_ASK"
        read -r OC_SETUP_CHOICE
        if [[ "$OC_SETUP_CHOICE" =~ ^[Nn]$ ]]; then
            echo "$M_OC_SETUP_SKIP"
            return 0
        fi
    fi

    echo "$M_OC_SETUP_START"

    OPENCLAW_DIR="${HOME}/.openclaw"
    OPENCLAW_SKILL_DIR="${OPENCLAW_DIR}/skills/clawtrade"
    OPENCLAW_CONFIG="${OPENCLAW_DIR}/openclaw.json"

    mkdir -p "$OPENCLAW_SKILL_DIR"
    cp openclaw-skill/SKILL.md "$OPENCLAW_SKILL_DIR/SKILL.md"
    echo "$M_OC_SKILL_INSTALLED"

    mkdir -p "$OPENCLAW_DIR"
    if [ -f "$OPENCLAW_CONFIG" ]; then
        OPENCLAW_BACKUP="${OPENCLAW_CONFIG}.bak.$(date +%F-%H%M%S)"
        cp "$OPENCLAW_CONFIG" "$OPENCLAW_BACKUP"
        echo "${M_OC_CONFIG_BACKUP}${OPENCLAW_BACKUP}"
    fi

    if openclaw config set skills.entries.clawtrade.enabled true --strict-json >/dev/null 2>&1 \
        && openclaw config set skills.entries.clawtrade.env.CLAWTRADE_SECRET "\"${CLAWTRADE_SECRET}\"" --strict-json >/dev/null 2>&1; then
        echo "$M_OC_CONFIG_UPDATED"
    else
        echo "$M_OC_CONFIG_FAILED"
        return
    fi

    echo "$M_OC_RESTARTING"
    if CLAWTRADE_SECRET="$CLAWTRADE_SECRET" openclaw gateway restart >/dev/null 2>&1; then
        echo "$M_OC_RESTARTED"
    else
        echo "$M_OC_RESTART_FAILED"
    fi

    verify_openclaw_skill_ready
}

if [ "$OPENCLAW_ONLY" = "1" ]; then
    echo "$M_OC_ONLY_MODE"
    if [ ! -f ".env" ]; then
        echo "$M_OC_ONLY_ENV_MISSING"
        exit 1
    fi

    CLAWTRADE_SECRET=$(awk -F= '/^CLAWTRADE_SECRET=/{sub(/^CLAWTRADE_SECRET=/, ""); print; exit}' .env)
    if [ -z "$CLAWTRADE_SECRET" ]; then
        echo "$M_OC_ONLY_SECRET_MISSING"
        exit 1
    fi

    setup_openclaw_skill
    echo "$M_OC_ONLY_DONE"
    exit 0
fi

if ! check_command docker; then
    echo "$M_DOCKER_MISSING"
    echo ""
    case "$(uname -s)" in
        Linux*)
            printf "%s" "$M_DOCKER_INSTALL_ASK"
            read -r INSTALL_DOCKER
            if [[ "$INSTALL_DOCKER" =~ ^[Nn]$ ]]; then
                echo "$M_DOCKER_INSTALL_MANUAL"
                exit 1
            fi
            echo "$M_DOCKER_INSTALLING"
            curl -fsSL https://get.docker.com | sh
            echo "$M_DOCKER_INSTALLED"
            echo ""
            ;;
        Darwin*)
            printf "%b\n" "$M_DOCKER_MACOS"
            exit 1
            ;;
        *)
            echo "$M_DOCKER_INSTALL_MANUAL"
            exit 1
            ;;
    esac
fi

if ! docker info &> /dev/null; then
    echo "$M_DOCKER_NOT_RUNNING"
    case "$(uname -s)" in
        Linux*)
            echo "$M_DOCKER_STARTING"
            sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null || true
            sleep 3
            if ! docker info &> /dev/null; then
                echo "$M_DOCKER_START_FAIL"
                exit 1
            fi
            ;;
        Darwin*)
            echo "$M_DOCKER_MACOS_START"
            exit 1
            ;;
    esac
fi

if ! docker compose version &> /dev/null; then
    printf "%b\n" "$M_COMPOSE_MISSING"
    exit 1
fi

if ! check_command openssl; then
    echo "$M_OPENSSL_MISSING"
    case "$(uname -s)" in
        Linux*)  echo "$M_OPENSSL_LINUX" ;;
        Darwin*) echo "$M_OPENSSL_MACOS" ;;
    esac
    exit 1
fi

DOCKER_VER=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
echo "✓ Docker ${DOCKER_VER} $M_DETECTED"
echo "✓ Docker Compose $M_DETECTED"
echo ""

# ---- Broker selection ----
echo "$M_SELECT_BROKER"
echo "$M_BROKER_1"
echo "$M_BROKER_2"
echo "$M_BROKER_3"
echo "$M_BROKER_4"
echo ""
read -p "$M_ENTER_CHOICE" BROKER_CHOICE

case $BROKER_CHOICE in
    1) BROKER_TYPE="ibkr" ;;
    2) BROKER_TYPE="alpaca" ;;
    3) BROKER_TYPE="longbridge" ;;
    4) BROKER_TYPE="tiger" ;;
    *) echo "$M_INVALID"; exit 1 ;;
esac

echo ""
echo "${M_SELECTED}${BROKER_TYPE}"
echo ""

# ---- Collect broker-specific credentials ----
case $BROKER_TYPE in
    ibkr)
        echo "$M_IBKR_WARN"
        echo ""
        read -p "$M_IBKR_USER" IBEAM_ACCOUNT
        read -sp "$M_IBKR_PASS" IBEAM_PASSWORD && echo
        BROKER_VARS="IBEAM_ACCOUNT=${IBEAM_ACCOUNT}
IBEAM_PASSWORD=${IBEAM_PASSWORD}"
        ;;
    alpaca)
        echo "$M_ALPACA_KEYS"
        echo ""
        read -p "$M_ALPACA_KEY" ALPACA_API_KEY
        read -sp "$M_ALPACA_SECRET" ALPACA_SECRET_KEY && echo
        echo ""
        read -p "$M_ALPACA_PAPER" USE_PAPER
        if [[ "$USE_PAPER" =~ ^[Nn]$ ]]; then
            ALPACA_BASE_URL="https://api.alpaca.markets"
        else
            ALPACA_BASE_URL="https://paper-api.alpaca.markets"
        fi
        BROKER_VARS="ALPACA_API_KEY=${ALPACA_API_KEY}
ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
ALPACA_BASE_URL=${ALPACA_BASE_URL}
ALPACA_DATA_URL=https://data.alpaca.markets"
        ;;
    longbridge)
        echo "$M_LB_KEYS"
        echo ""
        read -p "$M_LB_APP_KEY" LONGBRIDGE_APP_KEY
        read -sp "$M_LB_APP_SECRET" LONGBRIDGE_APP_SECRET && echo
        read -sp "$M_LB_TOKEN" LONGBRIDGE_ACCESS_TOKEN && echo
        BROKER_VARS="LONGBRIDGE_APP_KEY=${LONGBRIDGE_APP_KEY}
LONGBRIDGE_APP_SECRET=${LONGBRIDGE_APP_SECRET}
LONGBRIDGE_ACCESS_TOKEN=${LONGBRIDGE_ACCESS_TOKEN}"
        ;;
    tiger)
        echo "$M_TIGER_KEYS"
        echo ""
        read -p "$M_TIGER_ID" TIGER_ID
        read -p "$M_TIGER_ACCOUNT" TIGER_ACCOUNT
        echo "$M_TIGER_RSA"
        TIGER_PRIVATE_KEY=""
        while IFS= read -r line; do
            [[ -z "$line" ]] && break
            TIGER_PRIVATE_KEY="${TIGER_PRIVATE_KEY}${line}\n"
        done
        BROKER_VARS="TIGER_ID=${TIGER_ID}
TIGER_ACCOUNT=${TIGER_ACCOUNT}
TIGER_PRIVATE_KEY=${TIGER_PRIVATE_KEY}"
        ;;
esac

# ---- ClawTrade API key ----
echo ""
read -sp "$M_CT_SECRET" CLAWTRADE_SECRET && echo

if [ -z "$CLAWTRADE_SECRET" ]; then
    CLAWTRADE_SECRET=$(openssl rand -hex 32)
    echo ""
    echo "$M_CT_GENERATED"
fi

# ---- Generate .env file ----
cat > .env << EOF
BROKER_TYPE=${BROKER_TYPE}
CLAWTRADE_SECRET=${CLAWTRADE_SECRET}
${BROKER_VARS}
EOF
chmod 600 .env

echo ""
echo "$M_CONFIG_SAVED"

# ---- Build and start ----
echo ""
echo "$M_BUILDING"

if [ "$BROKER_TYPE" = "ibkr" ]; then
    docker compose --profile ibkr build
    echo ""
    echo "$M_STARTING_IBKR"
    docker compose --profile ibkr up -d
else
    docker compose build clawtrade
    echo ""
    echo "$M_STARTING"
    docker compose up -d
fi

echo ""
echo "$M_COMPLETE"
echo ""
echo "$M_RUNNING"
echo "${M_BROKER_LABEL}${BROKER_TYPE}"
echo ""
echo "$M_YOUR_KEY"
echo "  $CLAWTRADE_SECRET"
echo ""
echo "$M_SAVE_KEY"

echo ""
setup_openclaw_skill

if [ "$BROKER_TYPE" = "ibkr" ]; then
    echo ""
    printf "%b\n" "$M_IBKR_2FA"
fi

echo ""
echo "$M_NEXT"
