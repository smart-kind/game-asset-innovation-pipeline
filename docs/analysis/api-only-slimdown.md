# API-only 精简分析（InvokeAI fork）

> **范围**：本仓库是基于 InvokeAI 的 fork（Apache-2.0）。本文分析将其精简为「纯外部 API 生图服务」的可行边界、耦合点与瘦身量。分析基于分支 `analysis/api-only-slim` 上的静态统计（2026-10-27）。所有 LOC/行数为写文时的实测数字；聚合处均附简短算式。

## 1. 目标

- **API-only**：彻底移除本地模型（local model）支持，只保留外部 API provider：
  - Alibaba Cloud DashScope（Wan / Qwen-Image）
  - OpenAI（GPT Image / DALL-E）
  - Gemini
  - Atlas Cloud
  - BytePlus Seedream
- **去 GPU**：GPU/NVIDIA 已出局——不再支持 CUDA/ROCm，Docker 镜像不含 GPU 依赖。外部 provider 全部是纯 HTTP 调用，普通 CPU Python 镜像即可承载。
- **保留的核心资产**：`invokeai/app/` 的 REST API 层、session queue、invocation 图执行引擎（node engine），以及外部生图链路（见 §2.1）。

## 2. 可保留 / 可删边界

### 2.1 保留：外部 provider 架构（现状核实）

外部模型在本仓库中是**声明式**的，链路与本地模型栈基本正交：

- **声明层**：`invokeai/backend/model_manager/starter_models/external.py`（792 行）定义 `StarterModel` 条目，`source=external://<provider>/<model-id>`，格式为 `ModelFormat.ExternalApi`，能力矩阵为 `ExternalModelCapabilities`（定义在 `invokeai/backend/model_manager/configs/external_api.py`，113 行）。
- **Invocation 层**：`invokeai/app/invocations/external_image_generation.py`（379 行），`BaseExternalImageGenerationInvocation` 加各 provider 子类（OpenAI、AlibabaCloud、Gemini、Seedream、AtlasCloud）。
- **Service 层**：`invokeai/app/services/external_generation/`，共 2,013 LOC，包含 `external_generation_default.py`、`external_generation_base.py`、`external_generation_common.py`、`image_utils.py`、`startup.py`、`errors.py`，以及 `providers/` 子目录 5 个 provider（合计 1,366 行 = alibabacloud.py 417 + atlascloud.py 368 + gemini.py 248 + openai.py 162 + seedream.py 171；已含在 2,013 总数内）。
- **零重依赖已验证**：外部 provider 路径对 torch / diffusers / transformers **零硬依赖**，只用 `requests`、`PIL`（Pillow）和模型配置/存储基础设施；内部完成 SSRF 防护的下载、base64 图片编解码、带 retry/backoff 的 provider HTTP 调用。
- **启动同步**：`invokeai/app/services/external_generation/startup.py` → `sync_configured_external_starter_models()`，在启动时为已配置的 provider 注册外部 starter model 到 model manager。
- **配置面**：provider 通过外部 API key 设置配置（app config 中的 `external_alibabacloud_api_key` 等，存在 `external_generation` 配置段）；API 路由 `invokeai/app/api/routers/app_info.py` 暴露 `set_external_provider_config` / `get_external_provider_statuses`。
- **模型注册/存储**：`ExternalApiModelConfig`（`invokeai/backend/model_manager/configs/external_api.py`）是 `Config_Base` 子类；`ModelFormat.ExternalApi`、`ModelType.ExternalImageGenerator`、`BaseModelType.External` 定义在 `invokeai/backend/model_manager/taxonomy.py`。安装流程 `invokeai/app/services/model_install/model_install_default.py` 与 `model_records` 对外部模型的持久化与其他模型类型完全一致。

保留的外部链路核心总量约 3,297 LOC：792（starter models）+ 379（invocation）+ 2,013（service，含 providers）+ 113（config）≈ 3.3k。

### 2.2 删除：本地模型栈（体量）

Backend `invokeai/backend` 约 **117k LOC** Python，分布于 43 个子目录。下表中「本地架构目录」合计约 **18MB 源码**，是可以整体删除的对象（`model_manager/`、`image_util/`、`util/` 除外——它们本地/外部混用，见 §3）：

| 目录 | LOC | 角色 |
|---|---|---|
| `model_manager/` | 40,958 | 模型记录存储、安装、所有类型的 loader（外部 + 本地混合，耦合见 §3） |
| `image_util/` | 13,339 | 图像处理（大部分可复用，但部分子模块依赖 torch） |
| `util/` | 6,742 | 共享 helpers，含 `devices.py`（TorchDevice） |
| `pid/` | 6,439 | PiD decoder（本地） |
| `quantization/` | 6,239 | GGUF/SDNQ 加载（仅本地） |
| `patches/` | 5,924 | model state-dict patches（仅本地） |
| `minimax_h3/` | 5,880 | MiniMax H3 pipeline（本地） |
| `flux/` | 4,276 | FLUX 架构（本地） |
| `stable_diffusion/` | 4,223 | SD1/2 架构（本地） |
| `anima/` | 2,902 | Anima 架构 |
| `architectures/` | 2,763 | 架构 registry + 默认设置 |
| `ltx2/` | 2,684 | LTX2（视频，本地） |
| `hidiffusion/` | 2,286 | HiDiffusion |
| `ideogram4/` | 1,979 | |
| `z_image/` | 1,961 | |
| `krea2/` | 1,387 | |
| `flux2/` | 1,157 | |
| `rectified_flow/` | 752 | |
| `wan/` | 739 | |
| `fun_controlnet/` | 655 | |
| `tiles/` | 578 | |
| `ip_adapter/` | 474 | |
| `qwen_image_2_1/` | 405 | |
| `working_memory/` | 393 | |
| `ernie_image/` | 316 | |
| `model_hash/` | 279 | |
| `onnx/` | 222 | |
| `qwen3_5/`、`qwen2_5_vl/`、`qwen3_vl/`、`qwen3/`、`sd3/`、`clip/`、`t5/`、`sig_lip/` | ~2,000 | encoder/CLIP/LLM 子模块（仅本地） |

**Invocations**：`invokeai/app/invocations/` 有 168 个顶层文件（16,686 LOC 共享 utilities），加上按架构划分的 pipeline 子目录合计约 **30,056 LOC**——全部是本地 pipeline（sd、flux、flux2、wan、ltx2、minimax_h3、anima、krea2、z_image、pid、qwen_image、ideogram4、ernie_image、qwen_image_2_1、sd3、cogview4、vae、text_encoder）。仅顶层文件中依赖 torch 的部分再加约 **6,912 LOC**。

**Frontend**：`webv2` src 共 **642,615 LOC**，其中 `workbench/` = 358,270、`features/` = 248,218（含 model manager UI、外部模型设置区等）。遗留 `webv1` = **214,079 LOC**。

## 3. 依赖耦合点（难点：本地与外部交错处）

以下 6 处是精简时必须手工处理的耦合（含具体行号）：

1. **`invokeai/backend/model_manager/configs/factory.py`（1,023 行）**：`AnyModelConfig` 这个 pydantic `Union` 列出了全部 config 类——约 100 个本地 checkpoint/LoRA/VAE/encoder config，外加 `ExternalApiModelConfig`（在第 619 行）。`ModelConfigFactory.from_model_on_disk` 遍历 `Config_Base.CONFIG_CLASSES`。裁剪这个 Union 是机械操作，但必须保留 external config 与磁盘扫描兜底项（`Unknown_Config`）。
2. **`invokeai/app/run_app.py`**：第 110 行 `from invokeai.backend.krea2.attention import resolve_krea2_sdpa_backends`；第 95 行 `from invokeai.backend.util.devices import TorchDevice`——**启动路径上的硬耦合**。
3. **`invokeai/app/api/dependencies.py`**：第 75 行 `from invokeai.backend.stable_diffusion.diffusion.conditioning_data import ConditioningFieldData`——虽然只是纯 dataclass 导入，仍是对本地架构目录的引用。
4. **`invokeai/app/services/invocation_services.py`**：引用 torch 与 minimax_h3。
5. **`invokeai/app/services/shared/invocation_context.py`** 与 **`invokeai/app/services/shared/sqlite_migrator/migrations/migration_2026_09_07_add_minimax_h3_ref2va_system_prompt.py`**：引用 minimax_h3。
6. **`invokeai/app/util/`** 下的 `torch_cuda_allocator.py`、`rocm_aotriton.py`、`startup_utils.py`、`controlnet_utils.py`：import torch。

## 4. 可瘦身量估算

- **Backend**：总量约 117k LOC。表中剔除 `model_manager/`（40,958）、`image_util/`（13,339）、`util/`（6,742）三个混用目录后，其余 27 个纯本地架构目录合计约 **56.9k LOC**（6,439+6,239+5,924+5,880+4,276+4,223+2,902+2,763+2,684+2,286+1,979+1,961+1,387+1,157+752+739+655+578+474+405+393+316+279+222+~2,000）。叠加 `model_manager/` 的大部分、`util/` 的 torch 部分与 `image_util/` 的 torch 子模块，**可删的 local-only 总量估约 85–90k LOC**；需选择性保留拆分的约 27–32k（≈117k − 85~90k），主要是外部链路依赖的 model record store、install、config/taxonomy 子集。
- **Invocations**：本地 pipeline 子目录约 **30,056 LOC** 可整删；顶层 168 个文件中 torch 依赖部分约 **6,912 LOC** 需逐个甄别（外部生图 `external_image_generation.py` 379 行明确保留）。顶层共享 utilities（16,686 LOC）中哪些留下要按 import 图核，不能整体删。
- **Frontend**：最大剩余重量是 `webv2` 的 `workbench/`（358,270 LOC）。API-only 形态下两条路：出 headless 构建（完全不打前端），或保留 API 调试 UI 但删 model manager UI 中本地 checkpoint 相关段（在 `features/` 248,218 LOC 内）。`webv1` 214,079 LOC 属遗留代码，可**整体安全删除**。
- **Docker**：`docker/` 构建可彻底去掉 cuda/rocm build args，改为 plain CPU Python 镜像——外部 provider 是纯 HTTP，无 GPU/重型 Python 依赖（见 §2.1「零重依赖已验证」）。

**安全删 vs 需谨慎**：纯架构目录（56.9k）、`webv1`、本地 pipeline invocation 子目录、docker GPU 参数——可整删，安全。`model_manager/`、`image_util/`、`util/`、顶层 invocations、`factory.py` Union、`webv2 workbench`——混用或引用面广，需按 §3 逐点处理。

## 5. 实施顺序建议

分四阶段，每阶段可独立验证——外部链路测试集全绿即证明该阶段没有误伤保留功能：

1. **裁剪依赖声明**：先在 `pyproject` 层面去掉 torch / diffusers / transformers 等（此步会立即暴露 §3 的启动路径耦合，需同步处理 `run_app.py`、`invocation_services.py`、`app/util/` 的 torch 引用）。
2. **删 backend 目录**：按 §2.2 表先删 27 个纯架构目录（约 56.9k LOC），再对 `model_manager/` / `image_util/` / `util/` 做选择性拆分，保留 §2.1 外部链路所需的子集。
3. **删 invocations**：先删本地 pipeline 子目录（约 30k LOC），再逐个清理顶层 torch-dependent 文件（约 6,912 LOC），保留 `external_image_generation.py`。
4. **删 frontend / 出 headless**：整体删除 `webv1`；`webv2` 按 §4 二选一（headless 构建，或剪掉 model manager 本地模型 UI 段）；同步简化 `docker/`（去 cuda/rocm args；API-only 可直接跳过 webv1 构建，见 §6）。

每阶段验证命令（只跑外部相关测试，不跑全量）：

```bash
uv run --no-sync pytest tests/app/services/external_generation/
uv run --no-sync pytest tests/app/invocations/test_external_image_generation.py
uv run --no-sync pytest tests/app/routers/test_model_manager.py   # external 段落
uv run --no-sync pytest tests/app/routers/test_app_info.py         # external provider config 用例
```

## 6. 风险

1. **`factory.py` Union 裁剪**：牵动约 100 个 config 类（`invokeai/backend/model_manager/configs/factory.py`，1,023 行），删多了会破坏 `ModelConfigFactory` 的反序列化，删少了 external 路径不变；必须同时保住 `ExternalApiModelConfig`（第 619 行）与磁盘扫描兜底 `Unknown_Config`。
2. **`app/` 层对本地架构目录的残留引用**：§3 所列 6 处（`run_app.py`、`dependencies.py`、`invocation_services.py`、`invocation_context.py` 及 minimax_h3 migration、`app/util/` 四个 torch 文件）任何一处漏处理，都会在启动或 API 请求时抛 ImportError；其中 sqlite migration 文件引用 minimax_h3 属于**历史迁移**，删除该模型代码前需确认 migration 是否仍要求 import 其常量。
3. **model_manager 磁盘扫描探测本地格式**：对本地 checkpoint 格式的 disk probing 在对应 loader/格式模块被删后，可能因引用缺失目录或类而抛异常，需要把扫描范围收窄到 external + `Unknown_Config` 兜底路径。
4. **Docker 构建链**：当前 `docker/` 构建会跑 pnpm 同时构建 webv1 与 webv2；API-only 下 webv1 可整体跳过，但若直接删目录而不同步改构建脚本，会在镜像构建阶段失败——两者要同一改动内完成。

## 7. 实施记录（`api-only-slim` 分支，按 §5 四阶段执行）

1. **裁剪依赖声明（§5.1）**：`pyproject.toml` 删除整个「Core generation dependencies」块（accelerate / bitsandbytes / compel / diffusers / gguf / mediapipe / mistral-common / onnx / onnxruntime / opencv / imageio / psutil / safetensors / sentencepiece / spandrel / torch / torchvision / torchsde / transformers 及其平台变体），删除 `xformers` / `cpu` / `cuda` / `rocm` / `mysql` extras 与 `[tool.uv]` 中所有 torch/rocm/nvidia 索引与约束；保留 REST API 应用依赖（fastapi / sqlalchemy / pillow / requests / pypatchmatch 等，pypatchmatch 缺失时优雅降级）。同步处理启动路径耦合：`run_app.py` 删除 torch allocator / ROCm / AOTriton / `TorchDevice` / `resolve_krea2_sdpa_backends` 等启动块；`startup_utils.py` 顶层 `import torch` 改惰性，`apply_monkeypatches` 无 torch 时 early-return；`taxonomy.py` 删除 `AnyModel` TypeAlias 及其 torch/diffusers/onnxruntime 顶层 import（该别名全部引用方都是本地 pipeline 模块，随 §5.3 一并删除）。
2. **解耦混用目录（§5.2 的前置）**：backend 纯架构目录整体删除；`model_manager` 保留外部链路子集——`model_on_disk.py` 权重读取（safetensors/gguf/quantization loader）改函数内惰性导入，元数据/hash 路径保持无 torch；`configs/` 删除全部本地 config 模块，`factory.py` 的 `AnyModelConfig` Union 收窄为 `ExternalApiModelConfig` + `Unknown_Config`；`starter_models/` 仅保留 `external.py`。`model_load` 默认实现替换为 no-op（`load_model` 抛「API-only build 禁用本地加载」），`model_manager_default.reidentify_model` 仅保留 external 路径（非 external 记录返回 400）。`image_util/` 保留 PIL 纯操作与 `infill_methods`（patchmatch 降级），删除 torch 子模块；`util/devices.py`（`TorchDevice`）删除，`invocation_context` 的引用改惰性 try/except。
3. **删除 invocations 本地管线（§5.3）**：18 个本地 pipeline 子目录（sd/flux/flux2/wan/ltx2/minimax_h3/anima/krea2/z_image/pid/qwen_image/qwen_image_2_1/ideogram4/ernie_image/sd3/cogview4/vae/text_encoder）整体删除；顶层 torch 依赖文件逐甄别，保留 `external_image_generation.py` 及 torch-free 共享 utilities。`invocations/__init__.py` 的 `load_all_modules()` 动态发现机制不变，删除后仅剩 27 个模块（baseinvocation / fields / image / external_image_generation 等），graph 引擎在精简 invocations 集合上正常注册。
4. **前端与 Docker（§5.4）**：`webv1` 整体删除；`webv2` 保留（UI 仍可冒烟，后续可决策 headless）。`docker/`：Dockerfile 去 webv1 构建层、去 `GPU_DRIVER` build-arg、去 opencv/patchmatch 编译与 ROCm 软链、`uv sync --frozen`（无 extra）；compose 收为单服务 `invokeai`（无 nvidia/amd runtime）；entrypoint 去 ROCm render-group 与 SSH 段；`.env.sample` 补 `INVOKEAI_EXTERNAL_*_API_KEY` 五项 provider key 说明。
5. **验证**：slim venv（无 torch/diffusers/safetensors/gguf/onnxruntime）下四组外部测试 558 passed（`tests/app/services/external_generation/` + `test_external_image_generation.py` + `test_app_info.py` + `test_model_manager.py`）；`invokeai.app.api_app` 与 `load_all_modules()` 在无 torch 环境 import 通过；`patchmatch_status` 端点在 pypatchmatch 缺失时优雅返回不可用。

遗留：`docs/` 与 `tests/AGENTS.md` 中提及本地模型的段落未同步（不影响运行）；webv2 UI 中本地模型管理面板仍会显示但功能禁用；`.dev_scripts/` 本地模型回归脚本未删。

---

*本文档为工程分析，非执行计划；数字与路径以 `analysis/api-only-slim` 分支上的仓库现状为准。§7 为 `api-only-slim` 分支的实施记录。*
