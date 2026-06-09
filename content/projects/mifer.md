---
title: Mifer — 基于 Eino 的 AI Agent 终端助手
date: 2026-06-09T12:00:00+08:00
draft: false
tags: ["Go", "AI", "Eino", "Agent", "TUI", "LLM", "MCP", "RAG"]
---

[项目源码](https://github.com/mife-user/mifer)

## 前言

Mifer 是一个基于字节跳动开源 [CloudWeGo Eino](https://github.com/cloudwego/eino) 框架构建的智能 AI Agent 桌面应用。它提供 CLI（TUI）+ HTTP 双模交互，支持多 LLM 后端、多 Agent 编排协作、流式对话、MCP 协议工具扩展、Skills 技能系统、RAG 检索增强、对话回退等能力。一句话定位：**可编程、可扩展的桌面级 AI 助手**。

**技术栈一览：**

| 层级 | 技术选型 |
|------|----------|
| AI 编排 | CloudWeGo Eino v0.8 (ADK) |
| LLM 后端 | OpenAI / Claude / Gemini / Ollama |
| MCP 协议 | mcp-go v0.44 |
| TUI 框架 | Bubble Tea + Bubbles (Elm 架构) |
| 终端渲染 | Glamour (Markdown) + Lip Gloss (样式) |
| HTTP 服务 | Gin v1.12 |
| 对话记忆 | 自建 JSONL 文件持久化 (零外部依赖) |
| 向量存储 | Qdrant (gRPC) |
| 嵌入模型 | Ollama (nomic-embed-text) |
| 配置管理 | Viper (多环境 + 环境变量覆盖) |
| 日志 | Zap + Lumberjack (日志轮转) |
| 认证 | JWT (golang-jwt/v5) |
| CI/CD | GitHub Actions (多架构构建) |

---

## 一、项目架构 — 分层设计

```
cmd/main/          → 程序入口，3 种运行模式：serve / chat / default
cmd/bootstrap/     → 启动编排：配置 → 上下文 → 日志 → 路由 → CLI 初始化

internal/api/      → HTTP 接口层
  ├── routes/      → 路由注册 + 热重载
  ├── handler/     → AgentHandler / AdminHandler
  ├── middlewares/  → JWT 认证 + CORS
  └── dto/         → 请求/响应 DTO

internal/service/  → 业务逻辑层 (AgentService)
internal/domain/   → 领域核心：AgentService / Agent 接口契约

internal/ai/       → AI 核心 (无 HTTP 依赖，可独立使用)
  ├── agent/       → Eino ADK 多 Agent 编排 (5 子 Agent + 1 Orchestrator)
  ├── executor/    → adk.Runner 包装器 + Token 统计
  ├── callback/    → 全局 Tool 回调处理器
  ├── llm/         → 多后端 ChatModel 管理 (Registry 模式)
  ├── memory/      → JSONL 对话记忆持久化 + 回退
  ├── prompt/      → 系统提示词构建与管理
  ├── rag/         → RAG 检索增强 (chunker / embedder / loader / vectorstore)
  └── tools/       → Function Calling 工具定义 (含 MCP 适配层)

cli/               → CLI 客户端
  ├── client/      → HTTP API 调用 (chat / memory / reback / mcp / skill / plan)
  ├── render/      → Glamour Markdown 渲染 + Lip Gloss 样式
  └── tui/         → Bubble Tea TUI 界面 (Init/Update/View)

pkg/               → 公共基础设施
  ├── conf/        → Viper 配置管理
  ├── logger/      → Zap 结构化日志
  ├── mcp/         → MCP 协议支持 (Manager + Adapter + Status)
  ├── skill/       → Skills 技能系统 (Manager + Tool + AgentHub)
  ├── sse/         → SSE 流式响应工具
  ├── task/        → 异步任务管理
  └── qdrant/      → Qdrant gRPC 客户端

config/            → YAML 配置文件 (首次运行自动生成)
```

**依赖方向**：`cmd` → `api` → `service` → `ai` → `pkg`，每层只依赖下层，`pkg` 完全不依赖 `internal`。

---

## 二、核心设计决策

### 2.1 为什么自建 JSONL 记忆层，而不是用 Eino 自带 Memory？

Eino ADK 自带内存记忆，但它绑定于进程生命周期，重启即丢失。Mifer 自建 JSONL 文件记忆层：

```go
// memory/save.go — 增量追加写入，锁保护并发
func (m *Memory) Save() error {
    m.mu.Lock()
    defer m.mu.Unlock()
    // 只写入未持久化的新消息 (savedCount 之后)
    newMsgs := m.Messages[m.savedCount:]
    f, _ := os.OpenFile(fileName, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    for _, msg := range newMsgs {
        line, _ := json.Marshal(msg)
        f.Write(line)
        f.Write([]byte("\n"))
    }
    m.savedCount = len(m.Messages)
}
```

设计要点：
- **增量追加**：只写新消息，不重写整个文件
- **锁保护**：`sync.Mutex` 防止并发写入混乱
- **会话隔离**：基于 workdir 哈希生成目录名，不同项目对话互不干扰
- **切换/回退**：支持 `/excmem <id>` 随时切换，支持 `/reback <index>` 回退到历史任意轮次

### 2.2 为什么 LLM 后端用 Registry 模式？

项目需要同时接入多个模型（日常用 DeepSeek，复杂任务用 Claude，本地测试用 Ollama），各提供商的 ChatModel 创建方式不同。

```go
// llm/providers.go — 函数表模式注册
var providerInitMap = map[string]func(context.Context, conf.BackendConfig) (model.BaseChatModel, error){
    "openai": initOpenAIModel,
    "claude": initClaudeModel,
    "gemini": initGeminiModel,
    "ollama": initOllamaModel,
}
```

Registry 对外暴露 `Get(name)` 方法，缺失时自动 fallback 到 default。业务代码切换模型不改一行代码。

### 2.3 三级模型分配策略

根据任务复杂度分配不同能力的模型，平衡成本与质量：

| 模型级别 | 用途 | 示例 Agent |
|---------|------|-----------|
| haiku | 快速响应、简单对话 | 轻量任务 |
| sonnet | 均衡能力、代码生成 | MiEditer / MiSummarizer / MiCommander |
| opus | 最强推理、深度分析 | MiPlanner / MiAuditor |
| default | 编排调度主脑 | Mifer（Orchestrator） |

### 2.4 为什么 Agent 编排设 0 轮迭代？

`MaxIteration=0` 由模型自主控制迭代次数，避免预设上限导致任务中断，也避免过多迭代造成反思循环。模型在判断任务完成时自行停止，无需框架硬编码上限。

### 2.5 为什么设计 serve / chat / default 三种启动模式？

```
go run ./cmd/main          → 同时启动服务 + CLI（default）
go run ./cmd/main serve    → 仅启动 HTTP 服务（生产部署）
go run ./cmd/main chat     → 仅启动 CLI 客户端（连接已有服务）
```

CLI 和服务端之间通过 HTTP + SSE 通信，CLI 本身不直接依赖 `internal/` 的任何模块。这意味着：
- **同一套 HTTP API** 同时服务于 CLI 和未来的 Web UI
- **CLI 可独立连接到远程服务**：`chat` 模式下 CLI 仅作为 HTTP 客户端
- **default 模式自动编排**：启动服务后等待就绪，再启动 CLI，`Ctrl+C` 同时关闭两者

---

## 三、AI 核心详解

### 3.1 多 Agent 协作体系

基于 Eino ADK 的 Orchestrator，Mifer 调度 5 个专家 Agent：

```
用户输入
  → Mifer (Orchestrator)   —— 分析意图，调度子 Agent，模型自主控制迭代
      ├── MiEditer          —— 文件读写与创建 (sonnet)
      ├── MiSummarizer      —— 文档摘要 + 知识库检索 (sonnet)
      ├── MiPlanner         —— 项目计划与方案设计 (opus)
      ├── MiCommander       —— 终端命令执行 (sonnet + 白名单约束)
      └── MiAuditor         —— 代码与配置安全审计 (opus)
```

编排器关键参数：
- `MaxIteration: 0`：由模型自主控制迭代次数
- `EmitInternalEvents: true`：转发子 Agent 内部事件到父级事件流，TUI 侧边栏可实时显示子 Agent 及工具调用过程

### 3.2 流式执行引擎 + Token 统计

`executor/chat.go` 中的核心执行流程：

```
1. AppendUser → 将用户消息加入记忆
2. runner.Run() → 获取事件迭代器
3. 循环 iter.Next()
    ├── event.AgentName 变化 → 发射 agent_start / agent_end 事件
    ├── 检测 ToolCalls → 发射 tool_start 事件
    ├── 检测 Tool 角色消息 → 发射 tool_end / tool_error 事件
    ├── 流式消息 → 逐 chunk 发射 response 事件 + reasoning 事件
    ├── 累加 Token 统计 (prompt/completion/cached/reasoning)
    └── 非流式消息 → 发射完整 response
4. AppendAssistant → 助手回复加入记忆
5. memory.Save() → 增量持久化到 JSONL
```

Token 统计在 `tokens.go` 中独立管理，与 executor 主逻辑解耦，支持按会话累计、按模型分类。

### 3.3 RAG 检索增强（一）：懒加载 + 工具闭包注入

知识库检索以**可选工具**形式接入——LLM 在对话中自主判断何时检索、何时入库，不需要预设规则。

**懒加载层** (`LazyService`)：
```
Init() → NewLazyService()   // 仅创建 embedder / loader / chunker，无网络调用，即时返回
         ↓
首次工具调用 → ensureReady()  // 此时才连接 Qdrant，创建 indexer / retriever
         ↓                 // Mutex 保护，失败后下次调用可重试
         组装为完整 Service
```

**工具闭包注入** (`tools.KnowledgeTools(ragSvc)`)：
```go
func New(ragSvc rag.RAGService) (tool.InvokableTool, error) {
    return utils.InferTool("knowledge_search", "检索知识库...", func(ctx, input) {
        docs, _ := ragSvc.RetrieveWithContext(ctx, query, ctxSize) // 闭包捕获 ragSvc
        return KnowledgeSearchOutput{Results: ragSvc.FormatDocs(docs)}
    })
}
```

设计要点：
1. **RAG 不是框架强制的依赖**，而是 AI 可选的工具——`KnowledgeTools(ragSvc)` 为 nil 时静默返回空工具列表
2. **懒初始化零等待**：启动时不触碰网络；用户不触发知识库功能就永远不连接 Qdrant
3. **失败可恢复**：`ensureReady()` 用 `sync.Mutex` 而非 `sync.Once`，上次连接失败后下次调用可重试
4. **AI 自主决策**：工具通过闭包持有 RAG 接口，LLM 在对话中判断何时检索

### 3.4 RAG 检索增强（二）：上下文分块扩展检索

在基础语义检索之上，实现了**上下文窗口扩展**机制——检索到匹配分块后，自动获取其前后各 N 个相邻分块，合并去重后按文档和位置排序返回。

```
语义检索命中 chunk[i] → 查询同文档 chunk[i-N ... i+N] → 去重合并 → 排序输出
```

**核心实现** (`RetrieveWithContext`)：
- 首次语义检索获取 TopK 匹配分块
- 对每个匹配分块，按 `source_document` + `chunk_index` 范围查询相邻分块
- 通过 `seen map` 去重
- 最终结果按源文档 + 分块序号排序，保证上下文连贯性
- LLM 可通过 `context_size` 参数控制扩展窗口大小

这一设计解决了传统 RAG "只见树木不见森林"的问题。

### 3.5 MCP 协议支持：外挂式工具生态

基于 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 实现外挂式工具扩展——第三方工具通过 stdio 协议接入，AI 在对话中自动发现和调用，无需修改 Mifer 核心代码。

**架构**：
```
MCP Manager (生命周期管理)
  → MCPToolAdapter (JSON Schema → Eino InvokableTool 自动转换)
    → GetToolsForAgent(agentName) (按 Agent 名路由工具)
```

**关键设计**：
- **工具适配层** — Schema 通过 JSON 桥接自动转换，无需手工映射；工具名以 `{serverName}_{toolName}` 命名空间隔离
- **Agent 级分配** — 每个 MCP Server 配置 `agents` 字段指定工具分配给哪些子 Agent
- **热重载** — `Reload()` 对比新旧配置增量更新（新增/删除/配置变更），不停机
- **失败隔离** — 单个 Server 连接失败不阻塞其他 Server 和 Agent 启动
- **状态可观测** — `GET /api/mcp/status` 返回所有 Server 的连接状态与工具数量，CLI `/mcp` 命令实时查看
- **进程隔离** — MCP Server 以 stdio 子进程运行，错误不暴露给终端用户
- **内置 Demo Server** — `cmd/mcp-demo/` 提供 echo / get_time / calculator / random_number 示例工具

### 3.6 Skills 技能系统：声明式自定义技能

Skills 允许用户通过 **YAML frontmatter + Markdown 指令** 声明式定义技能，支持 `inline`（内联）和 `fork`（分叉）双模式执行。

**技能示例**：
```markdown
---
name: my-skill
description: 我的自定义技能
context: fork
agent: MiEditer
---

# 技能指令
当此技能被调用时，请按以下步骤操作...
```

**关键设计**：
- **inline 模式** — 技能内容直接注入当前对话上下文，LLM 在同一 Agent 中遵循指令执行
- **fork 模式** — 通过 `AgentHub` 查找目标 Agent，创建子 Agent 独立执行；目标 Agent 不存在时自动降级为 inline
- **AgentHub 依赖反转** — 技能系统通过 `AgentHub` 接口查找 Agent，不直接依赖 `internal/ai/agent`
- **文件系统即数据库** — 技能以 `目录名/SKILL.md` 形式存储，零配置、零依赖
- **LLM 自主选择** — `skill` 工具的描述中动态注入所有可用技能列表，LLM 根据用户意图自主判断是否调用

### 3.7 工具调用确认机制

基于 **Eino `ToolsNodeConfig.ToolCallMiddlewares`** 实现的工具调用前用户确认系统——AI 执行任何工具前先通过 SSE 通知 TUI，用户确认后才真正执行。

**架构**：
```
LLM 请求工具 → ToolMiddleware 拦截 → 存入 PendingStore + 发送 SSE "tool_confirm"
→ TUI 侧边栏显示确认列表 [Yes / No / Allow]
→ 用户选择 → POST /api/tool/confirm → resolve channel → 中间件解阻塞
```

**关键设计**：
- **Actor 模型并发** — `confirm.Store` 使用专用 goroutine + channel 串行化所有状态访问，避免锁竞争
- **Channel 阻塞模型** — 中间件生成 UUID，写入 `PendingStore`（含 `chan ConfirmResult`），发送 SSE 后 `select` 阻塞等待
- **三态确认** — Yes（仅本次执行）、No（拒绝）、Allow（始终允许：非命令工具加入 Session 白名单，命令工具写入 `.mifer/allowlist.yaml` 持久化）
- **配置驱动** — `confirm.enabled` 开关 + `confirm.exclude` 排除列表

### 3.8 全局工具回调

基于 Eino 全局回调机制统一处理所有工具调用事件（开始 / 结束 / 错误），替代了早期分散在各 executor 中的事件处理代码。TUI 侧边栏通过回调事件实时展示工具执行状态。

### 3.9 对话回退 (Reback)

支持将对话回退到历史任意轮次后重新生成。底层在 JSONL 文件中按索引截断，`AgentService.Reback(ctx, index)` 统一接口，同时清理内存中的 Agent 状态，保证回退后对话连续性。

### 3.10 配置热重载

`/reload` 命令或 `POST /api/admin/reload` 接口触发，运行时重新加载 YAML 配置、命令白名单和 MCP Server 配置，无需重启服务。

### 3.11 Plan 管理：AI 自主的计划系统

Plan 功能的设计哲学是**"由 AI 决定，而非框架强制"**——不使用 Graph/Workflow 的强制编排，让 LLM 自主调度计划。

- **无 Graph 强制** — `MiPlanner` Agent 配备 `PlannerTools()`（仅限文件创建和写入，工作目录锁定在 `.mifer/plans/`），AI 直接编写 Markdown 计划文件
- **面向 AI 能力演进** — 随着 LLM 推理能力增强，许多需要工程化 Graph 编排的场景可以由 AI 自主完成
- **CLI 集成** — `/plan` 命令查看计划文件列表，回车加载并展示计划内容

### 3.12 /init 命令：AI 自动生成项目提示词

`/init` 命令让 AI 自动探索项目结构、阅读源码和已有文档，然后生成 `.mifer/MIFER.md` 项目级提示词文件。执行流程：

1. AI 列出项目目录结构，识别配置文件、源码目录和文档
2. 分批次阅读所有核心源文件和配置文件
3. 阅读已有文档补充理解
4. 生成 MIFER.md，包含项目概述、技术栈、架构、构建命令、代码约定和开发指南

生成的 MIFER.md 自动拼接到系统提示词中，后续对话中 AI 自动获得项目上下文。

### 3.13 /config 命令：外部编辑器修改配置

`/config` 命令调出系统默认编辑器（优先级：配置 `cli.tui.editor` → `$VISUAL` → `$EDITOR` → 平台默认）直接编辑 YAML 配置文件，关闭编辑器后自动执行 `/reload` 热重载。

### 3.14 多模态与工具生态

- **文件查看器**：支持图片（多模态模型描述）、PDF / Word / Markdown / 纯文本的加载与读取，自动 MIME 检测
- **图片生成器**：通过多模态模型 API 调用图片生成服务
- **知识库工具**：`knowledge_search` 检索（含上下文扩展）+ `knowledge_store` 入库，文档自动切分（递归分块 + SHA256 去重）与向量化

---

## 四、CLI / TUI 实现

### 4.1 Bubble Tea Elm 架构

```
NewModel(client, config)
  → 创建 Model (注入 client / config / mark / lip 样式)
  → 初始化子组件 (textarea / spinner / viewport / memoryList / sidebarVP)

tea.NewProgram(m).Run()
  → Init()    → textarea.Blink (光标闪烁命令)
  → Update()  → 事件循环 (按键/流式消息/窗口变化/spinner tick)
  → View()    → 7 步渲染管线
```

### 4.2 Update 消息分发

| 消息类型 | 触发条件 | 处理逻辑 |
|---------|----------|---------|
| WindowSizeMsg | 终端尺寸变化 | 重新计算 viewport/sidebar/textarea 尺寸 |
| MouseMsg | 鼠标滚轮/点击 | 委托给对应 viewport 处理 |
| KeyMsg | 按键输入 | 多模式分发：记忆模式 / 补全模式 / 正常输入 |
| streamStatusMsg | Agent切换/工具调用 | 更新侧边栏状态（含工具确认列表） |
| streamContentMsg | AI 流式输出 | 追加到 accBuf，逐字渲染 |
| streamDoneMsg | 流式传输完成 | Markdown 渲染，追加到消息列表 |
| chatRespMsg | 非流式回退 | Glamour 渲染，显示完整响应 |
| systemMsg | 命令执行结果 | 追加系统消息到对话区 |
| spinner.TickMsg | 旋转动画帧 | 推进 spinner 动画 |

### 4.3 Tab 命令补全

输入以 `/` 开头时自动触发命令补全，补全列表最多显示 5 条，超出后视窗滚动。支持的命令包括 `/help`、`/exit`、`/viewmemory`、`/excmem`、`/reback`、`/reload`、`/mcp`、`/skill`、`/plan`、`/init`、`/config`、`/compact`。

### 4.4 SSE 流取消

TUI 模式下支持 `Ctrl+C` 中断正在生成的 SSE 流——取消后对话记录保留已生成的部分内容，不会丢失上下文。

---

## 五、HTTP API 层

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/chat` | 流式对话（SSE） |
| GET | `/api/memory` | 记忆列表 |
| GET | `/api/memory/:id` | 获取指定会话记忆 |
| POST | `/api/memory/exchange/:id` | 切换记忆会话 |
| POST | `/api/memory/clear` | 清除当前记忆 |
| GET | `/api/memory/reback` | 获取回退索引列表 |
| POST | `/api/memory/reback/:index` | 回退到指定轮次 |
| GET | `/api/prompt` | 获取系统提示词 |
| POST | `/api/prompt` | 修改系统提示词 |
| POST | `/api/prompt/reset` | 重置为默认提示词 |
| POST | `/api/admin/reload` | 热重载配置与白名单 |
| GET | `/api/plan` | 列出所有计划文件 |
| GET | `/api/plan/:name` | 获取指定计划内容 |
| GET | `/api/mcp/status` | MCP Server 状态查询 |
| GET | `/api/skill/list` | 已加载技能列表 |

Chat 接口采用 SSE（Server-Sent Events）流式传输，事件格式：

```
event: response
data: {"content": "你好"}

event: thinking
data: {"content": "让我思考一下..."}

event: agent_start
data: "MiPlanner"

event: tool_start
data: "file_reader"

event: tool_confirm
data: {"uuid":"...", "tool":"command_executor", "params":{...}}

event: token
data: {"prompt": 150, "completion": 80, "total": 230, "cached": 20, "reasoning": 45}
```

---

## 六、基础设施

### 配置管理（Viper）

- 首次运行自动生成默认配置文件（带中文注释）
- 支持环境变量覆盖（`MIFER_AI_BASEURL`, `MIFER_AI_APIKEY`, `MIFER_AI_MODEL` 等）
- 多环境配置：dev 模式路径 `./config/`，prod 模式路径 `~/.mifer/config/`

### 日志系统（Zap + Lumberjack）

- dev → 控制台彩色输出，prod → JSON 格式，按级别分文件（debug/info/warn/error）
- 日志轮转：单文件最大 10MB，保留 5 个备份

### Docker 部署

```bash
# 构建并启动全部服务（Mifer + Qdrant + Ollama）
docker-compose up -d

# 仅启动 Mifer（需自行提供 Qdrant 和 Ollama）
docker-compose up -d mifer
```

### 优雅启动

端口冲突时自动递增重试（最多到 18000）：

```go
func (a *Application) Run() error {
    for a.Config.Gin.Port <= 18000 {
        err = a.server.ListenAndServe()
        if err != nil && err != http.ErrServerClosed {
            a.Config.Gin.Port += 10  // 端口自增 10
            continue
        }
        return nil
    }
}
```

### CI/CD

GitHub Actions，Tag 推送自动构建 Windows + Linux 多架构二进制。

---

## 七、项目亮点总结

1. **Eino ADK 多 Agent 编排**：5 子 Agent + 1 Orchestrator 协作，三级模型路由（haiku/sonnet/opus），0 轮迭代由模型自主控制
2. **自建 JSONL 记忆层**：增量追加 + 锁保护 + 多会话隔离 + 对话回退，零外部依赖
3. **Registry 多 LLM 管理**：4 个 provider 函数表注册 + fallback 机制，切换模型不改业务代码
4. **RAG 检索增强**：懒加载 + 工具闭包注入 + 上下文分块扩展检索，AI 自主决策检索时机
5. **MCP 协议工具生态**：外挂式工具扩展，JSON Schema 自动适配，Agent 级分配，热重载，失败隔离
6. **Skills 技能系统**：YAML 声明式定义，inline/fork 双模式，AgentHub 依赖反转，零配置存储
7. **工具调用确认**：Actor 模型 + Channel 阻塞 + 三态确认（Yes/No/Allow），持久化白名单
8. **流式 SSE + 事件管道**：Agent 切换/工具调用/推理过程/token 统计全部以事件穿透到 TUI 侧边栏
9. **Bubble Tea TUI**：Elm 架构 + Markdown 渲染 + 流式实时输出 + 命令补全 + SSE 流取消
10. **配置热重载**：`/reload` 运行时更新配置、白名单、MCP Server，无需重启

---

## 八、后续方向

- [ ] MCP Server 模式——让 Mifer 自身作为 MCP Server 对外暴露能力
- [ ] Web UI 管理面板
- [ ] 会话分支与多路线对话探索
- [ ] Redis 缓存集成——会话状态与工具结果缓存
- [ ] 单元测试覆盖
