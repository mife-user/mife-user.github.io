---
title: Mifer — 基于 Eino 的 AI Agent 终端助手
date: 2026-06-09T12:00:00+08:00
lastmod: 2026-08-24T12:00:00+08:00
draft: false
tags: ["Go", "AI", "Eino", "Agent", "TUI", "LLM", "MCP", "RAG"]
---

[项目源码](https://github.com/mife-user/mifer)

## 前言

Mifer 是一个基于字节跳动开源 [CloudWeGo Eino](https://github.com/cloudwego/eino) 框架构建的智能 AI Agent 桌面应用。它提供 CLI（TUI）+ HTTP 双模交互，支持多 LLM 后端、配置驱动的多 Agent 协作、流式对话、工具调用确认、MCP 协议工具扩展、Skills 技能系统、RAG 检索增强、三层上下文压缩、文件快照与对话回退。一句话定位：**可编程、可扩展的桌面级 AI 助手**。

**技术栈一览：**

| 层级 | 技术选型 |
|------|----------|
| 语言 | Go 1.25 |
| AI 编排 | CloudWeGo Eino v0.8 (ADK + Graph) |
| LLM 后端 | OpenAI 兼容 / Claude / Gemini / Ollama（后端名称用户自定义） |
| MCP 协议 | mcp-go v0.44 |
| TUI 框架 | Bubble Tea + Bubbles (Elm 架构) |
| 终端渲染 | Glamour (Markdown) + Lip Gloss (样式) |
| HTTP 服务 | Gin v1.12 |
| Web 搜索 | SearXNG / Bing API / DuckDuckGo |
| 对话记忆 | 自建 JSONL 文件持久化 (零外部依赖) |
| 向量存储 | Qdrant (gRPC) |
| 嵌入模型 | Ollama (nomic-embed-text) |
| 配置管理 | Viper (环境变量覆盖 + 热重载) |
| 日志 | Zap + 自定义轮转 (按级别分文件) |
| 认证 | JWT (golang-jwt/v5) |
| CI/CD | GitHub Actions (Windows/Linux × amd64/arm64 四平台) |

---

## 一、项目架构 — 分层设计

```
cmd/main/           → 程序入口，3 种运行模式：serve / chat / default
cmd/bootstrap/      → 启动编排：配置 → 上下文(session id) → 日志 → 路由 → CLI
cmd/mcp-demo/       → 内置 MCP Stdio 演示 Server (echo / get_time / calculator / random_number)

internal/api/       → HTTP 接口层
  ├── routes/       → 路由注册 + 配置热重载（带回滚）
  ├── handler/      → AgentHandler / ToolHandler
  ├── middlewares/  → TraceID + CORS
  └── dto/          → 请求/响应 DTO（request/response 按模块分子目录）

internal/service/   → 业务逻辑层 (agentservice / toolservice，1:1 委托 executor)
internal/domain/    → 领域核心接口契约 (AgentService / Agent / ToolService)

internal/ai/        → AI 核心 (无 HTTP 依赖，可独立使用)
  ├── agent/        → Eino 编排器 + 配置驱动自定义 Agent + PlanAgent + Graphs
  ├── executor/     → adk.Runner 包装器 + Chat 编排 + Token 统计 + 快照调度
  ├── callback/     → per-invocation Tool 回调处理器
  ├── llm/          → 多后端 ChatModel 管理 (Registry 模式)
  ├── memory/       → JSONL 对话记忆持久化 + 回退 + 重命名
  ├── prompt/       → Prompty：MIFER.md 拼接 + ChatTemplate 模板
  ├── rag/          → RAG 检索增强 (chunker / embedder / loader / vectorstore)
  ├── confirm/      → 工具调用确认子系统 (Actor Store + Middleware)
  ├── compressor/   → 三层上下文压缩
  ├── offload/      → 大体积工具结果卸载存储
  └── tools/        → Function Calling 工具实现 + 错误/确认/持久化中间件

cli/                → CLI 客户端（仅依赖 HTTP API，不 import internal/）
  ├── client/       → HTTP API 调用 (chat / memory / reback / mcp / skill / plan ...)
  ├── render/       → Glamour Markdown 渲染 + Lip Gloss 样式
  └── tui/          → Bubble Tea TUI 界面 (Init/Update/View)

pkg/                → 公共基础设施（不依赖 internal/）
  ├── conf/         → Viper 配置管理（首次运行自动生成带注释的默认配置）
  ├── logger/       → Zap 结构化日志（TraceID + 按大小轮转）
  ├── mcp/          → MCP 协议支持 (Manager + Adapter + Status)
  ├── skill/        → Skills 技能系统 (Manager + Tool + AgentHub)
  ├── sse/          → SSE 写入器（单 goroutine 串行化 + 心跳保活）
  ├── snapshot/     → 文件快照（内容寻址 + 增量变更日志）
  └── ...           → auth / errorer / res / task / utils / exc / qdrant / cache

config/             → YAML 配置文件（首次运行自动生成）
```

**依赖方向**：`cmd` → `api` → `service` → `ai` → `pkg`，每层只依赖下层，`pkg` 完全不依赖 `internal`。CLI 通过 HTTP + SSE 与服务端通信，本身不 import 任何 `internal/` 包。

---

## 二、核心设计决策

### 2.1 为什么自建 JSONL 记忆层？

Eino ADK 自带的内存记忆绑定于进程生命周期，重启即丢失。Mifer 自建 JSONL 文件记忆层：

```go
// memory/save.go — 增量追加写入，锁保护并发
func (m *Memory) Save() error {
    m.mu.Lock()
    defer m.mu.Unlock()
    newMsgs := m.messages[m.savedCount:] // 只写未持久化的新消息
    f, _ := os.OpenFile(fileName, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    for _, msg := range newMsgs {
        line, _ := json.Marshal(msg)
        f.Write(line)
        f.Write([]byte("\n"))
    }
    m.savedCount = len(m.messages)
}
```

围绕这个基础能力，Memory 还提供了一整套会话操作：

- **原子替换** — `ReplaceMessages()` 全量重写文件，供上下文压缩使用
- **会话切换** — `SwitchSession()` 先持久化当前会话再加载目标会话，保证切换原子性
- **对话回退** — `Reback(index)` 按 User 消息定位轮次，截断内存并覆盖重写 JSONL
- **自动重命名** — 首轮对话结束用首条用户消息前缀（20 字符净化）作为会话名，同时重命名 `.jsonl` 和 `_snapshots/` 目录，失败回滚
- **工具记录持久化** — `AppendToolExchange()` 把 ToolCall + ToolResult 写入历史，压缩后 LLM 仍能看到完整调用轨迹

存储路径按 `memory/{workdir_basename}/{sessionID}.jsonl` 隔离，不同项目、不同会话互不干扰。

### 2.2 LLM 后端 Registry：用户命名 + agent_backends 映射

各提供商的 ChatModel 创建方式不同，且项目需要同时接入多个模型。Registry 模式把这件事拆成两层：

```go
// llm/type.go — provider 函数表注册
func NewRegistry() *Registry {
    r.RegisterProvider(&openAIProvider{})
    r.RegisterProvider(&claudeProvider{})
    r.RegisterProvider(&geminiProvider{})
    r.RegisterProvider(&ollamaProvider{})
}
```

配置中 `ai.backends` 下的键名完全由用户定义（如 `main`、`fast-model`），`type` 字段区分 `chat` / `embedding`。Agent 与后端的映射由 `ai.agent_backends` 决定：

```go
// agent/init.go — 回退链：配置映射 → 第一个注册后端 → nil
func getBackendModel(reg *llm.Registry, agentName string) model.BaseChatModel {
    cfg := conf.GetConfig()
    backendName, ok := cfg.Ai.AgentBackends[agentName]
    if !ok || backendName == "" {
        backendName = reg.FirstKey()
    }
    return reg.Get(backendName)
}
```

切换模型只改 YAML，不改一行业务代码；缺失映射自动 fallback，保证可用性。

### 2.3 serve / chat / default 三种启动模式

```
go run ./cmd/main          → 同时启动服务 + CLI（default）
go run ./cmd/main serve    → 仅启动 HTTP 服务（生产部署）
go run ./cmd/main chat     → 仅启动 CLI 客户端（连接已有服务，--<id> 可指定会话）
```

CLI 和服务端之间通过 HTTP + SSE 通信，这意味着：

- **同一套 HTTP API** 同时服务于 CLI 和未来的 Web UI
- **CLI 可独立连接远程服务**：`chat` 模式下 CLI 仅是 HTTP 客户端，不加载模型、不初始化记忆
- **default 模式自动编排**：启动服务 sleep 1s 后拉起 CLI，信号与 channel 双通道同步退出

会话 ID 的生成也值得注意：`bootstrap.initontext` 用 `RandomStr(8)` 加 Workdir 做 `PseudoRandom` 哈希，既保证同工作目录的可关联性，又用 64 bit 熵避免碰撞；`main.go` 的 `--<id>` 参数可手动指定，实现跨进程恢复同一会话。

### 2.4 接口隔离：domain 层契约

`internal/domain/bridge.go` 定义 `AgentService` 与 `Agent` 两个方法签名完全相同的接口——前者给 HTTP Handler 用，后者由 executor 实现，service 层 1:1 委托：

```go
type AgentService interface {
    Chat(ctx context.Context, req *TalkReq, callback func(event, content string) error) error
    LoadMemory(ctx context.Context, req *MemoryReq) (*MemoryResp, error)
    Reback(ctx context.Context, req *RebackReq) (*RebackResp, error)
    // ... 共 18 个方法
}
```

接口定义在消费侧（domain），实现在各自包内（`agentservice/`、`toolservice/`、`executor/`），HTTP 层完全不感知 AI 实现细节，方便 mock 与替换。

---

## 三、AI 核心详解

### 3.1 Agent 体系：单编排器 + 配置驱动子 Agent

主 Agent `Mifer` 通过 `deep.New` 创建，**直接拥有全部工具**——文件读写、命令执行、知识库、Web 搜索、技能调用、并行调度，无需委派即可独立完成任务：

```go
// agent/agent_mifer.go
agent, err := deep.New(ctx, &deep.Config{
    Name:        "Mifer",
    Instruction: miferInstruction,
    ChatModel:   agentModel,
    ToolsConfig: adk.ToolsConfig{
        EmitInternalEvents: true,
        ToolsNodeConfig: compose.ToolsNodeConfig{
            Tools:               orchTools,
            ToolCallMiddlewares: []compose.ToolMiddleware{h.errorMw, confirmMiddleware, h.persistenceMw},
        },
    },
    SubAgents:    subagents,
    MaxIteration: 100,
})
```

子 Agent 不再硬编码，而是**配置驱动**——YAML 的 `agents:` 段声明名称、描述、指令、后端和工具列表，启动时逐个创建并注册到 `skillHub`：

```yaml
agents:
  - name: "MiTest"
    description: "测试Agent"
    instruction: "你是MiTest，测试Agent。"
    model: "main"
    tools: [file_reader]
```

另有三个内置组件：

| 组件 | 类型 | 说明 |
|------|------|------|
| PlanAgent | `adk.NewChatModelAgent` | 计划制定助手，只有只读工具（file_reader/file_viewer/web_search/web_fetch/knowledge_search），MaxIterations=20 |
| PlanGraph | `compose.Graph` | `plan_agent(Lambda) → plan_write(Lambda) → plan_confirm(Lambda)` 三节点流水线 |
| HabitGraph | `compose.Graph` | `ChatModel → Lambda(写 MIFER.md)`，用户画像总结 |

`EmitInternalEvents: true` 将子 Agent 内部事件转发到父级事件流，TUI 侧边栏可实时显示工具调用过程。所有 Agent 注册进 `AgentHub`，供技能 fork 模式和 `parallel_dispatch` 按名路由。

> ⚠️ `MaxIteration=100` 是防失控上限而非预期值——正常情况下模型判断任务完成后自行停止。设上限是为了避免异常场景下的无限反思循环烧光 Token。

### 3.2 流式执行引擎

`executor/chat.go` 把一次对话拆成三段：

```
prepareChat     → 压缩检查（上轮标记）→ session 切换 → AppendUser → 注入 callback 到 ctx
runConversation → Prompt.Build → Runner.Run（最多 3 次重试）→ 迭代事件流
finalizeChat    → AppendAssistant → Save → 自动重命名 → 快照 → 异步习惯总结
```

事件循环中的关键分流：

```go
// chat_run.go — 单次 agent 运行
iter := e.Runner.Run(ctx, msgs, adk.WithCallbacks(toolCB))
for {
    event, ok := iter.Next()
    // Agent 切换 → 发射 agent_start / agent_end
    // 流式消息 → 逐 chunk 发射 response + thinking
    // Usage 元数据 → Token 累计 + 压缩阈值检查
}
```

错误处理分三类：`context.Canceled` 视为用户主动中断静默返回；网络类临时错误（timeout / TLS handshake / connection refused 等）走指数退避重试，最多 3 次；其余直接报错。

Token 统计独立在 `tokens.go`：从 `ResponseMeta.Usage` 累加 prompt/completion/cached/reasoning 四项，通过 `\x00` 分隔的 payload 发给前端展示。每轮累计超过 `length × threshold` 时标记 `needsCompression`，下一轮对话开始前触发压缩。

### 3.3 工具生态与三级中间件链

每个工具独立子目录，通过 `utils.InferTool` 或 `utils.InferEnhancedTool` 创建：

| 工具 | 能力 | 安全措施 |
|------|------|---------|
| file_reader | 读文本，start_line/max_lines 分页（默认 100 上限 500 行） | 路径 Clean 防穿越 |
| file_writer / file_creator | 写入 / 创建文件 | 写前必读约束写入系统指令 |
| file_viewer | 图片识别，批量路径 | `EnhancedInvokableTool` 返回 base64 图片数据，LLM 原生多模态识别 |
| command_executor | Windows PowerShell / Unix bash | 危险命令正则拦截 + 沙箱 + 超时 + 输出限流 |
| web_search | SearXNG（默认）/ Bing API / DuckDuckGo 三后端 | 结果数上限 10 |
| web_fetch | HTML 正文提取 | SSRF 内网防护 + 重定向校验 |
| knowledge_search / knowledge_store | 知识库检索（含上下文扩展）/ 入库 | 懒加载，未配置静默降级 |
| parallel_dispatch | 并行调度多个已注册 Agent | 单次最多 10 任务，per-task recover |

所有工具调用经过统一的中间件链（见 3.1 代码中的 `ToolCallMiddlewares`）：

```
errorMw（最外层）  → Go error 转文字响应，避免 error 中断对话流
confirmMiddleware  → 敏感工具调用前阻塞等待用户确认
persistenceMw（最内层）→ 已执行的 ToolCall + ToolResult 写入对话记忆
```

顺序有讲究：error 中间件放最外层才能捕获下游（如确认拒绝）产生的错误；持久化放最内层确保只记录真正执行了的调用。

`file_viewer` 值得单独一提：早期版本为多模态单独传入一个视觉模型，现在改用 Eino 的 `EnhancedInvokableTool` 直接返回 `*schema.ToolResult`（base64 + MIME），框架自动把图片注入 `UserInputMultiContent`，由主对话模型原生识别——少一次模型调用，架构也更干净。

### 3.4 命令执行的安全防线

`command_executor` 是权限最大的工具，防御纵深做了五层：

```go
var dangerousPatterns = []*regexp.Regexp{
    regexp.MustCompile(`rm\s+-rf`),
    regexp.MustCompile(`mkfs\.`),
    regexp.MustCompile(`sudo\s`),
    regexp.MustCompile(`curl.*\|\s*(ba)?sh`),   // 下载执行
    regexp.MustCompile(`:\(\)\s*\{`),            // fork bomb
    // ... chmod 777 / dd / kill -9 / 写裸盘等共 17 条
}
```

1. **危险命令正则拦截** — 匹配即拒绝并返回命中的规则名
2. **交互式命令检测** — ssh/vim/top 等需要 TTY 的命令直接拒绝
3. **电源命令检测** — reboot/shutdown/halt/poweroff 一律禁止
4. **工作目录沙箱** — 解析后的绝对路径必须以 Workdir 为前缀（大小写与分隔符归一化后比较）
5. **资源限制** — 超时默认 30s 最大 120s；stdout/stderr 各限 100KB，超出截断并标记

Windows 下特意用 PowerShell 而非 cmd.exe——AI 倾向生成 Unix 风格命令，PowerShell 内置的 ls/cat/rm 别名兼容性远好于 cmd。

`web_fetch` 同样有 SSRF 防护：拒绝 localhost/回环/10./172.16./192.168. 及云元数据地址，重定向时逐跳复查，最多 3 次重定向，Content-Type 必须是 text/html。

### 3.5 工具调用确认机制

基于 Eino `ToolCallMiddlewares` 实现的工具调用前用户确认——AI 执行任何敏感工具前先通过 SSE 通知 TUI，用户确认后才真正执行。

**Store 采用 Actor 模型**：专用 goroutine + channel 串行化所有状态访问，外部通过发送闭包提交操作：

```go
// confirm/store.go
func (s *Store) Resolve(id string, result ConfirmResult) {
    s.cmdCh <- func(state *storeState) {
        entry, ok := state.pending[id]
        if ok {
            select {
            case entry.ResultCh <- result: // 缓冲为 1，非阻塞
            default:
            }
        }
    }
}
```

**中间件的 Channel 阻塞模型**：

```
LLM 请求工具 → Middleware 判定需确认 → 生成 UUID 存入 PendingStore
→ SSE "tool_confirm"（含完整参数 DTO）→ select 阻塞等待
→ TUI 弹出确认列表 [Yes / No / Allow] → POST /api/tool/confirm → resolve channel 解除阻塞
```

判定是否需要确认的逻辑（`NeedConfirm`）：`enabled` 开关 → `exclude` 排除列表 → `command_executor` 额外查全局白名单（`.mifer/allowlist.yaml`，支持 `git*` 通配符）→ session 白名单。

三态选择的语义：Yes 仅本次放行；No 拒绝并把错误文字返回给 LLM 自行调整；Allow 对非命令工具加入 session 白名单（对话结束自动清理），对命令工具写入磁盘白名单永久生效。Actor 主循环每 30s 巡检一次，清理超过 5 分钟无人处理的待确认项。

### 3.6 RAG 检索增强（一）：懒加载 + 工具闭包注入

知识库检索以**可选工具**形式接入——LLM 在对话中自主判断何时检索、何时入库。

**懒加载层** (`LazyService`)：

```
Init() → NewLazyService()   // 仅创建 embedder / loader / chunker，无网络调用
         ↓
首次工具调用 → ensureReady()  // 此时才连接 Qdrant，创建 indexer / retriever
         ↓                 // Mutex 保护，失败后下次调用可重试
         组装为完整 Service
```

**工具闭包注入**——工具包只依赖自己定义的最小接口：

```go
// knowledgesearch/knowledgesearch.go
type retriever interface {
    RetrieveWithContext(ctx context.Context, query string, contextSize int) ([]*schema.Document, error)
    FormatDocs(docs []*schema.Document) string
}

func New(ragSvc retriever) (tool.InvokableTool, error) {
    return utils.InferTool("knowledge_search", "...", func(ctx, input) {
        docs, _ := ragSvc.RetrieveWithContext(ctx, input.Query, input.ContextSize)
        return KnowledgeSearchOutput{Results: ragSvc.FormatDocs(docs)}
    })
}
```

设计要点：RAG 不是框架强制的依赖，`KnowledgeTools(nil)` 静默返回空列表；启动零网络等待；`ensureReady` 用 Mutex 而非 sync.Once，连接失败后下次可重试。

### 3.7 RAG 检索增强（二）：上下文分块扩展检索

仅有语义检索存在"断章取义"问题——命中分块缺乏前后文。`RetrieveWithContext` 在基础检索之上加了窗口扩展：

```go
// rag/retrieve.go
filter := &qdrant.Filter{
    Must: []*qdrant.Condition{
        qdrant.NewMatchKeyword("source_document", srcDoc),
        qdrant.NewRange("chunk_index", &qdrant.Range{Gte: &gte, Lte: &lte}),
    },
}
neighbors, err := s.retriever.Retrieve(ctx, query,
    qdrantretriever.WithFilter(filter),
    retriever.WithTopK(contextSize*2+1))
```

流程：首次语义检索取 TopK → 对每个命中分块按 `source_document + chunk_index` 范围查询前后 N 个邻居 → `seen map` 去重 → 按源文档和分块序号排序输出。单个文档邻居查询失败只跳过不影响整体。LLM 可通过 `context_size` 参数控制窗口大小，默认 0 不扩展。`FormatDocs` 按文档分组渲染，保持阅读连贯性。

### 3.8 MCP 协议支持：外挂式工具生态

基于 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 实现外挂式工具扩展——第三方工具以 stdio 子进程接入，AI 自动发现和调用，无需修改 Mifer 核心代码。

```
MCP Manager (生命周期管理：启动/握手/ListTools/关闭)
  → MCPToolAdapter (JSON Schema 序列化桥接 → Eino InvokableTool)
    → GetToolsForAgent(agentName) (按 Agent 名路由)
```

适配的核心是 Schema 桥接——MCP 的 InputSchema 经 JSON 序列化后反序列化为 Eino 的 jsonschema.Schema，零手工映射：

```go
rawJSON, _ := json.Marshal(a.mcpTool.InputSchema)
var einoSchema jsonschema.Schema
json.Unmarshal(rawJSON, &einoSchema)
info.ParamsOneOf = schema.NewParamsOneOfByJSONSchema(&einoSchema)
```

关键设计：

- **命名空间隔离** — 工具名 `{serverName}_{toolName}`，避免多 Server 冲突
- **Agent 级分配** — 每个 Server 配置 `agents` 字段，空或 `["*"]` 表示全部可用
- **失败隔离** — 单个 Server 连接失败只标记 Status=error，不阻塞其他 Server；初始化失败时 defer 关闭客户端防止子进程泄漏
- **错误转文字** — `result.IsError` 时返回错误文本而非 Go error，让 LLM 自行处理
- **状态可观测** — `GET /api/mcp/status` 返回连接状态与工具数量，CLI `/mcp` 实时查看
- **内置 Demo** — `cmd/mcp-demo/` 提供 echo / get_time / calculator / random_number 四个示例工具

### 3.9 Skills 技能系统：声明式自定义技能

Skills 允许用户通过 **YAML frontmatter + Markdown 指令**声明式定义技能，支持 `inline`（内联）和 `fork`(分叉) 双模式：

```markdown
---
name: my-skill
description: 我的自定义技能
context: fork
agent: MiTest
---

# 技能指令
当此技能被调用时，请按以下步骤操作...
```

- **inline 模式** — 技能内容直接返回注入当前上下文，LLM 在同一 Agent 中遵循执行
- **fork 模式** — 通过 `AgentHub` 查找目标 Agent 创建子任务独立执行；目标不存在自动降级 inline
- **动态描述** — `SkillTool.Info()` 把所有可用技能列表拼进 tool description，LLM 根据用户意图自主选择是否调用
- **零配置存储** — 技能即 `目录名/SKILL.md`，frontmatter 手工解析避免引入 YAML 依赖；首次启动自动创建 hello-world 示例和内置的 context-summarizer（供压缩器使用）

### 3.10 /plan 计划强制执行：PlanGraph

`/plan <任务>` 触发两阶段流程，通过**工具隔离 + 用户确认**确保先规划后执行：

```
用户 /plan <任务>
  │
  ├── PlanAgent(只读工具) 流式分析 → planning/thinking/response 事件实时显示
  ├── plan_write Lambda → 计划写入 .mifer/plans/plan_时间戳.md
  ├── plan_confirm Lambda → SSE "plan_confirm" → TUI 全屏预览 → Enter 确认 / Esc 拒绝
  └── Mifer(全工具) 按计划执行 → 正常对话流
```

这是 Eino Graph 编排的典型应用——三个 Lambda 节点串联编译为 `Runnable[[]*schema.Message, string]`：

```go
g.AddLambdaNode("plan_agent", ...)   // 运行 PlanAgent，转发流式事件
g.AddLambdaNode("plan_write", ...)   // 持久化计划文件
g.AddLambdaNode("plan_confirm", ...) // 复用 confirm.Store 阻塞等待用户，30 分钟超时
g.AddEdge(compose.START, "plan_agent")
```

工具层面强制隔离：PlanAgent 只有只读工具，**无写入和命令权限**，从根上杜绝"跳过计划直接动手"。拒绝时返回哨兵错误 `ErrPlanRejected`，上层捕获后发 system 事件告知用户。整个流程共享 Memory，计划确认后保存一轮、执行完成再保存一轮，历史完整不丢上下文。

### 3.11 上下文压缩：三层记忆模型 + Offload

长对话必然撑爆上下文窗口。Mifer 的方案不是简单丢弃历史，而是按信息密度分层处理：

```
Layer 1（最近 recent_rounds 轮）— 完整保留，含 ToolCall + ToolResult 原文
Layer 2（中间 slim_rounds 轮）— 保留 ToolCall，超长 ToolResult 截断/offload
Layer 3（更早轮次）— 调用压缩模型生成摘要，替换为两条 System 消息
```

以 User 消息为边界切分轮次后逐层处理。Layer 2 的 offload 机制最有意思——超过 50KB 的工具结果不粗暴截断，而是存档到本地文件并留下可追溯的占位符：

```go
copied.Content = fmt.Sprintf(
    "【工具结果已存档】工具 [%s] 返回了约 %d 字符的结果，完整内容已保存至 %s。" +
    "如需查看完整结果，请使用 file_reader 工具读取该文件。\n\n" +
    "结果摘要（前 1000 字符）：\n%s", ...)
```

这样 LLM 需要时可以主动找回完整数据。摘要阶段复用内置的 `context-summarizer` 技能模板 + `fast-model` 后端，每条消息超 8000 字节按 UTF-8 字符边界截断（避免切出半个汉字）。降级策略完备：技能缺失、模型不可用或调用失败时，退化为移除最早轮次只保留最近 N 轮。

触发时机有两个：Token 累计超阈值后下一轮对话前自动压缩，或 `/compact` 命令手动触发。压缩完成后 `ReplaceMessages` 原子替换记忆并全量重写文件。

### 3.12 文件快照：对话回退的文件级 Undo

AI 改错了文件怎么办？`pkg/snapshot/` 实现了基于**内容寻址 + 追加式变更日志**的增量快照系统，让对话回退时文件状态一并回滚：

```
{sessionID}_snapshots/
├── objects/{hash前2位}/{完整sha256}   ← 文件内容仓库（去重）
└── changes.jsonl                      ← 追加式变更日志
```

```go
// copy.go — 快速变更检测：size+mtime 未变直接跳过
if hasLast && lastEntry.Size == info.Size() && lastEntry.Mtime == currentMtime {
    return nil
}
hash, size, _ := s.computeFileHash(path)  // 仅变更文件计算 SHA256
s.storeObject(path, hash)                 // 内容去重入库
s.appendChange(entry)                     // 追加日志
```

设计要点：

- **追加式而非每轮全量目录** — 恢复时扫描 `round ≤ target` 的条目，对每个文件取最新一条重建状态，删除用空 Hash 标记
- **按需计算** — size + mtime 未变的文件零开销；本轮无任何变更就不产生日志
- **恢复即双向同步** — 从 objects 池还原目标文件，同时删除目标状态中不存在多余文件
- **孤儿治理** — `RemoveRound` 过滤指定轮次条目后 tmp + Rename 原子重写；`InitBaseline` 保证 r0 基线存在，并自动迁移旧版 `r{N}/` 目录格式
- **纯库设计** — 不依赖项目内任何包，排除 `.git`/`node_modules`/`.mifer` 等目录

回退时的联动：`Executor.Reback` 先回滚记忆，再 `RestoreToRound(index-1)` 恢复文件，最后删除被回退轮次的快照记录——对话和文件系统保持一致。

> ⚠️ 快照按 `{sessionID}_snapshots/` 隔离，但操作同一个 workdir。多个并发会话各自回退可能互相覆盖文件，设计上假设同一工作目录同时只有一个活跃会话。

### 3.13 HabitGraph：自动维护的用户画像

每轮对话结束后异步触发（fire-and-forget，不阻塞响应）：读取已有的用户级 `MIFER.md`，连同本轮对话一起交给 `habit_summarizer` 后端分析，输出增量更新后的画像并全量覆写。

- 分析维度：编程语言偏好、技术栈、工作习惯、常用工具、项目类型、沟通风格
- 明确要求不记录敏感信息（密码、密钥、个人身份信息）
- 用户级 `~/.mifer/MIFER.md` 与项目级 `.mifer/MIFER.md` 都会自动拼接到系统提示词，前者优先

配合 `/init` 命令（AI 探索项目结构、阅读源码后自动生成项目级 MIFER.md），形成"项目上下文 + 用户习惯"的双重个性化。

### 3.14 配置热重载（带回滚）

`/reload` 命令或 `POST /api/admin/reload` 触发运行时重载：

```go
// routes/reload.go
oldConfig := *conf.GetConfig()          // 1. 快照旧配置
conf.LoadConfig()                        // 2. 重读
conf.StatusConfig()                      // 3. 校验，失败回滚
newExec, err := executor.Init(r.appCtx)  // 4. 重建执行器，失败回滚
oldSvc := r.agentHandler.SwapService(...) // 5. RWMutex 保护下原子替换
oldAgentSvc.CloseExecutor()               // 6. 释放旧实例资源（MCP 子进程、确认 Store actor）
```

响应中携带每个后端的状态报告（ok / failed + 原因），api_key 未配置的后端会被明确指出。适用于动态切换模型、调整参数、启用新 MCP Server 等场景，全程不停机。

### 3.15 per-invocation 回调替代全局注册

工具事件的传递经历了一次架构修正：早期用 `callbacks.AppendGlobalHandlers` 全局注册，callback 通过 context 注入；现在改为 `callback.NewHandler(cb)` 闭包工厂，每次 `Runner.Run()` 通过 `adk.WithCallbacks(handler)` 按调用注入：

```go
toolCB := aicallback.NewHandler(callback)          // 闭包捕获，零依赖 context
iter := e.Runner.Run(ctx, msgs, adk.WithCallbacks(toolCB))
```

OnStart/OnEnd/OnError 三个处理器都通过闭包持有 cb。额外做了一个补漏：工具可能执行成功但返回值 JSON 里带 `error` 字段（如"文件不存在"），Go error 为 nil，此时从返回值中提取 error 字段补发 `tool_error` 事件。

---

## 四、CLI / TUI 实现

### 4.1 Bubble Tea Elm 架构

```
NewModel(client) → 注入 mark/lip 样式，初始化 textarea/spinner/viewport/各选择列表
tea.NewProgram(m).Run()
  → Init()    → textarea.Blink + 后端状态检查（api_key 未配置提前告警）
  → Update()  → 消息循环（按键/流式消息/窗口变化/spinner tick）
  → View()    → 渲染管线输出
```

Model 的状态划分非常细致：消息区 viewport、侧边栏 viewport、全屏记忆查看 viewport、全屏计划查看 viewport 各自独立；输入历史环形缓冲支持 ↑↓ 导航，进入导航前暂存当前输入便于恢复。

### 4.2 流式传输与侧边栏

流式响应通过 `streamCh` channel 送入 Update 循环，逐 chunk 追加缓冲区实时渲染，`Ctrl+C` 可中断——已生成的部分内容保留，不丢上下文。

侧边栏是一个小型状态机，区分两个概念：

```go
Current      string // 显示层的活跃项（agent 名或缩进的 tool 名）
CurrentAgent string // 真正运行中的 agent（不被工具事件覆盖）
```

`tool_start` 只覆盖 Current 显示，不动 CurrentAgent；`tool_end` 后回落显示仍在运行的 agent；`agent_end` 只有匹配 CurrentAgent 才生效，重复/乱序事件幂等忽略。这个设计解决了嵌套事件乱序导致的显示错乱。底部实时显示 Token 用量统计，每条日志带时间戳。

### 4.3 命令系统

输入 `/` 开头触发 Tab 补全（最多显示 5 条，超出滚动）。完整命令集：

| 命令 | 功能 |
|------|------|
| `/help` `/exit` `/quit` | 帮助 / 退出 |
| `/clear` | 清除当前对话创建新会话 |
| `/viewmemory [id]` | 查看/加载历史会话（全屏浏览模式） |
| `/excmem <id>` | 切换到指定会话 |
| `/rename <name>` | 重命名当前会话 |
| `/reback` | 列出可回退轮次，选择后对话+文件一并回滚 |
| `/compact` | 手动触发上下文压缩 |
| `/prompt [text\|reset]` | 查看/设置/重置系统提示词 |
| `/reload` `/config` | 热重载 / 外部编辑器打开配置（关闭后自动 reload） |
| `/plan <描述>` | 计划模式：先规划 → 确认 → 再执行 |
| `/plan` | 浏览已有计划文件 |
| `/init` | AI 分析项目生成 `.mifer/MIFER.md` |
| `/mcp` `/skill` `/agents` | MCP 状态 / 技能列表 / Agent 列表 |

工具确认弹窗针对每种工具定制参数展示——command_executor 显示命令原文、file_creator 显示路径和内容预览，让用户明确知道要确认的是什么。

---

## 五、HTTP API 层

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/chat` | 流式对话（SSE），支持 `mode:"plan"` 与 `session_id` 自动切换 |
| GET | `/api/memory` | 记忆列表 |
| GET | `/api/memory/:id` | 获取指定会话记忆 |
| POST | `/api/memory/exchange/:id` | 切换记忆会话 |
| POST | `/api/memory/clear` | 清除当前记忆 |
| POST | `/api/memory/rename` | 重命名会话 |
| POST | `/api/memory/compact` | 手动上下文压缩 |
| GET | `/api/memory/reback` | 获取回退索引列表 |
| POST | `/api/memory/reback/:index` | 回退到指定轮次（含文件快照恢复） |
| GET/POST | `/api/prompt` | 系统提示词读取 / 修改 |
| POST | `/api/prompt/reset` | 重置为默认提示词 |
| POST | `/api/admin/reload` | 配置热重载（带回滚） |
| GET | `/api/admin/status` | 后端就绪状态检查 |
| GET | `/api/plan` `/api/plan/:name` | 计划文件列表 / 内容 |
| GET | `/api/mcp/status` | MCP Server 状态查询 |
| GET | `/api/skill/list` | 已加载技能列表 |
| GET | `/api/agents` | Agent 列表（含后端、模型、工具集） |
| POST | `/api/tool/confirm` | 工具确认结果提交 |
| POST | `/api/tool/allowlist/add` | 命令白名单追加 |

Chat 接口采用 SSE 流式传输，共 11 种事件类型：

```
event: response      data: {"content": "你好"}                    # 内容 token 流
event: thinking      data: {"content": "让我思考一下..."}          # 推理过程流
event: agent_start   data: "PlanAgent"                            # Agent 切换
event: tool_start    data: "file_reader\x00{\"file_path\":...}"   # \x00 分隔工具名与参数
event: tool_end      data: "file_reader"
event: tool_error    data: "file_reader\x00文件不存在"
event: tool_confirm  data: {"uuid":"...", "tool":"command_executor", "params":{...}}
event: plan_confirm  data: {"id":"...", "file_path":"...", "content":"..."}
event: token         data: "150\x0080\x00230\x0020\x0045"          # prompt/completion/total/cached/reasoning
event: system        data: "正在分析项目并制定计划..."              # 系统通知
```

`[DONE]` 表示正常结束，`[ERROR] <msg>` 表示流错误。底层 `pkg/sse/writer.go` 由专用 goroutine + 缓冲 channel（buf=16）驱动：`SendSync` 阻塞写入并感知断连，`SendFire` 即发即忘用于心跳；写入失败自动触发 cancel 联动请求退出，channel 满判定 TCP 半开直接放弃，避免死锁。

---

## 六、基础设施

### 配置管理（Viper）

首次运行自动生成带中文注释的默认配置，涵盖运行环境、日志、JWT、快照开关、RAG、MCP、搜索、技能、确认策略、AI 后端、压缩参数、自定义 Agent、Gin、TUI 样式等全部模块。敏感字段支持环境变量覆盖：`MIFER_AI_BACKENDS_<NAME>_APIKEY` 可覆盖任意后端的 api_key，另有 `MIFER_JWT_SECRET`、`MIFER_SEARCH_API_KEY` 等。dev 模式配置在 `./config/dev.yaml`，prod 在 `~/.mifer/config/prod.yaml`。

### 日志系统（Zap）

按级别分四个文件（debug/info/warn/error.log），自定义 `rotatingFile` 按大小轮转淘汰。dev 彩色控制台 Debug 级别，prod JSON Info 级别。TraceMiddleware 注入 TraceID 贯穿请求链路。结构化字段用 `logger.S/I/U/C` 辅助函数，日志消息统一中文。

### Docker 部署

```bash
docker-compose up -d              # 全部服务
docker-compose up -d qdrant       # 按需启动单个
```

| 服务 | 端口 | 用途 |
|------|------|------|
| Qdrant | 6333/6334 | RAG 向量数据库 |
| SearXNG | 18080 | 元搜索引擎，web_search 默认后端 |
| Ollama | 11434 | 本地嵌入模型 |
| Loki + Promtail | 3100 | 日志聚合与采集 |

### 优雅启动与关闭

端口冲突自动递增重试（+=10，上限 18000）；关闭时 30s 超时优雅停机，Executor 统一释放 MCP 子进程与确认 Store 的 actor goroutine。

### CI/CD

GitHub Actions 推送 `v*` 标签自动构建 Windows/Linux × amd64/arm64 四平台二进制（`CGO_ENABLED=0` + `-ldflags="-s -w"`），打包为 zip/tar.gz 附带使用教程与 docker-compose.yml，发布 GitHub Release。

---

## 七、项目亮点总结

1. **Eino 深度实践**：ADK 编排器 + Graph 流水线（Plan/Habit）+ ToolMiddleware 三件套（错误转换/确认/持久化），一套代码演示了框架的全部主流用法
2. **配置驱动的多 Agent**：自定义 Agent、后端映射、工具分配全部 YAML 声明，缺失配置逐级 fallback
3. **自建 JSONL 记忆层**：增量追加 + 原子替换 + 多会话切换 + 回退 + 自动重命名，零外部依赖
4. **工具调用确认**：Actor Store + Channel 阻塞 + 三态确认（Yes/No/Allow），session 白名单与磁盘白名单双层豁免
5. **三层上下文压缩**：完整保留/精简/offload 分层处理，超长结果存档可溯源，多重降级兜底
6. **文件快照系统**：内容寻址去重 + 追加式变更日志，对话回退时文件状态一并 Undo
7. **RAG 懒加载 + 上下文扩展检索**：启动零网络等待，命中分块自动带前后文，解决"只见树木不见森林"
8. **MCP 外挂工具生态**：JSON Schema 自动桥接，Agent 级分配，失败隔离，热重载
9. **安全纵深**：危险命令正则拦截、工作目录沙箱、SSRF 防护、超时与输出限流、人机确认
10. **工程完整性**：SSE 心跳与断连感知、热重载带回滚、四平台 CI、优雅停机、结构化日志 TraceID

---

## 八、后续方向

- [ ] MCP Server 模式——让 Mifer 自身作为 MCP Server 对外暴露能力
- [ ] Web UI 管理面板
- [ ] 会话分支与多路线对话探索
- [ ] Redis 缓存集成——会话状态与工具结果缓存
- [ ] 单元测试覆盖补全
