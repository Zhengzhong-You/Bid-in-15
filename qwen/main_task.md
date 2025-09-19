Great—下面给你一个**一站式、可直接跑**的实现（按你的 1–3 步需求整合好），并且把「长对话（自动拼接历史）」也做进去了。你可以把这些代码丢给 **Claude** 或直接在你本机/集群执行；核心执行对象始终是 **Qwen (7B)**，Claude 在这里仅是帮你“写代码/运行代码”的助手。

---

## 📦 你将得到的文件（可下载）

* **控制脚本（All-in-One）**：[`qwen_controller.py`](sandbox:/mnt/data/qwen_game/qwen_controller.py)
* **依赖列表**：[`requirements.txt`](sandbox:/mnt/data/qwen_game/requirements.txt)

> 说明：我没有真的在这里帮你生成 19,500 个空文件（怕占你磁盘），但 `qwen_controller.py` 里有 **prepare-logs** 子命令，一条命令就能批量建立占位文件（`log_{cfg}cfg_{min}min_{ins}ins.txt`）。

---

## 🧰 功能概览（与你的 3 点对应）

1. **加载并自测 Qwen（Smoke Test）**

    * 调用 `transformers + bitsandbytes`，以 **4-bit (NF4, BF16 compute)** 加载 `Qwen/Qwen2.5-7B-Instruct`（可改为任意 Qwen-7B）。
    * 一条简单提示词验证「能生成」即可。

2. **准备占位日志文件**

    * 文件名严格按你格式：`log_1cfg_1min_1ins.txt`
    * 范围：`cfg ∈ [1..10]`，`min ∈ [1..5]`，`ins ∈ [1..390]` → 共 `10 * 5 * 390` 个空文件。
    * 目录可自定义（默认 `./logs`）。**真的会创建那么多空文件**，请在你机器上执行。

3. **「Game」总控（5 分钟预算的试验回合）**

    * 设定 **总预算 5 分钟**，Qwen 作为专家在 10 个配置里决定每一步要试哪个 `cfg`、用几分钟 `min`。
    * 每轮把对应日志 **（自动清除 instance 标识）** 读入并“喂给”Qwen；Qwen再根据日志调整下一轮（比如把 2min 改为 1min 等）。
    * 预算用完后，Qwen **总结所有轮次** 并输出 **最终选择的参数**。
    * 全过程会记录成**长对话与 JSONL 历史**（像 ChatGPT 那样自动拼接上下文），文件在 `--history-dir` 下。

---

## 🚀 快速开始（H100 推荐环境）

> 你可以让 **Claude** 帮你在一台 H100 节点上执行以下命令，或者自己运行：

```bash
# 1) 创建并激活环境（conda 示例）
conda create -y -n qwen-h100 python=3.10
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate qwen-h100

# 2) 安装 PyTorch (CUDA 12.1 轮子，适配 H100)
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio

# 3) 安装依赖
pip install -r requirements.txt
# 若你没下载 requirements.txt，可用：
# pip install "transformers>=4.44.2" "accelerate>=0.33.0" "peft>=0.12.0" "bitsandbytes>=0.44.0" sentencepiece psutil numpy
```

---

## 🧪 用法

> 下面的脚本入口都在 [`qwen_controller.py`](sandbox:/mnt/data/qwen_game/qwen_controller.py)。

### A. 自检 Qwen 是否能跑

```bash
python qwen_controller.py smoke-test --model Qwen/Qwen2.5-7B-Instruct
# 成功会打印一条简短回答，如 "Qwen smoke test OK..."
```

### B. 批量创建占位日志（10*5*390 空文件）

```bash
python qwen_controller.py prepare-logs --logs-dir ./logs
# 会输出 "Prepared 19500 empty log files under ./logs"
```

> 文件命名规则示例：`./logs/log_2cfg_1min_37ins.txt`
> **注意：** 确认磁盘空间与 inode 充足（19,500 个文件）。

### C. 运行「Game」（长对话 & 最终参数）

```bash
python qwen_controller.py run-game \
  --ins 1 \
  --logs-dir ./logs \
  --history-dir ./history \
  --model Qwen/Qwen2.5-7B-Instruct
```

运行后会输出一个 JSON 概览，并在 `./history` 目录生成：

* `transcript_ins1.txt`：**长对话**（包含系统提示、每轮决策、工具日志回传、最终总结）
* `history_ins1.jsonl`：结构化历史（便于程序读取/审计）

---

## 🧩 设计要点（与你的细节需求对齐）

* **持续对话**：脚本内部维护 `messages`（系统/用户/助手/工具）→ 每一轮都拼接历史再问 Qwen。
* **5 分钟预算**：每轮 Qwen 只在 `1..5min` 内决策，脚本自动 **clamp** 不超预算。
* **文件名协议**：准确按 `log_{cfg}cfg_{min}min_{ins}ins.txt`；如果文件缺失会自动建空文件。
* **日志脱敏**：`sanitize_log()` 会在喂给 Qwen 前移除 `ins=xxx`、`xxxins`、`instance 123` 等 **实例标识**。
* **鲁棒 JSON**：每次让 Qwen **按 JSON schema** 回复；若夹杂文字，会从生成文本中**提取第一段 JSON**。
* **最终决策**：预算耗尽后，切换到 “总结系统提示”，Qwen 输出 `{final_cfg, rationale, trial_brief[]}`。
* **模型可替换**：`--model Qwen/Qwen1.5-7B-Chat` 或你本地路径都行。
* **量化**：默认 4-bit（NF4），H100 上 `torch_dtype=bfloat16` 计算。

---

## 🧠 给 Claude 的一句话指令（可复制粘贴）

> 下面这段可以直接发给 Claude，让它帮你在一台装好 CUDA 驱动的机器上执行并协助排错：

```
你是代码执行助手。请在一台有 H100 的 Linux 机器上完成以下操作：

1) 用 conda 创建 python=3.10 的环境并激活；安装 PyTorch cu121 轮子；安装 transformers/accelerate/peft/bitsandbytes/sentencepiece 等依赖。
2) 将用户提供的 qwen_controller.py 与 requirements.txt 放到当前目录，按其中说明先做 smoke-test。
3) 执行：python qwen_controller.py prepare-logs --logs-dir ./logs
4) 执行：python qwen_controller.py run-game --ins 1 --logs-dir ./logs --history-dir ./history
5) 若出现 JSON 解析或显存等问题，回显完整错误与已尝试的修复步骤。
```

---

## 🔧 额外提示

* **空日志策略**：当前占位日志是空的，Qwen 仍会“按流程”给出探索→利用的建议。如果你后续把真实 solver 日志写进去（覆盖对应文件），Qwen 就能据此做更有信息量的下一步选择。
* **多实例批量跑**：用外层脚本/Slurm 循环 `--ins 1..390` 即可；每个实例各自生成 `transcript_ins*.txt` 和 `history_ins*.jsonl`。
* **进行中断**：中途中断后再次 `run-game` 会重新开始本轮（当前脚本未做断点续跑，你可以基于 `history_ins*.jsonl` 很容易加上）。

---

需要我把这套再封装一个 **Slurm 单卡/多卡** 的 sbatch 模板（加载环境 + 逐实例循环）吗？我可以按你集群的 `module` 习惯把 CUDA 模块与资源约束一起写好。
