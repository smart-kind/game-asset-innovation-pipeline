#!/usr/bin/env bash
# 一键部署脚本：把 API-only InvokeAI 打包并启动到目标机器（Mac Mini）
# 用法：bash deploy.sh
# 前提：目标机装好 Docker Desktop（含 docker compose）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="$ROOT/docker"
IMAGE_NAME="invokeai-api-only"
COMPOSE_DIR="$DOCKER_DIR"

echo "==> 1/4 构建镜像（$IMAGE_NAME）"
cd "$COMPOSE_DIR"
docker compose build

echo "==> 2/4 初始化数据目录与节点包"
# invokeai-data/nodes 已随仓库分发（4 个节点包）；首次运行时
# load_custom_nodes 会自动补写 README 与 custom_nodes 脚手架
mkdir -p "$COMPOSE_DIR/invokeai-data"

echo "==> 3/4 生成 .env（保留已有内容）"
if [[ ! -f "$COMPOSE_DIR/.env" ]]; then
  cp "$COMPOSE_DIR/.env.sample" "$COMPOSE_DIR/.env"
  echo "    已从 .env.sample 生成 .env，请填入 API key 后重启容器"
else
  echo "    已有 .env，跳过"
fi

echo "==> 4/4 启动容器"
docker compose up -d
docker compose ps

cat <<EOF

部署完成。
  服务: http://localhost:9090
  Swagger: http://localhost:9090/docs
  日志:  cd docker && docker compose logs -f invokeai

下一步（按需）：
  1. 编辑 docker/.env 填入 INVOKEAI_EXTERNAL_*_API_KEY（见 .env.sample 注释）
     然后 docker compose restart invokeai
  2. 若需重新拉取节点包或加新包：
     cd docker/invokeai-data/nodes && git clone <repo>
     再 docker compose restart invokeai
  3. 停止服务：cd docker && docker compose down

EOF
