# 改造方案：API-only 资产生成引擎（基于 InvokeAI 裁剪）

**项目**：P003 游戏美术资产流水线 · 线 2
**仓库**：github.com/smart-kind/game-asset-innovation-pipeline
**基座**：invoke-ai/InvokeAI（Apache-2.0）
**本仓库定位**：从 InvokeAI 裁剪而来的 **API-only 图像编辑/生成引擎**——砍掉本地模型与 GUI 重负载，只保留 REST API 驱动的核心，供薄客户端与 Agent 调度。

---

## 0. 目标与非目标

**目标**
- 只保留 External Providers（百炼 Wan / OpenAI GPT Image / Gemini Nano Banana / BytePlus）作为模型来源
- 保留生成管线（generate / img2img / inpaint / outpaint / upscale / style reference / IP-Adapter / ControlNet 透传）
- 保留 REST API + 队列（Agent 可无头驱动）
- 输出可被流水线消费（PNG / 透明 PNG + 元数据）

**非目标（本版不做）**
- 本地模型（SD1.5/SDXL/Flux/CogView/Z-Image/Qwen-Image 本地版）的加载、显存管理
- 本地模型下载/管理界面
- GUI 画布（Unified Canvas）——用外部查看器替代
- LoRA 训练、模型微调

---

## 1. 裁剪范围（要砍的）

| 模块 | 处理 |
|---|---|
| 本地模型引擎（diffusers/ckpt 加载） | **删** |
| Model Manager（本地模型下载/管理） | **删** |
| GPU 调度 / 显存监控 | **删** |
| Unified Canvas（WebUI 画布） | **删**（保留其调用的生成节点） |
| Gallery/Board 重负载 GUI | **降**为轻量列表（或直接删，用 REST 查询） |
| LoRA 训练 / 微调 | **删** |
| 本地 SAM / 分割模型 | **删**（抠图改走 rembg 流水线） |

**保留**
- 节点图（workflow）引擎 + 生成节点（文生图/img2img/inpaint/outpaint/upscale/style-ref/IPA/ControlNet）
- External Providers 适配层（百炼/OpenAI/Gemini/BytePlus）
- 队列、结果回传、元数据（prompt/seed/params）
- REST API（`/docs` Swagger + 生成/队列/Recall 参数端点）
- 最小 WebUI：只留"生成"与"结果查看"两屏，够冒烟用（可后置）

> 原则：InvokeAI 的节点引擎是核心资产，砍的是"本地模型 + 重 GUI"，不是砍引擎。

## 2. 新增（要做的）

1. **薄客户端 CLI**（见 P003 主方案 M2）：import-url / sync-dir / run-job / 抠图 / 超分 / sidecar
2. **Cocos loader**（见 cocos-ui-loader-design.md，走 feedback 执行）：JSON 物化场景 + 运行态 loader
3. **抠图步**：rembg（u2net/isnet，MIT/Apache 权重）；**禁 BiRefNet**（CC-BY-NC，与广告变现商用冲突）
4. **External Providers 参数补全**：若 InvokeAI 未把"参考图 + mask + 垫图强度"完整透传给 Wan/OpenAI，在 provider 层补字段

## 3. 技术选型

- 运行时：Python（跟随 InvokeAI 本体，避免大改）
- 包管理：venv + 依赖裁剪（去掉 diffusers/transformers 本地模型依赖，保留 httpx/pydantic/FastAPI）
- 部署：Docker（官方 docker/ 改造，去掉 nvidia runtime 依赖）
- 版本：基于 InvokeAI 最新 Community Edition（含 Alibaba Cloud external provider 的那个 release）

## 4. License 与合规

- 基座 InvokeAI = Apache-2.0：fork、裁剪、再开源均合法；**保留原 LICENSE 与 NOTICE**
- 权重：只用 MIT / Apache 权重（u2net/isnet）；禁用 CC-BY-NC（BiRefNet）
- 生成结果商用：百炼 Wan / OpenAI GPT Image 按各自服务条款；API 付费调用无碍
- 本仓库作为 smart-kind 下开源项目，License 建议保持 Apache-2.0（与基座一致，避免混牌）

## 5. 实施里程碑

| 里程碑 | 内容 | 备注 |
|---|---|---|
| E0 | 克隆 InvokeAI + 建 smart-kind 仓库 + 本方案 | 已完成 |
| E1 | 裁依赖 + 本地起服务（External Providers 冒烟） | 删 diffusers 本地栈 |
| E2 | 裁剪重 GUI，留 REST + 最小生成页 | 队列/结果查看可用 |
| E3 | provider 参数透传补全（ref+mask+垫图强度） | 对照百炼 Wan 文档 |
| E4 | 薄客户端 CLI 打通（run-job 调本服务） | 与 P003 M2 合并 |
| E5 | 发布 v0.1 + 开源 | 保留 Apache-2.0 头 |

## 6. 风险

- 裁得过多 → 节点引擎依赖本地模型的内部调用残留（E1 需全量 grep 本地模型引用）
- External Providers 参数不全（E3 可能需改 InvokeAI 源码，Apache-2.0 允许）
- 版本漂移：基座 InvokeAI 迭代快，定期 rebase 时注意裁剪 patch 冲突
