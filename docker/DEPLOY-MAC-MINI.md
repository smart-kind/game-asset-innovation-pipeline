# 部署到 Mac Mini（API-only InvokeAI，无源码）

目标：Mac Mini 上**不需要仓库源码**，只传 2 个文件即可跑起来。

## 镜像体积

`invokeai-api-only.tar.gz` 约 **535 MB**（未压缩镜像 1.64 GB）。主体是 venv 里的 Python 依赖（onnxruntime/scipy/PIL 那 991 MB 层）+ 源码 80 MB + webv2 前端 dist 9 MB。节点包 1.6 MB 单独打包，走 bind mount，不在镜像里。

## 待传输文件（都在这台机器的 `docker/` 下）

| 文件 | 大小 | 说明 |
|---|---|---|
| `docker/invokeai-api-only.tar.gz` | 535 MB | 容器镜像（含全部 pip 依赖，无需 build） |
| `docker/invokeai-node-packs.zip` | 1.6 MB | 4 个节点包（14 个节点），解压到 `invokeai-data/nodes/` |
| `docker/docker-compose.standalone.yml` | 0.5 KB | 无 build 段的 compose，直接用已 load 的镜像 |
| `docker/deploy-standalone.sh` | 1.8 KB | 一键脚本：load 镜像 → 解节点包 → 生成 .env → 起容器 |
| `docker/.env.sample` | 2 KB | API key 配置模板 |

## Mac Mini 上的步骤

### 1. 传文件

```bash
# 在 Mac Mini 上建目录，把 5 个文件拷进去（tar.gz 535MB 走 scp 几分钟）
mkdir -p ~/invokeai-deploy
scp user@this-machine:~/_projects/2_personal/games/game-asset-innovation-pipeline/docker/{invokeai-api-only.tar.gz,invokeai-node-packs.zip,docker-compose.standalone.yml,deploy-standalone.sh,.env.sample} ~/invokeai-deploy/
```

### 2. 一键启动（无源码）

```bash
cd ~/invokeai-deploy
bash deploy-standalone.sh
```

脚本做 5 步：检查镜像 tar → `docker load` → 解压节点包到 `invokeai-data/nodes/` → 生成 `.env`（若缺）→ `docker compose -f docker-compose.standalone.yml up -d`。
完成后服务在 `http://localhost:9090`。

**前提**：Mac Mini 装好 Docker Desktop（含 `docker compose`）。

### 3. 配 API key（必须）

编辑 `~/invokeai-deploy/.env`，填你要用的 provider（任选/多填）：

```
INVOKEAI_EXTERNAL_ALIBABACLOUD_API_KEY=sk-...   # 百炼 Wan / Qwen-Image
INVOKEAI_EXTERNAL_OPENAI_API_KEY=sk-...          # GPT Image / DALL-E
INVOKEAI_EXTERNAL_GEMINI_API_KEY=...             # Gemini 图像
INVOKEAI_EXTERNAL_SEEDREAM_API_KEY=...           # BytePlus Seedream
INVOKEAI_EXTERNAL_ATLASCLOUD_API_KEY=...         # Atlas Cloud
```

改完：

```bash
cd ~/invokeai-deploy
docker compose -f docker-compose.standalone.yml restart invokeai
```

## 节点包（zip 已含，解压即用）

`invokeai-node-packs.zip` 里是 4 个节点包（14 个节点），**不需要再下**：

| 包 | 节点 | 用途 |
|---|---|---|
| `remove-background-node` | `remove_background` | 抠图（rembg，u2net/isnet，MIT 权重） |
| `image-resize-plus-node` | `image_resize_plus` | 裁剪/缩放（crop·fill·fit·center） |
| `invoke_image_export` | `save_png/webp/avif/tiff/jpeg` | 多格式导出 |
| `composition-nodes` | `img_enhance·img_composite·offset_image·text_mask·cmyk_split·cmyk_merge·cmyk_separation` | 增强/合成/偏移/文本 mask/CMYK |

这些包依赖的 6 个 pip 包（`rembg`/`onnxruntime`/`pillow-avif-plugin`/`opencv-contrib-python`/`scipy`/`libxcb1`）已写进镜像，**无需再装**。
**首次跑 `remove_background` 会自动下载 u2net 权重**（几 MB，需联网）。

### 加新节点包（无源码也能加）

```bash
cd ~/invokeai-deploy/invokeai-data/nodes
git clone <repo-url> <pack-name>
# 若包需要额外 pip 依赖（容器 venv 在 /opt/venv，无 pip 二进制，用 uv）：
docker exec docker-invokeai-1 sh -c "cd /opt/invokeai && uv pip install --python /opt/venv/bin/python <pkg>"
docker compose -f docker-compose.standalone.yml restart invokeai
```

## 工作流

- 打开 `http://localhost:9090` → 工作流编辑器 → 左侧 **Nodes** 搜节点名拖出来连线。
- 预设 `.json` 工作流：下载后在编辑器 **Load Workflow** 导入；或在 UI 里搭好 **Save as Workflow**，薄客户端（P003 M2 的 `run-job`）直接按图调用。

## 数据与日志

- 运行时数据（DB、模型记录、生成图）在 `~/invokeai-deploy/invokeai-data/`（bind mount 到容器 `/invokeai`）。
- 日志：`cd ~/invokeai-deploy && docker compose -f docker-compose.standalone.yml logs -f invokeai`
- 停止：`docker compose -f docker-compose.standalone.yml down`

## 注意

- 无 GPU/CUDA/本地模型：纯 API 出图。本地模型相关节点（ControlNet/LoRA/VAE 类）装了也跑不通，别装。
- 抠图走 rembg（MIT 权重）；**禁用 BiRefNet**（CC-BY-NC 权重与商用冲突）。
- 中文界面：设置 → 语言 → 简体中文（翻译已打进前端 dist）。
- 端口占用：改 `.env` 的 `INVOKEAI_PORT`，`docker-compose.standalone.yml` 已引用该变量。

---

## 附录：有源码时的备选（build 方式）

如果 Mac Mini 上有完整源码，也可走 build 路线（`docker/` 下 `deploy.sh` + `docker-compose.yml`，现场 `docker compose build`）。本目录同时保留两套：

- **无源码**（推荐，本文主线）：`invokeai-api-only.tar.gz` + `invokeai-node-packs.zip` + `deploy-standalone.sh`
- **有源码**：`deploy.sh`（build）+ `docker-compose.yml`

两套都在这台机器的 `docker/` 下。无源码部署只需要前 5 个文件，不必传整个仓库。
