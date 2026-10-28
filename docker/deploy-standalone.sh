#!/usr/bin/env bash
# 无源码部署脚本：Mac Mini 上不需要仓库源码
# 前提：已把 invokeai-api-only.tar.gz + invokeai-node-packs.zip 拷到本机
# 用法：
#   1. 把 invokeai-api-only.tar.gz 和解压后的 invokeai-data/ 放在同一目录
#   2. bash deploy-standalone.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_TAR="$DIR/invokeai-api-only.tar.gz"
DATA_DIR="$DIR/invokeai-data"
NODES_ZIP="$DIR/invokeai-node-packs.zip"

echo "==> 1/5 检查镜像 tar"
[[ -f "$IMAGE_TAR" ]] || { echo "找不到 $IMAGE_TAR，先把 invokeai-api-only.tar.gz 拷到 $DIR"; exit 1; }

echo "==> 2/5 docker load 镜像"
gunzip -c "$IMAGE_TAR" | docker load

echo "==> 3/5 解压节点包到 invokeai-data/nodes/"
mkdir -p "$DATA_DIR/nodes"
if [[ -f "$NODES_ZIP" ]]; then
  unzip -o -q "$NODES_ZIP" -d "$DATA_DIR/nodes"
  echo "    已解压 $(unzip -l "$NODES_ZIP" | tail -1 | awk '{print $2}') 个文件"
else
  echo "    未找到 $NODES_ZIP（若节点包已提前放好可跳过）"
fi

echo "==> 4/5 生成 .env（保留已有）"
if [[ ! -f "$DIR/.env" ]]; then
  [[ -f "$DIR/.env.sample" ]] && cp "$DIR/.env.sample" "$DIR/.env"
  echo "    已生成 .env，填入 API key 后 restart"
else
  echo "    已有 .env，跳过"
fi

echo "==> 5/5 启动容器（standalone compose，无 build）"
cd "$DIR"
docker compose -f docker-compose.standalone.yml up -d
docker compose -f docker-compose.standalone.yml ps

cat <<EOF

部署完成（无源码）。
  服务:   http://localhost:9090
  Swagger: http://localhost:9090/docs
  日志:   docker compose -f docker-compose.standalone.yml logs -f invokeai

下一步：
  1. 编辑 ./.env 填 INVOKEAI_EXTERNAL_*_API_KEY，再
     docker compose -f docker-compose.standalone.yml restart invokeai
  2. 停服务：docker compose -f docker-compose.standalone.yml down

EOF
