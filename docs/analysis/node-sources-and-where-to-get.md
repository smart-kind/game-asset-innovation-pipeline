# 节点包与预设工作流：从哪儿拿、怎么装

> 适用：`api-only-slim` 分支（InvokeAI fork，外部 provider 生图 + 节点引擎）。
> 最后更新：2026-10-27。

## 两个概念先分清

| 概念 | 是什么 | 从哪拿 |
|---|---|---|
| **节点包（node pack）** | 一段 Python 代码，注册新的 Invocation 节点（如抠图、打码、网格化）。装进 `INVOKEAI_ROOT/nodes/` 目录 | GitHub 上的社区仓库（[官方清单](#官方-community-nodes-清单)），或 webv2 UI 的 **Nodes → 粘贴 Git URL 安装** |
| **预设工作流（workflow）** | 一个 `.json` 节点图文件，把一组节点连好的成品方案（如"放大工作流"、"文字 mask 工作流"） | 各节点包仓库里附带的 example workflow（见 [官方清单](#官方-community-nodes-清单)），webv2 UI 里 **Load Workflow** 按钮导入 |

UI 入口（webv2）：左侧 **Nodes** 侧栏 → 粘贴 GitHub 仓库 URL → 安装节点包；工作流编辑器顶部 **Load Workflow** → 选择 `.json` 文件加载。REST 接口对应 `invokeai/app/api/routers/custom_nodes.py`（`POST /api/v2/custom_nodes/install` 等，见 [Swagger](http://localhost:9090/docs)）。

## 装节点包（手动方式，容器内）

容器内自定义节点目录：`/invokeai/nodes/`（host 侧挂载卷 `./invokeai-data/nodes/`）。

```bash
# 例：装 rembg 抠图节点包（P003 抠图步要用）
cd invokeai-data/nodes
git clone https://github.com/VeyDlin/remove-background-node.git
# 该包需要 rembg 依赖，进 venv 装：
docker exec docker-invokeai-1 /opt/venv/bin/pip install rembg
# 重启容器使新节点生效
cd docker && docker compose restart
```

注意：
- 每个节点包目录必须带 `__init__.py`，里面 import 节点模块才加载（格式见容器内 `/invokeai/nodes/README.md`，即 `invokeai/app/invocations/custom_nodes/README.md` 的副本）。
- 节点包是第三方代码，用前看下它 import 什么、依赖什么——P003 的 License 原则：**禁用 CC-BY-NC 权重**（BiRefNet 即 CC-BY-NC，见 `docs/invokeai-api-only-mod-plan.md` §4），抠图走 rembg（u2net/isnet，MIT/Apache 权重）。
- 节点包需要额外 pip 依赖的，用 `docker exec docker-invokeai-1 /opt/venv/bin/pip install <pkg>` 装（容器 venv 在 `/opt/venv`）。装完不用重建镜像，但**要 restart 容器**让节点重新注册。

## 官方 Community Nodes 清单

来源：[invoke.ai/features/workflows/community-nodes](https://invoke.ai/features/workflows/community-nodes/)（官方维护的社区节点列表），仓库全在 GitHub：

**P003 流水线相关（抠图/后处理）**
- [remove-background-node](https://github.com/VeyDlin/remove-background-node) — rembg 抠图（u2net/isnet，MIT/Apache 权重）✅ 推荐
- [invoke_image_export](https://github.com/veeliks/invoke_image_export) — 多格式导出（AVIF/JPEG/PNG/TIFF/WebP）✅ 出图流水线要用
- [clean-artifact-after-cut-node](https://github.com/VeyDlin/clean-artifact-after-cut-node) — 抠图后残影清理
- [clahe-node](https://github.com/VeyDlin/clahe-node) — 局部对比度增强
- [image-resize-plus-node](https://github.com/VeyDlin/image-resize-plus-node) — fill/stretch/fit/center/crop 多种缩放

**工作流模板（带 example .json 的）**
- [XYGrid_nodes](https://github.com/skunkworxdark/XYGrid_nodes) — 分块放大 + 网格拼回（附 example workflow）
- [Ollama-Node](https://github.com/Jonseed/Ollama-Node) — 本地 LLM 扩写 prompt（附 [Flux 示例图](https://github.com/Jonseed/Ollama-Node/blob/main/Ollama-Node-Flux-example.json)）
- [shift3d](https://gitlab.com/srcrr/shift3d) — 2D→3D 立体图（[示例工作流](https://gitlab.com/srcrr/shift3d/-/raw/main/example-workflow.json)）
- [GridToGifNode](https://github.com/mildmisery/invokeai-GridToGifNode) — 网格转 GIF（[示例工作流](https://github.com/mildmisery/invokeai-GridToGifNode/blob/main/Grid%20to%20Gif%20Example%20Workflow.json)）
- [composition-nodes](https://github.com/dwringer/composition-nodes) — 15 个图像/遮罩合成节点（含 Text to Mask、图层混合、Offset 等）

**其它（按需）**
- [anammorphic-tools](https://github.com/JPPhoto/anamorphic-tools)（anamorphic 镜头效果）、[film-grain-node](https://github.com/JPPhoto/film-grain-node)、[halftone-node](https://github.com/JPPhoto/halftone-node) — 风格化
- [one-button-prompt](https://github.com/AIrjen/OneButtonPrompt_X_InvokeAI)、[Prompt-tools-nodes](https://github.com/skunkworxdark/Prompt-tools-nodes) — 提示词工具
- [load_video_frame](https://github.com/helix4u/load_video_frame)、[GridToGifNode](https://github.com/mildmisery/invokeai-GridToGifNode) — 视频帧/动画

> 官方原话：社区节点由社区开发，InvokeAI 不保证其可靠性/安全性，出问题去官方 Discord 反馈。

## 预设工作流（成品 .json）的其它来源

- **官方仓库自带**：`invoke-ai/InvokeAI` 的 [docs/workflows/](https://github.com/invoke-ai/InvokeAI/tree/docs/docs/workflows) 目录（如 `Prompt_from_File.json`）。
- **Discord / 社区分享**：官方 Discord 频道经常有人贴工作流 JSON，下载后直接 **Load Workflow** 导入。
- **自建**：在 webv2 工作流编辑器里拖好节点连好线，**Save as Workflow** 存成项目内工作流；导出 `.json` 给薄客户端（P003 M2 的 `run-job`）按图调用。

## API-only 模式下的注意事项

1. **本地模型节点装了也跑不通**：社区节点里很多依赖本地 torch 管线（ControlNet/LoRA/VAE 类，如 `adapters-linked-nodes`、`latent-upscale`、`enhance-detail-node`），本分支已删本地模型栈，装了会在运行时报错。选节点包时优先**纯 PIL/numpy/HTTP 类**（抠图、导出、风格滤镜、prompt 工具、远程图加载）。
2. **抠图推荐 rembg 而不是 BiRefNet**：BiRefNet 权重 CC-BY-NC，与 P003 广告变现商用冲突（mod-plan §4 明令禁用）；rembg 默认 u2net/isnet 是 MIT/Apache 权重。
3. 装节点包 + 额外 pip 依赖后，**容器 restart 而非重建镜像**；但 pip 装的东西重启容器会保留（在 `/opt/venv` 里，不在卷里）——如果要重建镜像才丢。想固化进镜像的话把依赖加进 `pyproject.toml` 再 build。
4. 节点包注册进 `InvocationRegistry` 后，薄客户端的 `run-job` 按节点图调用时无需改代码——新节点名直接写进工作流 JSON 即可。
