---
name: model-router
description: Switch the global default model/provider for OpenClaw by editing the live gateway config. Use when the user asks to切换默认模型、切换 provider、改 baseUrl/apiKey、添加新模型通道，尤其是在官方 Dashboard 的 Chat 中用自然语言下达这类命令时。
---

# Model Router

用于把“切换全局默认模型 / 新增模型通道 / 修改 provider 的 baseUrl 或 apiKey”这类命令，映射为对 OpenClaw 配置的安全修改。

## 触发场景

- “把全局默认模型切到 lck/gpt-5.4”
- “把默认模型改成 qwen/coder”
- “新增一个 provider，baseUrl 是 ...，apiKey 是 ...，模型是 ...”
- “把当前默认模型换成更便宜的通道”

## 原则

- 先读当前配置，再改；不要盲写。
- 优先修改 `agents.defaults.model.primary`。
- 如目标 provider / model 不存在，则同时补齐：
  - `models.providers.<provider>`
  - `agents.defaults.models.<provider/model>`
- 这是配置变更，完成后应明确告知用户：**可能需要重启 gateway 才能让所有旧会话完全吃到新默认值**。
- 如果只是新开会话或显式指定模型，通常无需等待太久。

## 操作流程

1. 读取当前配置：优先使用 `gateway config.get` / `gateway config.schema`，必要时读取 `/root/.openclaw/openclaw.json`。
2. 确认目标：
   - 目标 provider 名
   - 目标 model id
   - 若用户提供了新通道，则记录 baseUrl / apiKey / api 类型
3. 修改配置：
   - 设置 `agents.defaults.model.primary = "provider/model"`
   - 确保 `agents.defaults.models."provider/model"` 存在，可写 alias
   - 若 provider 不存在，则补齐 `models.providers.<provider>`
4. 若用户明确要求“立即全局生效”，优先使用 `gateway config.patch`；需要时告知可能重启。
5. 汇报时只给出：
   - 切换前默认模型
   - 切换后默认模型
   - 是否新增了 provider / model
   - 是否需要重启

## 常见映射

- `lck` -> `lck/gpt-5.4`
- `qwen` -> `qwen-portal/coder-model`

## 禁止事项

- 不要随意删除旧 provider。
- 不要在未确认的情况下覆盖用户现有 apiKey。
- 不要把“切换默认模型”和“批量重构所有脚本硬编码”混为一谈；后者需要单独授权。
