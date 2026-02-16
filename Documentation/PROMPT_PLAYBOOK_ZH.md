# Prompt 玩法规范（中文，严格 SOP）

本规范用于 `codex-mem` 的 `ask` 工作流。目标是让项目学习、问答、排障、实现都走统一的可验证流程，而不是靠长 prompt 或临场发挥。

## 1. 适用范围

- 适用于 `ask` 四类场景：`onboarding`、`daily_qa`、`bug_triage`、`implementation`
- 适用于“第一次阅读项目”与“后续增量提问”
- 适用于需要证据化输出的协作场景

## 2. 硬性规则（必须遵守）

1. 用户输入保持短句任务描述，不写长模板提示词。
2. 第一阅读必须按顺序执行：
   - 自上而下：目标 -> 架构 -> 模块边界 -> 主流程
   - 自下而上：入口 -> 关键模块 -> 关键函数/数据路径
3. onboarding 必须覆盖三个类别：
   - `entrypoint`
   - `persistence`
   - `ai_generation`
4. 关键结论必须附证据：
   - 文件路径
   - 函数/类/符号
   - 命令输出摘要（如执行过命令）
5. 禁止自造 KPI、百分比或硬目标。
   - 数字结论只能引用仓库已有 benchmark 文件。

## 2.1 底层逻辑识别锚点（写进提问）

为确保命中 `onboarding` 路由与核心链路，第一阅读提问中建议至少包含以下锚点中的 4 项以上：
- 北极星 / north star
- 架构 / architecture
- 模块地图 / module map
- 入口 / entrypoint
- 主流程 / main flow
- 持久化 / persistence
- AI 生成链路 / ai generation
- 风险 / risks

并在问题末尾追加一行自检要求：
- `请返回 mapping_decision、coverage_gate、prompt_plan、prompt_metrics 四个字段用于验收。`

## 3. 第一阅读 SOP（严格执行）

### 步骤 1：执行 onboarding 提问

```bash
python3 Scripts/codex_mem.py --root . ask \
  "learn this project: north star, architecture, module map, entrypoint, main flow, persistence, ai generation, risks

请返回 mapping_decision、coverage_gate、prompt_plan、prompt_metrics 四个字段用于验收。" \
  --project demo
```

### 步骤 2：执行路由与覆盖校验（第一阅读必做）

```bash
python3 Scripts/codex_mem.py --root . ask \
  "learn this project: north star, architecture, module map, entrypoint, persistence, risks" \
  --project demo --mapping-debug
```

### 步骤 3：按固定结构输出阅读结果

必须包含以下小节：
- 北极星与边界
- 架构与模块地图
- 主流程（输入 -> 处理 -> 持久化 -> 输出）
- `entrypoint` / `persistence` / `ai_generation` 证据表
- 主要风险与待确认项

### 步骤 4：完成闸门（Pass/Fail）

只有全部满足才算“第一阅读完成”：
- `coverage_gate.pass = true`
- 固定小节齐全
- 无无证据结论
- 无自定义数字目标

任一不满足，必须输出 `INCOMPLETE` 并列出缺失证据。

## 4. 标准短输入（推荐）

- onboarding：`learn this repo architecture and risks`
- 日常问答：`why did this flow fail yesterday`
- 排障：`triage crash in startup path`
- 实现：`implement compact renderer with compatibility`

## 5. 常用命令模板

### 冷启动学习

```bash
python3 Scripts/codex_mem.py --root . ask \
  "learn this project: architecture, entrypoint, persistence, risks" \
  --project demo
```

### 日常增量问答

```bash
python3 Scripts/codex_mem.py --root . ask "what changed in generation flow" --project demo
```

### 强制本地路由

```bash
python3 Scripts/codex_mem.py --root . ask \
  "what changed in generation flow" \
  --project demo --mapping-fallback off
```

### 回归对比（仅测试）

```bash
python3 Scripts/codex_mem.py --root . ask \
  "learn this repo architecture and top risks" \
  --project demo --prompt-style legacy
```

## 6. 输出字段解读（compact）

- `mapping_decision`：路由来源、置信度、低置信标记
- `coverage_gate`：必需类别覆盖情况与 pass/fail
- `prompt_plan`：预算分配与证据选择
- `prompt_metrics`：渲染后大小与预算使用

兼容字段：
- `suggested_prompt`
- `token_estimate`

## 7. 执行口令（给助手）

你必须遵循本文件 SOP。  
优先短提示词，严格第一阅读流程，严格证据化结论。  
若覆盖闸门未通过或证据不足，直接输出 `INCOMPLETE`，不得伪造完成状态。

## 8. 系统强制输出契约（对用户）

`ask` 结果必须包含 `forced_next_input` 字段，且不可省略。  
该字段用于给用户下一条“可直接执行”的跨项目输入指令，至少包含：
- `required_output_fields`：`mapping_decision`、`coverage_gate`、`prompt_plan`、`prompt_metrics`
- `next_input.command_template_zh` / `next_input.command_template_en`
- `next_input.prompt_template_zh` / `next_input.prompt_template_en`
- 当覆盖未通过时，必须包含 `next_input.refine_prompt_zh`

不允许只返回抽象建议；必须返回可执行命令模板与可复用 prompt 模板。
