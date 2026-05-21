---
title: Mifer — 基于 Eino 的 AI Agent 终端助手
date: 2026-05-21T12:00:00+08:00
draft: false
tags: ["Go", "AI", "Eino", "Agent", "TUI", "LLM"]
---

[项目源码](https://github.com/mife-user/mifer)

## 前言

Mifer 是一个基于字节跳动开源 [CloudWeGo Eino](https://github.com/cloudwego/eino) 框架构建的智能 AI Agent 桌面应用。它提供 CLI（TUI）+ HTTP 双模交互，支持多 LLM 后端、多 Agent 编排协作、流式对话与 Function Calling 工具调用。一句话定位：**可编程、可扩展的桌面级 AI 助手**。

**技术栈一览：**

| 层级 | 技术选型 |
|------|----------|
| AI 编排 | CloudWeGo Eino v0.8 (ADK) |
| LLM 后端 | OpenAI / Claude / Gemini / Ollama |
| TUI 框架 | Bubble Tea + Bubbles (Elm 架构) |
| 终端渲染 | Glamour (Markdown) + Lip Gloss (样式) |
| HTTP 服务 | Gin v1.12 |
| 对话记忆 | 自建 JSONL 文件持久化 (零外部依赖) |
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
  ├── routes/      → 路由注册，组装依赖链
  ├── handler/     → AgentHandler (Chat / Memory / Exchange)
  ├── middlewares/  → JWT 认证 + CORS
  └── dto/         → 请求/响应 DTO

internal/service/  → 业务逻辑层 (AgentService)
internal/domain/   → 领域核心：AgentService / Agent 接口契约
                      
internal/ai/       → AI 核心 (无 HTTP 依赖，可独立使用)
  ├── agent/       → Eino ADK 多 Agent 编排 (6 个专家 Agent)
  ├── executor/    → adk.Runner 包装器 (流式事件处理)
  ├── llm/         → 多后端 ChatModel 管理 (Registry 模式)
  ├── memory/      → JSONL 对话记忆持久化
  ├── prompt/      → 提示词构建
  └── tools/       → Function Calling 工具定义

cli/               → CLI 客户端
  ├── client/      → HTTP API 调用 (chat / memory / exchmem)
  ├── render/      → Glamour Markdown 渲染 + Lip Gloss 样式
  └── tui/         → Bubble Tea TUI 界面 (Init/Update/View)

pkg/               → 公共基础设施 (conf / logger / auth / errorer / res / task)
config/            → YAML 配置文件 (首次运行自动生成)
```

**依赖方向**：`cmd` → `api` → `service` → `ai` → `pkg`，每层只依赖下层，`pkg` 和 `ai` 完全不依赖 `internal` 的其他部分。

---

## 二、核心设计决策

### 2.1 为什么自建 JSONL 记忆层，而不是用 Eino 自带 Memory？

Eino ADK 自带内存记忆，但它绑定于进程生命周期，重启即丢失。Mifer 自建 JSONL 文件记忆层，核心实现：

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
- **增量追加**：只写新消息，不重写整个文件，会话间切换高效
- **锁保护**：`sync.Mutex` 防止并发写入混乱
- **会话隔离**：基于 workdir 哈希生成目录名，不同项目对话互不干扰
- **切换会话**：支持 `/excmem <id>` 随时切换，自动持久化当前会话并加载新会话
- **路径安全**：校验 ID 不包含 `..` `/` `\`，防止路径穿越

### 2.2 为什么 LLM 后端用 Registry 模式？

项目需要同时接入多个模型（日常用 DeepSeek，复杂任务用 Claude，本地测试用 Ollama），各提供商的 ChatModel 创建方式不同。

```
配置中定义后端 → initBackend 按 provider 查函数表 → 创建对应的 ChatModel → 注册到 Registry
```

```go
// llm/providers.go — 函数表模式注册
var providerInitMap = map[string]func(context.Context, conf.BackendConfig) (model.BaseChatModel, error){
    "openai": initOpenAIModel,
    "claude": initClaudeModel,
    "gemini": initGeminiModel,
    "ollama": initOllamaModel,
}

func initBackend(ctx context.Context, key string, cfg conf.BackendConfig) (model.BaseChatModel, error) {
    initFn, ok := providerInitMap[cfg.Provider]  // 查表
    return initFn(ctx, cfg)
}
```

Registry 对外暴露 `Get(name)` 方法，缺失时自动 fallback 到 default。业务代码切换模型不改一行代码。

### 2.3 三级模型分配策略

根据任务复杂度分配不同能力的模型，平衡成本与质量：

| 模型级别 | 用途 | 示例 Agent |
|---------|------|-----------|
| haiku | 快速响应、简单对话 | MiTalker（日常聊天） |
| sonnet | 均衡能力、代码生成 | MiEditer / MiSummarizer / MiCommander |
| opus | 最强推理、深度分析 | MiPlanner / MiAuditor |
| default | 编排调度主脑 | Mifer（Orchestrator） |

### 2.4 为什么选择 Bubble Tea + Elm 架构？

终端 UI 框架选型时考虑了 Bubble Tea 的 Elm 架构（Model → Init → Update → View），它的优势在于：

- **状态管理清晰**：所有 UI 状态集中在 `Model` 结构体中，状态变更可预测
- **事件驱动**：按键、窗口变化、HTTP 响应、定时器 tick 都是消息，统一在 `Update()` 中分发处理
- **可组合**：viewport、textarea、spinner、list 等 Bubbles 组件可独立维护各自状态
- **鼠标支持**：viewport 鼠标滚轮滚动消息历史，体验接近 GUI

---

## 三、AI 核心详解

### 3.1 多 Agent 协作体系

基于 Eino ADK 的 `deep` 编排器（Orchestrator），Mifer 调度 6 个专家 Agent：

```
用户输入
  → Mifer (Orchestrator)   —— 分析意图，调度子 Agent
      ├── MiTalker          —— 日常对话交流 (haiku)
      ├── MiEditer          —— 文件读取、写入、创建 (sonnet)
      ├── MiSummarizer      —— 文档阅读与摘要总结 (sonnet)
      ├── MiPlanner         —— 项目计划与方案编写 (opus)
      ├── MiCommander       —— 安全执行终端命令 (sonnet + 安全策略)
      └── MiAuditor         —— 代码与配置安全审计 (opus)
```

编排器配置关键参数：
- `MaxIteration: 2`：最大 2 轮迭代，避免无限反思循环
- `EmitInternalEvents: true`：转发子 Agent 内部事件到父级事件流，使 TUI 侧边栏可显示子 Agent 及工具调用过程

### 3.2 流式执行引擎

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

所有事件通过 `callback(event, content)` 回调给调用方，TUI 和 HTTP API 共用同一套执行引擎。

### 3.3 Function Calling 工具系统

工具注册在 `internal/ai/tools/` 中，按使用场景分组：

| 工具组 | 包含工具 | 使用 Agent |
|--------|---------|-----------|
| FileTools | file_reader, file_writer, file_creator | MiEditer |
| CommandTools | command_executor (含安全策略) | MiCommander |
| AuditTools | file_reader | MiAuditor |

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

`update.go` 中定义了 9 种消息类型的处理路径：

| 消息类型 | 触发条件 | 处理逻辑 |
|---------|----------|---------|
| WindowSizeMsg | 终端尺寸变化 | 重新计算 viewport/sidebar/textarea 尺寸 |
| MouseMsg | 鼠标滚轮/点击 | 委托给对应 viewport 处理 |
| KeyMsg | 按键输入 | 多模式分发：记忆模式 / 补全模式 / 正常输入 |
| streamStatusMsg | Agent切换/工具调用 | 更新侧边栏状态 |
| streamContentMsg | AI 流式输出 | 追加到 accBuf，逐字渲染 |
| streamDoneMsg | 流式传输完成 | Markdown 渲染，追加到消息列表 |
| chatRespMsg | 非流式回退 | Glamour 渲染，显示完整响应 |
| systemMsg | /viewmemory 等命令 | 追加系统消息到对话区 |
| spinner.TickMsg | 旋转动画帧 | 推进 spinner 动画 |

### 4.3 Tab 命令补全

输入以 `/` 开头时自动触发命令补全：

```
/ → 匹配所有命令/help、/exit、/viewmemory、/excmem
  → 首次 Tab：填入最长公共前缀
  → 再次 Tab：循环切换候选项
  → Enter 确认
```

补全列表最多显示 5 条，超出后视窗滚动（不可见区域自动计算偏移）。

---

## 五、HTTP API 层

```go
// routes/router.go
api := router.Group("/api")
{
    ai := api.Group("/ai")
    {
        ai.POST("/chat", r.agentHandler.Chat)    // SSE 流式聊天
    }
    memory := api.Group("/memory")
    {
        memory.GET("", r.agentHandler.ListMemories)          // 列出所有记忆会话
        memory.GET("/:id", r.agentHandler.LoadMemory)        // 加载指定会话
        memory.POST("/exchange/:id", r.agentHandler.ExchangeMemory)  // 切换会话
    }
}
```

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

event: token
data: {"prompt": 150, "completion": 80, "total": 230, "cached": 20, "reasoning": 45}
```

---

## 六、基础设施

### 配置管理（Viper）

- 首次运行自动生成 `config/dev.yaml` 默认配置文件
- 支持环境变量覆盖（`MIFER_AI_BASEURL`, `MIFER_AI_APIKEY`, `MIFER_AI_MODEL` 等）
- 多环境配置：dev 模式路径 `./config/`，prod 模式路径 `~/.mifer/config/`

### 日志系统（Zap + Lumberjack）

- dev → 控制台彩色输出，prod → JSON 格式
- 日志轮转：单文件最大 10MB，保留 5 个备份
- 结构化字段辅助函数

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

1. **Eino ADK 多 Agent 编排**：6 个专家 Agent + Orchestrator 协作，三级模型路由（haiku/sonnet/opus），2 轮迭代控制
2. **自建 JSONL 记忆层**：增量追加 + 锁保护 + 多会话隔离 + 路径安全校验，零外部依赖
3. **Registry 多 LLM 管理**：4 个 provider 函数表注册 + fallback 机制，切换模型不改业务代码
4. **流式 SSE + 事件管道**：Agent 切换/工具调用/推理过程/token 统计全部以事件穿透到 TUI 侧边栏
5. **Bubble Tea TUI**：Elm 架构 + Markdown 渲染 + 流式实时输出 + 命令补全 + 历史导航 + 记忆管理
6. **双模交互**：TUI 和 HTTP API 共享同一套 AI 执行引擎，前后端分离但状态一致

---

## 八、待完善方向

- [ ] MCP 协议支持（Client/Server），接入第三方工具生态
- [ ] Skills 技能系统，支持 YAML 声明式自定义技能
- [ ] RAG 检索增强，本地代码库语义索引
- [ ] Web UI 管理面板
- [ ] Docker 一键部署
- [ ] 单元测试覆盖
- [ ] Windows Terminal 兼容性优化
