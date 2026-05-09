---
title: 'Eino框架详解：从零开始，像搭积木一样构建AI应用'
date: 2026-05-05T12:00:00+08:00
draft: false
tags: ["Go", "Eino", "LLM", "AI", "框架", "CloudWeGo"]
---

## 前言：从一个具体目标说起

假设你想用 Go 写一个类似 Claude Code 的 CLI 工具——用户在终端输入问题，AI 能读文件、搜索代码、执行命令，最后给出回答。

要自己从头实现的话，你需要处理：
- 调用大模型 API（不同厂商接口还不同）
- 管理对话历史（哪些消息发给模型？哪些不需要？）
- 工具调用逻辑（模型说"我要读文件"→你去读→结果发回模型→模型继续思考→可能又调用工具→循环…）
- 流式输出（一个字一个字地显示）
- 错误处理和重试

这些很难。Eino 就是帮你把这些脏活累活都处理好的框架。

**本文会带你用搭积木的方式，一步步理解 Eino 的每个部分，最终实现一个迷你版 Claude Code。**

---

## 一、最简单的起点：和模型说一句话

先忘掉 Eino，想一下"和 AI 对话"这件事的本质是什么？

### 1.1 对话的本质：发送 Message，收到 Message

你和 AI 的每一次对话，本质上就是两件事：

```
你发送：一堆 Message（消息列表）
         ↓
      AI 模型处理
         ↓
你收到：一个新的 Message（AI 的回复）
```

**Message 是什么？** 它就是一条聊天记录，包含两个关键信息：

```go
// 一条消息
type Message struct {
    Role    string    // 谁说的？ "system" / "user" / "assistant" / "tool"
    Content string    // 说了什么？
}
```

- `system`：你给 AI 的"人设"（"你是一个编程助手"）
- `user`：你说的话（"帮我读一下 main.go"）
- `assistant`：AI 说的话（"好的，文件内容是…"）
- `tool`：工具执行的结果（文件内容、命令输出等）

**所以一次对话就是：你准备一个 `[]*Message` 列表，发给模型，模型返回一个新的 `*Message`。**

### 1.2 用 Eino 实现最简单的对话

```go
package main

import (
    "context"
    "fmt"

    "github.com/cloudwego/eino/schema"
    "github.com/cloudwego/eino-ext/components/model/openai"
)

func main() {
    ctx := context.Background()

    // 第1步：创建一个模型连接（就像拨通电话）
    model, _ := openai.NewChatModel(ctx, &openai.ChatModelConfig{
        Model:  "gpt-4o-mini",           // 用哪个模型
        APIKey: "sk-your-api-key",       // 你的 API 密钥
    })

    // 第2步：准备你要发送的消息
    messages := []*schema.Message{
        schema.SystemMessage("你是一个Go语言编程助手，用中文回答"),  // 人设
        schema.UserMessage("什么是goroutine？"),                    // 你的问题
    }

    // 第3步：发给模型，拿到回复
    reply, _ := model.Generate(ctx, messages)

    // 第4步：打印
    fmt.Println(reply.Content)
    // 输出：Goroutine 是 Go 语言中的轻量级线程...
}
```

到这里你已经能和大模型对话了。但 `Generate()` 具体是怎么工作的？`ChatModelConfig` 还有哪些配置项？`Message` 结构体到底包含哪些字段？在进入 Tool 之前，先把这些基础打牢。

### 1.3 非流式输出详解：Generate() 到底做了什么

`model.Generate(ctx, messages)` 是 Eino 中最基础、最常用的调用方式。它的工作模式是**阻塞等待，一次性返回完整结果**。

**函数签名：**

```go
func (cm *ChatModel) Generate(
    ctx   context.Context,       // 上下文，控制超时和取消
    input []*schema.Message,     // 对话消息列表
    opts  ...model.Option,       // 可选参数（温度、最大Token等）
) (*schema.Message, error)      // 返回完整回复或错误
```

**各参数的含义：**

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `ctx` | `context.Context` | 是 | 用于超时控制。如果模型调用太久，可以通过 ctx 取消 |
| `input` | `[]*schema.Message` | 是 | 你要发给模型的完整对话历史，包含 system/user/assistant/tool 消息 |
| `opts` | `...model.Option` | 否 | 临时覆盖配置，如本次调用提高温度 `model.WithTemperature(0.8)` |

**返回值：**

| 返回值 | 类型 | 说明 |
|---|---|---|
| 第一个 | `*schema.Message` | AI 的完整回复消息（全部生成完后一次性返回） |
| 第二个 | `error` | 调用失败的原因（网络错误、API返回错误等） |

**阻塞意味着什么？** 调用 `Generate()` 后，你的程序会"停住"等待，直到模型**完全生成完**所有内容才继续往下走。如果模型需要 10 秒生成回答，你的程序就卡 10 秒。

```
时间线 ──────────────────────────────────────────────→

你的程序                    AI 模型服务端
  │                            │
  ├─ Generate(messages) ──────→│ 收到请求
  │  (阻塞中...)              │ 生成 token 1
  │  (阻塞中...)              │ 生成 token 2
  │  (阻塞中...)              │ 生成 token 3
  │  (阻塞中...)              │ ...生成完成
  │←── *Message ──────────────│ 返回完整回复
  │                            │
  ├─ fmt.Println(reply.Content)   ← 拿到结果，继续执行
```

**完整的非流式调用示例（含错误处理）：**

```go
func askModel(ctx context.Context, model openai.ChatModel, question string) {
    messages := []*schema.Message{
        schema.SystemMessage("你是一个Go语言专家，用中文回答"),
        schema.UserMessage(question),
    }

    // 设置超时
    ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
    defer cancel()

    reply, err := model.Generate(ctx, messages)
    if err != nil {
        fmt.Printf("调用模型失败: %v\n", err)
        return
    }

    // 检查模型是否调用了工具
    if len(reply.ToolCalls) > 0 {
        fmt.Println("模型请求调用工具而非直接回答:")
        for _, tc := range reply.ToolCalls {
            fmt.Printf("  - %s(%s)\n", tc.Function.Name, tc.Function.Arguments)
        }
        return
    }

    // 正常的文字回复
    fmt.Println(reply.Content)
}
```

### 1.4 ChatModelConfig 结构体全字段

创建模型连接时，`ChatModelConfig` 决定了模型的所有行为：

```go
type ChatModelConfig struct {
    // ── 必填字段 ──
    Model  string // 模型名称。如 "gpt-4o", "gpt-4o-mini", "deepseek-chat"
    APIKey string // API 密钥。支持从环境变量读取

    // ── 连接相关 ──
    BaseURL string // 自定义 API 地址。默认是 OpenAI 官方地址。
                   // 用中转站或兼容接口时必填，如 "https://api.deepseek.com/v1"
    Timeout time.Duration // 单次请求的超时时间，建议 30s~120s

    // ── 生成参数（控制回答风格） ──
    Temperature *float32 // 温度，范围 0~2。越高回答越随机、有创造性
                         // 0.1~0.3 适合代码/精确任务，0.7~1.0 适合创意写作
    MaxTokens   *int     // 最大输出 Token 数。限制回复长度，防止一次返回太长
    TopP        *float32 // 核采样，范围 0~1。另一种控制随机性的方式
                         // 一般调 Temperature 就够了，这个选填

    // ── 高级选项 ──
    Stop       []string // 停止词。模型遇到这些词就停止生成
    ExtraFields map[string]any // 需要透传给 API 的额外字段（如某些厂商的特殊参数）
}
```

**不同场景的配置示例：**

```go
// 场景1：最小配置（本地开发测试）
model, _ := openai.NewChatModel(ctx, &openai.ChatModelConfig{
    Model:  "gpt-4o-mini",
    APIKey: os.Getenv("OPENAI_API_KEY"),
})

// 场景2：代码生成（需要精确、确定性的输出）
temp := float32(0.1)
maxTokens := 8192
model, _ := openai.NewChatModel(ctx, &openai.ChatModelConfig{
    Model:       "gpt-4o",
    APIKey:      os.Getenv("OPENAI_API_KEY"),
    Temperature: &temp,       // 极低温度，保证输出稳定
    MaxTokens:   &maxTokens,  // 代码可能很长，给足空间
    Timeout:     60 * time.Second,
})

// 场景3：使用 DeepSeek 等兼容接口
model, _ := openai.NewChatModel(ctx, &openai.ChatModelConfig{
    Model:   "deepseek-chat",
    APIKey:  os.Getenv("DEEPSEEK_API_KEY"),
    BaseURL: "https://api.deepseek.com/v1",  // ← 关键：指向兼容接口
})

// 场景4：通过中转站（如 one-api）访问
model, _ := openai.NewChatModel(ctx, &openai.ChatModelConfig{
    Model:   "gpt-4o",
    APIKey:  os.Getenv("ONEAPI_KEY"),
    BaseURL: "https://your-proxy.com/v1",     // ← 中转站地址
})
```

> **注意**：`Temperature`、`MaxTokens`、`TopP` 为什么是指针？因为 Go 中无法区分"没设置"和"设置为 0"。用指针后，`nil` 表示用模型默认值，非 `nil` 表示你显式设置了值。

### 1.5 Message 结构体详解

`schema.Message` 是整个 Eino 框架中最核心的数据载体。**一切对话都围绕 Message 展开——输入是 `[]*Message`，输出也是 `*Message`。**

```go
type Message struct {
    // ── 基础字段 ──
    Role    string // 消息角色。必须且只能是以下四种之一：
                   //   schema.System    - 给 AI 定人设
                   //   schema.User      - 用户说的话
                   //   schema.Assistant - AI 说的话（或工具调用请求）
                   //   schema.Tool      - 工具执行的结果
    Content string // 消息的文字内容。当 ToolCalls 不为空时，Content 通常为空

    // ── 工具调用相关 ──
    ToolCalls []ToolCall // 模型发出的工具调用请求列表。
                         // 不为空 = 模型想用工具而不是直接回答
    ToolCallID string    // 当 Role == schema.Tool 时，对应哪个 ToolCall
    ToolName  string     // 当 Role == schema.Tool 时，来自哪个工具

    // ── 元数据 ──
    Extra map[string]any // 扩展字段，存放各模型特有的额外信息
}
```

**四种消息的构造方式：**

```go
// 1. System 消息 —— 用辅助函数
systemMsg := schema.SystemMessage("你是一个Go语言专家，用中文回答，代码风格简洁")

// 2. User 消息 —— 用辅助函数
userMsg := schema.UserMessage("帮我读一下 main.go 的内容")

// 3. Assistant 消息 —— 自己构造（通常不需要手动创建，模型返回的就是）
// 情况A：纯文字回复
textReply := &schema.Message{
    Role:    schema.Assistant,
    Content: "main.go 中定义了三个函数...",
}
// 情况B：工具调用请求（Content 为空！）
toolCallReply := &schema.Message{
    Role:    schema.Assistant,
    Content: "",  // 空！
    ToolCalls: []schema.ToolCall{
        {
            ID: "call_abc123",
            Function: schema.FunctionCall{
                Name:      "read_file",
                Arguments: `{"path": "main.go"}`,
            },
        },
    },
}

// 4. Tool 消息 —— 用辅助函数
toolMsg := schema.ToolMessage(
    "package main\n\nfunc main() { ... }", // 工具执行结果（字符串）
    "read_file",                            // 工具名称
)
// 注意：ToolMessage 的第二个参数是工具名，模型需要知道这个结果来自哪个工具
```

**ToolCall 和 FunctionCall 结构体：**

```go
type ToolCall struct {
    ID       string       // 这次工具调用的唯一ID，用于关联 ToolMessage
    Type     string       // 通常为 "function"
    Function FunctionCall // 具体的函数调用信息
}

type FunctionCall struct {
    Name      string // 工具名称，和 ToolInfo.Name 对应
    Arguments string // JSON 格式的调用参数，如 `{"path": "main.go", "pattern": "func"}`
}
```

> **核心规则**：当 `Message.ToolCalls` 不为空时，`Message.Content` 通常为空。模型在说"我要调用工具"而不是"我在回答你"。你的代码需要检查 `ToolCalls`，执行对应工具，把结果用 ToolMessage 发回去。

### 1.6 ChatModel 接口全貌

Eino 的模型组件都实现了 `ChatModel` 接口。理解这个接口就理解了模型能做什么：

```go
type ChatModel interface {
    // ── 核心方法 ──

    // 非流式调用：阻塞等待完整回复（本节讲的）
    Generate(ctx context.Context, input []*Message, opts ...Option) (*Message, error)

    // 流式调用：返回一个 Stream，可以逐个接收生成的 Token（详见第八章）
    Stream(ctx context.Context, input []*Message, opts ...Option) (*StreamReader[Message], error)

    // ── 工具相关 ──

    // 绑定工具：告诉模型"你可以用这些工具"
    BindTools(tools []*schema.ToolInfo) error

    // 获取当前绑定的工具列表
    GetTools() []*schema.ToolInfo

    // ── 类型信息 ──
    GetType() string // 返回模型类型，如 "openai"
}
```

**关键方法对比：**

| 方法 | 返回方式 | 适用场景 |
|---|---|---|
| `Generate()` | 一次性返回完整 `*Message` | CLI 工具、脚本、批量处理——不需要实时显示 |
| `Stream()` | 返回 `*StreamReader`，逐个读取 chunk | 聊天界面、实时终端输出——逐字显示 |
| `BindTools()` | 无返回值（error） | 需要模型能调用工具时（读文件、搜索等） |

**非流式调用时不绑定工具 vs 绑定工具的对比：**

```go
// 不带工具：纯对话
reply, _ := model.Generate(ctx, messages)
fmt.Println(reply.Content)  // 直接拿到文字回复

// 带工具：模型可能返回 ToolCall
model.BindTools(tools)
reply, _ := model.Generate(ctx, messages)
if len(reply.ToolCalls) > 0 {
    // 模型想用工具！你需要执行工具，把结果发回去
} else {
    // 模型直接回答
    fmt.Println(reply.Content)
}
```

---

## 二、让模型"动手"：Tool 是什么？

### 2.1 直观理解 Tool

模型本身只会"说话"，它不能读文件、不能上网、不能执行命令。**Tool 就是给模型安装的"手"，让它能做事。**

举个例子。你对 AI 说"读取 main.go 的内容"，流程是这样的：

```
你: "读取 main.go"
     ↓
模型思考: "我需要读文件，调用 read_file 工具，参数是 main.go"
     ↓
模型返回的不是文字，而是一个"工具调用请求" ← 关键！
     ↓
你的程序收到这个请求，真的去读文件
     ↓
把文件内容包装成一条 Message 发回给模型
     ↓
模型看到文件内容，组织语言回答你
```

**关键理解：模型不是只输出文字，它也可以输出工具调用请求。Tool 就是把"模型的意图"和"程序的动作"连接起来的桥梁。**

### 2.2 一个具体的 Tool 长什么样

```go
// 定义一个"读取文件"的工具
type ReadFileTool struct{}

// Info() 告诉模型：我叫什么、我能干什么、需要什么参数
func (t *ReadFileTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
    return &schema.ToolInfo{
        Name: "read_file",                    // 工具名，模型用这个名字调用
        Desc: "读取指定路径的文件内容",          // 描述，模型据此判断何时使用
        ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
            "path": {                         // 参数名
                Type:     schema.String,      // 参数类型
                Desc:     "文件路径",          // 参数说明
                Required: true,               // 是否必填
            },
        }),
    }, nil
}

// InvokableRun() 是真正干活的：收到参数，执行操作，返回结果
func (t *ReadFileTool) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    // args 是 JSON 字符串，比如 {"path": "main.go"}
    var params struct{ Path string }
    json.Unmarshal([]byte(args), &params)

    content, err := os.ReadFile(params.Path)
    if err != nil {
        return "", err
    }
    return string(content), nil  // 返回文件内容（纯文本字符串）
}
```

拆解一下，一个 Tool 只有两个方法：

| 方法 | 作用 | 通俗理解 |
|---|---|---|
| `Info()` | 告诉模型"我能做什么、需要什么参数" | 就像你递给人一份说明书 |
| `InvokableRun()` | 真的执行操作，返回结果 | 人拿到说明书后干活 |

**Info() 返回到哪里去了？** 它被转成 JSON 发给模型，大模型根据描述自动判断什么时候该用哪个工具、填什么参数。你不需要写任何"if 用户说了xxx就调用yyy"的逻辑。

#### InvokableRun 函数签名详解

Tool 的核心是 `InvokableRun` 方法。它的签名值得仔细看：

```go
InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error)
//            ^上下文        ^JSON参数字符串   ^可选配置         ^执行结果  ^错误
```

**参数拆解：**

| 参数 | 类型 | 说明 |
|---|---|---|
| `ctx` | `context.Context` | 上下文。可从 ctx 中取到节点路径、回调等信息 |
| `args` | `string` | **JSON 字符串**。模型填的参数都在里面，如 `{"path":"main.go"}` |
| `opts` | `...tool.Option` | 可选配置。框架用的，你自己实现 Tool 时一般忽略 |

**返回值**：为什么只返回 `(string, error)` 而不是 `(*schema.Message, error)`？

因为 Tool 返回的纯文本字符串会被 Eino 自动包装成一条 `ToolMessage`——`schema.ToolMessage(result, toolName)`。你只管返回字符串，框架帮你包。

**常见的 args 解析写法（推荐用 json.Unmarshal）：**

```go
func (t *ReadFileTool) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    // 写法1：用匿名 struct（最常用）
    var params struct {
        Path string `json:"path"`
    }
    if err := json.Unmarshal([]byte(args), &params); err != nil {
        return "", fmt.Errorf("参数解析失败: %w", err)
    }
    // 用 params.Path 执行...
    data, err := os.ReadFile(params.Path)
    if err != nil {
        return "", err
    }
    return string(data), nil
}

// 写法2：多个参数
func (t *SearchCodeTool) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    var params struct {
        Pattern string `json:"pattern"`
        Dir     string `json:"dir"`
    }
    json.Unmarshal([]byte(args), &params)
    // 用 params.Pattern 和 params.Dir ...
}
```

> **注意**：`args` 是裸 JSON，不是 `{"args": ...}` 嵌套结构。模型生成的参数名必须和你 `json:"xxx"` tag 匹配。

#### BaseTool 接口

Eino 中所有 Tool 都实现 `tool.BaseTool` 接口：

```go
type BaseTool interface {
    // 告诉模型这个工具叫什么、做什么、需要什么参数
    Info(ctx context.Context) (*schema.ToolInfo, error)

    // 真正执行
    InvokableRun(ctx context.Context, argumentsInJSON string, opts ...Option) (string, error)
}
```

实现这两个方法，你的 struct 就能直接放进 Agent 或 Graph 的工具列表里。

### 2.3 模型如何"调用"工具——ToolCall 机制

当你把 Tool 注册给模型后（通过 `BindTools`），对话就会发生变化：

```go
// 把 readFileTool 告诉模型
model.BindTools([]*schema.ToolInfo{readFileTool.Info(ctx)})

// 发送消息
messages := []*schema.Message{
    schema.SystemMessage("你是一个编程助手"),
    schema.UserMessage("读取 main.go 的内容"),
}

reply, _ := model.Generate(ctx, messages)

// 关键：检查模型是"回复文字"还是"调用工具"
if len(reply.ToolCalls) > 0 {
    // 模型选择了调用工具！
    tc := reply.ToolCalls[0]
    fmt.Println(tc.Function.Name)   // "read_file"
    fmt.Println(tc.Function.Arguments) // `{"path": "main.go"}`
    // 注意：reply.Content 此时是空的！
} else {
    // 模型直接回答了文字
    fmt.Println(reply.Content)
}
```

**这里有一个非常关键的认知**：模型返回的 `Message` 有两种情况——

| 情况 | `reply.Content` | `reply.ToolCalls` | 含义 |
|---|---|---|---|
| 直接回答 | 有内容 | 空 | 模型觉得不需要用工具，直接说话 |
| 调用工具 | 空 | 有数据 | 模型说"我需要用这个工具，参数是xxx" |

**ToolCall 就是模型说"我不会回答这个问题，我要先用某个工具"，然后你执行工具，把结果发回去，模型再继续思考。**

### 2.4 ToolInfo 和 ParameterInfo 结构体详解

`Info()` 方法返回的 `*schema.ToolInfo` 是模型了解工具的唯一途径。你写得越清晰，模型调用越准确：

```go
type ToolInfo struct {
    Name        string        // 工具名称。模型用这个名字来调用
                              // 命名建议：snake_case，动词_名词，如 "read_file"
    Desc        string        // 工具描述。模型据此判断何时使用这个工具
                              // 写清楚"做什么、什么时候用、返回什么"
    ParamsOneOf *ParamsOneOf  // 参数定义。告诉模型需要哪些参数、什么类型
}

type ParamsOneOf struct {
    // 内部字段...
}
```

**ParamsOneOf 通过 `NewParamsOneOfByParams` 创建**，传入参数 map：

```go
schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
    "参数名": {字段...},
})
```

**ParameterInfo 结构体：**

```go
type ParameterInfo struct {
    Type     schema.DataType  // 参数类型：schema.String / schema.Number / schema.Boolean
    Desc     string           // 参数说明。写清楚这个参数是用来干什么的
    Required bool             // 是否必填。true=模型必须填，false=可选
    Enum     []string         // 可选。限制参数的合法值，如 ["go", "rust", "python"]
}
```

**Info() 写得好 vs 写得差的对比：**

```go
// ❌ 写得差：描述模糊，模型可能乱调用
func (t *Tool) Info(ctx context.Context) (*schema.ToolInfo, error) {
    return &schema.ToolInfo{
        Name: "tool1",
        Desc: "do something",
        ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
            "p1": {Type: schema.String},
        }),
    }, nil
}

// ✅ 写得好：描述清晰，模型能准确判断何时使用、填什么参数
func (t *ReadFileTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
    return &schema.ToolInfo{
        Name: "read_file",
        Desc: "读取指定路径的文件全部内容并返回。" +
              "用于查看源代码、配置文件、日志等。" +
              "不要在文件过大（>1MB）时使用此工具。",
        ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
            "path": {
                Type:     schema.String,
                Desc:     "要读取的文件路径。可以是相对于项目根目录的路径，也可以是绝对路径",
                Required: true,
            },
        }),
    }, nil
}
```

> **提示**：`Desc` 字段直接决定了模型判断"是否该用这个工具"的准确性。花 2 分钟把 Desc 写清楚，比花 2 小时调 prompt 更有效。



## 三、ReAct 循环：让模型"思考→行动→再思考"

### 3.1 手动实现 ReAct 循环

有了上面的理解，手写一个 ReAct 循环其实就是：

```
1. 把用户问题发给模型
2. 看模型返回什么：
   - 如果是文字 → 打印出来，结束
   - 如果是 ToolCall → 执行对应的工具，把结果发回模型，回到第2步
```

用代码写出来：

```go
func manualReAct(model ChatModel, tools map[string]Tool, userInput string) {
    messages := []*schema.Message{
        schema.UserMessage(userInput),
    }

    // 最多循环 20 次
    for i := 0; i < 20; i++ {
        reply, _ := model.Generate(ctx, messages)

        // 情况1：模型直接回答 → 打印并结束
        if len(reply.ToolCalls) == 0 {
            fmt.Println(reply.Content)
            return
        }

        // 情况2：模型要调工具 → 执行工具
        tc := reply.ToolCalls[0]
        toolName := tc.Function.Name
        toolArgs := tc.Function.Arguments

        // 把模型的 ToolCall 请求也加入对话历史
        messages = append(messages, reply)

        // 执行工具
        tool := tools[toolName]
        result, _ := tool.InvokableRun(ctx, toolArgs)

        // 把工具执行结果也加入对话历史
        messages = append(messages, schema.ToolMessage(result, toolName))

        // 继续循环——模型看到工具结果后，可能再调用工具，也可能回答
    }
}
```

这就是 ReAct 循环的全部秘密：**循环地把消息发给模型，执行模型要求的工具，把结果发回去，直到模型不再调用工具为止。**

### 3.2 Eino 的 Agent 帮你自动做这件事

上面 30 行代码的手动循环，Eino 的 `ChatModelAgent` 帮你做了。你只需要：

```go
// 创建 Agent，告诉它：你用这个模型，你有这些工具
agent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name:        "coder",          // Agent 的名字
    Description: "编程助手",
    Instruction: "你是一个Go语言编程助手，可以用工具读取文件、搜索代码、执行命令",
    Model:       model,
    ToolsConfig: adk.ToolsConfig{
        ToolsNodeConfig: compose.ToolsNodeConfig{
            Tools: []tool.BaseTool{readFileTool, searchTool, shellTool},
        },
    },
    MaxIterations: 20,  // 最多循环20次，防止死循环
})
```

**Agent 就是把"模型+工具+ReAct循环"打包成的一个整体。** 你给它一个指令，它内部自动处理"思考→调工具→看结果→再思考"的循环。

---

## 四、Runner：怎么和 Agent 交互

### 4.1 Runner 的作用

Agent 有了，但怎么"运行"它呢？用 `Runner`。

```go
// Runner 是 Agent 的执行器
runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: agent})
```

Runner 的作用：
- 管理对话的**生命周期**（开始、进行中、结束）
- 管理对话**历史**（记住之前说过什么）
- 提供**事件流**（实时告诉你 Agent 在干什么）

### 4.2 Query()：提问并获取事件流

```go
// 向 Agent 提问，返回一个"事件迭代器"
iter := runner.Query(ctx, "读取 main.go 的内容，看看 main 函数做了什么")

// 逐个取出事件
for {
    event, ok := iter.Next()
    if !ok {
        break  // 没有更多事件了，对话结束
    }
    // 处理这个事件
    fmt.Println(event.Message.Content)
}
```

**事件是什么？** Runner 把 Agent 的执行过程拆成一个个事件（Event），让你能实时看到进度。一个典型的对话会产生这样的事件序列：

```
Event 1: "我需要读取 main.go 文件"           ← Agent 开始思考
Event 2: (ToolCall: read_file, main.go)     ← Agent 决定调用工具
Event 3: "文件内容如下：package main..."      ← 工具返回结果
Event 4: "main 函数做了三件事：..."           ← Agent 给出最终回答
```

### 4.3 对话历史保存在哪里

Runner 内部维护了一个**会话**（Session）。每次 Query 的问题和历史都会被记住：

```go
runner.Query(ctx, "我叫小明")     // 第一次对话
runner.Query(ctx, "我叫什么？")   // 第二次对话，Agent 会回答"你叫小明"
```

这让你不用手动管理 `[]*Message` 列表。Runner 帮你自动维护对话历史。

### 4.4 RunnerConfig 结构体

创建 Runner 时的配置项不多，但每个都影响行为：

```go
type RunnerConfig struct {
    Agent          Agent           // 必填。Runner 要运行的 Agent（单 Agent 或多 Agent）
    EnableStreaming bool           // 是否启用流式输出，默认 false
    CheckPointID   string         // 断点 ID（用于 Interrupt/Resume 恢复）
}
```

**示例：**

```go
// 标准配置
runner := adk.NewRunner(ctx, adk.RunnerConfig{
    Agent: agent,
})

// 显式启用流式（如果你需要事件流逐 token 输出）
runner := adk.NewRunner(ctx, adk.RunnerConfig{
    Agent:           agent,
    EnableStreaming: true,
})
```

> `EnableStreaming` 为 true 时，`iter.Next()` 返回的事件里 `Message.Content` 是增量 token（一个字/一个词）；为 false 时是累积内容。通常用 Agent 时不需要手动设置这个，Event 迭代器本身就支持逐事件消费。

### 4.5 Iter 类型：如何消费事件流

`runner.Query()` 返回的是一个迭代器（`Iter`），它提供了两个关键方法：

```go
type AgentEventIter interface {
    // Next 返回下一个事件。如果没有更多事件了，ok 为 false
    Next() (event *adk.AgentEvent, ok bool)
}
```

**标准消费模式：**

```go
iter := runner.Query(ctx, "帮我分析代码")

for {
    event, ok := iter.Next()
    if !ok {
        break  // Stream 结束
    }
    // event 是 *adk.AgentEvent，包含：
    //   event.Message       - *schema.Message，当前的回复片段
    //   event.AgentName     - 哪个 Agent 产生的（多 Agent 场景有用）
    //   event.Action        - 事件类型（思考、工具调用、回复等）
    fmt.Print(event.Message.Content)
}
```

**AgentEvent 常见字段：**

```go
type AgentEvent struct {
    Message   *schema.Message // 当前的回复内容
    AgentName string          // 产生此事件的 Agent 名称
    Action    *AgentAction    // 事件类型（可选）
    Err       error           // 异常事件
}
```

`Action` 帮助你知道 Agent 在干什么——是在思考、调工具、还是输出最终回答。在多 Agent 场景中，`AgentName` 能让你区分是哪个专家在说话。



## 五、搭建迷你 Claude Code

现在回到最初的目标——用 Eino 写一个 CLI AI 编程助手。

### 5.1 需要哪些工具？

Claude Code 能做的事，我们至少需要三个基本工具：

| 工具 | 作用 |
|---|---|
| `read_file` | 读取文件内容 |
| `search_code` | 在项目中搜索代码（grep） |
| `run_command` | 执行终端命令 |

### 5.2 定义工具

```go
// ============ 工具1：读取文件 ============
type ReadFileTool struct{}

func (t *ReadFileTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
    return &schema.ToolInfo{
        Name: "read_file",
        Desc: "读取指定文件的内容。用于查看源代码、配置文件等。",
        ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
            "path": {Type: schema.String, Desc: "文件路径（相对于项目根目录）", Required: true},
        }),
    }, nil
}

func (t *ReadFileTool) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    var p struct{ Path string }
    json.Unmarshal([]byte(args), &p)
    data, err := os.ReadFile(p.Path)
    if err != nil {
        return fmt.Sprintf("错误：%v", err), nil  // 即使失败也返回字符串，让模型知道出错了
    }
    return string(data), nil
}

// ============ 工具2：搜索代码 ============
type SearchCodeTool struct{}

func (t *SearchCodeTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
    return &schema.ToolInfo{
        Name: "search_code",
        Desc: "在项目中搜索匹配指定模式的代码行，类似 grep",
        ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
            "pattern": {Type: schema.String, Desc: "搜索的正则表达式或关键字", Required: true},
            "path":    {Type: schema.String, Desc: "搜索目录，默认当前目录", Required: false},
        }),
    }, nil
}

func (t *SearchCodeTool) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    var p struct {
        Pattern string `json:"pattern"`
        Path    string `json:"path"`
    }
    json.Unmarshal([]byte(args), &p)
    if p.Path == "" {
        p.Path = "."
    }
    cmd := exec.Command("grep", "-rn", p.Pattern, p.Path)
    output, err := cmd.CombinedOutput()
    result := string(output)
    if len(result) == 0 {
        result = "没有找到匹配结果"
    }
    if err != nil {
        result = fmt.Sprintf("搜索完成：\n%s", result)
    }
    return result, nil
}

// ============ 工具3：执行命令 ============
type RunCommandTool struct{}

func (t *RunCommandTool) Info(ctx context.Context) (*schema.ToolInfo, error) {
    return &schema.ToolInfo{
        Name: "run_command",
        Desc: "在终端执行命令并返回输出。用于运行测试、构建代码、查看文件列表等",
        ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
            "command": {Type: schema.String, Desc: "要执行的命令", Required: true},
        }),
    }, nil
}

func (t *RunCommandTool) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    var p struct{ Command string }
    json.Unmarshal([]byte(args), &p)
    cmd := exec.Command("bash", "-c", p.Command)
    output, _ := cmd.CombinedOutput()
    return string(output), nil
}
```

### 5.3 组装成完整程序

```go
package main

import (
    "bufio"
    "context"
    "encoding/json"
    "fmt"
    "os"
    "os/exec"

    "github.com/cloudwego/eino/adk"
    "github.com/cloudwego/eino/components/tool"
    "github.com/cloudwego/eino/compose"
    "github.com/cloudwego/eino/schema"
    "github.com/cloudwego/eino-ext/components/model/openai"
)

func main() {
    ctx := context.Background()

    // ── 步骤1：创建模型 ──
    model, _ := openai.NewChatModel(ctx, &openai.ChatModelConfig{
        Model:  "gpt-4o",
        APIKey: os.Getenv("OPENAI_API_KEY"),
    })

    // ── 步骤2：创建工具 ──
    readTool := &ReadFileTool{}
    searchTool := &SearchCodeTool{}
    shellTool := &RunCommandTool{}

    // ── 步骤3：创建 Agent ──
    agent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
        Name:        "mini-cc",
        Description: "迷你版 Claude Code，Go 语言编程助手",
        Instruction: `你是一个 Go 语言编程助手，运行在用户的终端中。

你可以使用以下工具：
- read_file: 读取文件内容
- search_code: 在项目中搜索代码
- run_command: 执行终端命令

工作方式：
1. 理解用户的需求
2. 先用 search_code 找到相关代码
3. 用 read_file 查看具体文件
4. 如果需要运行测试或构建，使用 run_command
5. 给出你的分析或建议

注意：用中文回答，用简洁的方式呈现代码。`,
        Model: model,
        ToolsConfig: adk.ToolsConfig{
            ToolsNodeConfig: compose.ToolsNodeConfig{
                Tools: []tool.BaseTool{readTool, searchTool, shellTool},
            },
        },
        MaxIterations: 20,
    })

    // ── 步骤4：创建 Runner ──
    runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: agent})

    // ── 步骤5：交互循环 ──
    scanner := bufio.NewScanner(os.Stdin)
    fmt.Println("mini-cc 就绪，输入问题（输入 exit 退出）：")

    for {
        fmt.Print("\n> ")
        if !scanner.Scan() {
            break
        }
        input := scanner.Text()
        if input == "exit" {
            break
        }
        if input == "" {
            continue
        }

        // 提问
        iter := runner.Query(ctx, input)

        // 逐个接收事件
        for {
            event, ok := iter.Next()
            if !ok {
                break
            }
            // 流式打印回复内容
            fmt.Print(event.Message.Content)
        }
        fmt.Println()
    }
}
```

### 5.4 运行效果

```text
mini-cc 就绪，输入问题（输入 exit 退出）：

> 帮我看看 main.go 里有什么函数

我先搜索一下项目中有哪些 Go 文件。
[调用 search_code: pattern="func ", path="."]

搜索到以下函数：main()、handleRequest()、parseConfig()
让我读取 main.go 查看详情。
[调用 read_file: path="main.go"]

main.go 中有三个函数：
1. main() - 程序入口，初始化配置并启动HTTP服务
2. handleRequest() - 处理HTTP请求
3. parseConfig() - 解析配置文件

> exit
再见！
```

---

## 六、深入理解 Agent 的内部机制

上一节我们直接用 Agent 就完成了，但你可能会好奇：**Agent 内部到底发生了什么？**

### 6.1 第一次对话的完整数据流

假设你输入"读取 main.go"，Agent 内部做的事情是这样的：

```
第1轮 ─────────────────────────────────
→ 发送给模型的消息：
  SystemMessage("你是一个编程助手...")
  UserMessage("读取 main.go")

← 模型返回：
  Message{
    Role: "assistant",
    Content: "",                           // 没有文字！
    ToolCalls: [{
      Function: {Name: "read_file", Arguments: `{"path":"main.go"}`}
    }]
  }
  解读：模型说"我需要用 read_file 工具，参数是 main.go"

→ Agent 自动执行：readFileTool.InvokableRun(`{"path":"main.go"}`)
  返回: "package main\n\nfunc main() {\n\tfmt.Println(\"hello\")\n}\n"

→ 现在对话历史变成：
  UserMessage("读取 main.go")                        ← 用户说的
  AssistantMessage(ToolCalls: read_file...)          ← 模型说"我要调工具"
  ToolMessage("package main\nfunc main()...", read_file)  ← 工具执行结果

第2轮 ─────────────────────────────────
→ 发送给模型的消息（上面3条 + 新的 ToolMessage）

← 模型返回：
  Message{
    Role: "assistant",
    Content: "main.go 的内容是：\n```go\npackage main...\n```",
    ToolCalls: []                              // 没有工具调用！
  }
  解读：模型看到工具结果，决定不再调用工具，直接回答

→ 最终输出给用户："main.go 的内容是：..."
```

### 6.2 关键总结：三个角色在协作

| 角色 | 负责什么 |
|---|---|
| **模型（Model）** | 思考决策：该说话还是该用工具？用哪个工具？填什么参数？ |
| **工具（Tool）** | 执行操作：读文件、搜索、执行命令，返回结果 |
| **Agent** | 协调者：把模型和工具串起来，管理对话历史，控制循环次数 |

你作为开发者，只需要定义 Tool，配置 Agent。模型负责决策，Agent 负责执行循环。

---

## 七、Go 的类型安全优势：函数签名即文档

Eino 最大的优势之一是 Go 的**类型安全**。每个组件都有明确的输入输出类型，编译器帮你检查。

### 7.1 对比 Python 框架

在 LangChain (Python) 中，如果节点间的数据类型不匹配，只有运行时才能发现：

```python
# Python：错误要到运行才知道
chain = prompt | model | broken_parser  # 如果 parser 期望的输入和 model 输出不匹配？
result = chain.invoke("hello")           # Boom! 运行时崩溃
```

在 Eino 中，类型不匹配在编译时就报错：

```go
// Go：编译时就发现问题
graph := compose.NewGraph[string, int]()  // 输入 string，输出 int
graph.AddLambdaNode("node", func(ctx context.Context, in float64) (bool, error) {
    // ... 编译器告诉你：类型不匹配！
})
```

### 7.2 看懂函数签名

Eino 的 API 大量使用 Go 泛型。看一眼函数签名就知道输入输出是什么：

```go
// NewGraph[InputType, OutputType]  → 这个图接收 InputType，产出 OutputType
graph := compose.NewGraph[map[string]any, *schema.Message]()

// AddLambdaNode → 这个节点的函数签名是 func(ctx, Input) (Output, error)
graph.AddLambdaNode("process", func(ctx context.Context, input string) (int, error) {
    return len(input), nil
})
```

你几乎不需要查文档，看类型参数就知道怎么传数据。

---

## 八、流式输出：一个字一个字地显示

### 8.1 为什么需要流式

非流式：用户等着，模型全部生成完，一次性返回。等 10 秒什么都看不到。

流式：模型生成一个字，显示一个字，就像 ChatGPT 那样。

### 8.2 Eino 的流式处理

模型组件同时支持两种模式：

```go
// 非流式：阻塞等待完整结果
reply, err := model.Generate(ctx, messages)
// reply 是一个完整的 *Message

// 流式：返回一个"流"，可以逐个读取 token
stream, err := model.Stream(ctx, messages)
for {
    chunk, err := stream.Recv()
    if err == io.EOF {
        break
    }
    fmt.Print(chunk.Content)  // 一个字一个字地打印
}
```

使用 Agent 时，Runner.Query() 返回的迭代器天然支持流式——每个 Event 就是一个 chunk：

```go
iter := runner.Query(ctx, "解释并发编程")
for {
    event, ok := iter.Next()
    if !ok {
        break
    }
    fmt.Print(event.Message.Content)  // 逐字输出
}
```

### 8.3 Eino 的流式自动处理

当你把流式组件和非流式组件混用时，Eino **自动转换**：

| 场景 | Eino 自动做的事 |
|---|---|
| 流式节点 → 非流式节点 | 自动拼接（把流的所有 chunk 拼成一个完整值） |
| 非流式节点 → 流式节点 | 自动装箱（把单个值包成一个流） |
| 一个流 → 多个下游 | 自动复制流，每个下游各一份 |
| 多个流 → 一个下游 | 自动合并多个流 |

你不需要关心上下游是流式还是非流式。Eino 在编译时自动处理。

### 8.4 StreamReader 接口详解

`model.Stream()` 返回的 `*StreamReader` 不是普通的 channel，是一个封装好的迭代器：

```go
type StreamReader[T any] struct {
    // 内部字段，不直接访问
}

// 核心方法：接收下一个 chunk
func (sr *StreamReader[T]) Recv() (T, error)
//   - T: chunk 数据（这里是 *schema.Message，Content 只有一个/几个 token）
//   - error: io.EOF 表示流结束（正常结束，不是错误！）
//   - error: 其他错误表示流过程中出问题了
```

**完整的流式接收代码（含错误处理）：**

```go
stream, err := model.Stream(ctx, messages)
if err != nil {
    log.Fatalf("启动流式调用失败: %v", err)
}
defer stream.Close() // 记得关闭流

for {
    chunk, err := stream.Recv()
    if err == io.EOF {
        break // 流正常结束
    }
    if err != nil {
        fmt.Printf("\n流式接收出错: %v", err)
        break
    }
    fmt.Print(chunk.Content) // 逐个 token 打印
}
```

### 8.5 非流式 vs 流式：一张表说清楚

这是很多新手最困惑的地方。两种方式的根本区别在返回的**时间**和**方式**：

| | 非流式 `Generate()` | 流式 `Stream()` |
|---|---|---|
| **返回值** | `(*Message, error)` | `(*StreamReader, error)` |
| **获取方式** | 直接拿结果 | 循环 `Recv()` 逐个取 |
| **结束标志** | 函数返回即可 | `io.EOF` |
| **用户的感知** | 等 N 秒，突然出现全部文字 | 一个字一个字往外冒 |
| **内存** | 完整结果一次性载入 | 每次只保留一个 chunk |
| **适用场景** | 脚本、批量处理、后台任务 | 聊天界面、终端实时输出 |
| **实现复杂度** | 低，一次调用 | 稍高，需要管理流 |

**使用 Agent 时如何控制？** 你不需要直接调 `Generate()` 或 `Stream()`。Agent 内部自动处理。Runner 的事件迭代器天然支持流式：

```go
// Agent 方式：用 iter.Next() 就是流式的
iter := runner.Query(ctx, "解释并发编程")
for {
    event, ok := iter.Next()
    if !ok { break }
    fmt.Print(event.Message.Content) // 逐字输出
}
```

**同一段对话，两种写法对比：**

```go
// 非流式：自己调模型（无 Agent）
reply, err := model.Generate(ctx, messages)
fmt.Println(reply.Content) // 一次性打印完整回复

// 流式：自己调模型（无 Agent）
stream, err := model.Stream(ctx, messages)
for {
    chunk, err := stream.Recv()
    if err == io.EOF { break }
    fmt.Print(chunk.Content) // 逐字打印
}

// Agent 方式（自动流式）：你不需要关心 Generate 还是 Stream
iter := runner.Query(ctx, "帮我分析代码")
for {
    event, ok := iter.Next()
    if !ok { break }
    fmt.Print(event.Message.Content) // 逐字打印，Agent 内部自动处理
}
```

> **一句话总结**：自己调模型就用 `Generate()`（非流式）或 `Stream()`（流式）。用 Agent 就只关心 `iter.Next()`，流式是自动的。

---

## 九、两种构建方式：Agent 和 Graph 的区别

### 9.1 先搞清楚——这是两条不同的路

前五章我们一直用 **Agent + Runner** 的模式。但你可能会想："Graph 又是什么？是在 Runner 之后用的吗？"

**不是。Agent 和 Graph 是 Eino 提供的两种不同的构建方式，它们是平行的，选哪个取决于你的需求。**

用一个生活中的例子来理解：

**方式A：雇一个助理（Agent + Runner）**

你招了一个人，跟他说："帮我把这个项目分析一下"。他自己决定先去读代码、再搜索相关资料、最后写个报告。具体怎么做，他随机应变。

```
你：把项目分析一下
助理：好的（自己决定：先看代码→再搜索→再写报告）
你只需要等结果
```

**方式B：写一份操作手册（Graph）**

你写好步骤：第一步检查服务器、第二步备份数据库、第三步发邮件报告。每一步都写死了，执行的人必须按这个来，不能自己改顺序。

```
你：照这个手册做
执行者：第1步→第2步→第3步（严格按手册，不变通）
```

### 9.2 同样的问题，两种写法

看一个具体例子——"分析 main.go 有多少行代码"，对比两种方式怎么写：

**Agent 方式（模型自己决定怎么做）**：

```go
// 给模型一个读文件的工具，然后提问
model, _ := openai.NewChatModel(ctx, &openai.ChatModelConfig{
    Model: "gpt-4o-mini", APIKey: "...",
})

agent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name:        "analyzer",
    Instruction: "你是代码分析助手",
    Model:       model,
    ToolsConfig: adk.ToolsConfig{
        ToolsNodeConfig: compose.ToolsNodeConfig{
            Tools: []tool.BaseTool{readFileTool}, // 给一个读文件工具
        },
    },
})

runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: agent})
iter := runner.Query(ctx, "帮我分析 main.go 有多少行代码")

for {
    event, ok := iter.Next()
    if !ok { break }
    fmt.Print(event.Message.Content)
}
// 模型收到问题后自己决定：先调 read_file → 看内容 → 数行数 → 回答你
// 整个过程由模型做决策
```

**Graph 方式（你定义好固定流程）**：

```go
// 完全不用模型，只是两个普通 Go 函数串起来
graph := compose.NewGraph[string, string]()

// 节点1：读文件（一个普通 Go 函数，和大模型无关）
graph.AddLambdaNode("read_file", func(ctx context.Context, path string) (string, error) {
    data, _ := os.ReadFile(path)
    return string(data), nil
})

// 节点2：数行数（另一个普通 Go 函数，和大模型无关）
graph.AddLambdaNode("count_lines", func(ctx context.Context, code string) (string, error) {
    count := len(strings.Split(code, "\n"))
    return fmt.Sprintf("该文件共 %d 行代码", count), nil
})

// 固定路线：START → read_file → count_lines → END
graph.AddEdge(compose.START, "read_file")
graph.AddEdge("read_file", "count_lines")
graph.AddEdge("count_lines", compose.END)

// 编译，然后直接调用 Invoke
compiled, _ := graph.Compile(ctx)
result, _ := compiled.Invoke(ctx, "main.go")  // 传入文件路径
fmt.Println(result)  // "该文件共 42 行代码"
```

注意 Graph 方式的特点：
- **编译**：`graph.Compile(ctx)` 返回一个 `compiled` 对象
- **执行**：`compiled.Invoke(ctx, 输入)` 返回最终结果
- **没有 Runner**，没有事件流，没有对话历史
- 这个例子中甚至没有用大模型，就是两个纯函数的串联

### 9.3 核心区别对照表

| | Agent + Runner | Graph |
|---|---|---|
| **思路** | 雇一个能随机应变的助手 | 写一份死步骤的操作手册 |
| **谁决定步骤** | 模型自己判断 | 你事先在代码里写死 |
| **启动方式** | `runner.Query(问题)` | `compiled.Invoke(输入)` |
| **返回值** | 事件迭代器（逐个取出 Event） | 一次性返回最终结果 |
| **对话历史** | Runner 自动维护 | 没有对话历史（每次调用独立） |
| **流式输出** | 支持（事件流就是流式的） | 默认一次性返回 |
| **必须用模型吗** | 是 | 否，可以全是纯函数 |
| **典型场景** | "帮我查个 bug" | "每天凌晨3点备份数据库" |

### 9.4 用 Graph 但加入模型节点

当然，Graph 也可以加入模型节点——在固定流程的某个环节"让 AI 帮忙思考"：

```go
graph := compose.NewGraph[string, string]()

// 节点1：读文件
graph.AddLambdaNode("read_file", func(ctx context.Context, path string) (string, error) {
    data, _ := os.ReadFile(path)
    return string(data), nil
})

// 节点2：让模型评审代码 ← 这里加入模型
graph.AddChatModelNode("ai_review", model)

// 路线：START → read_file → ai_review → END
graph.AddEdge(compose.START, "read_file")
graph.AddEdge("read_file", "ai_review")
graph.AddEdge("ai_review", compose.END)

compiled, _ := graph.Compile(ctx)
result, _ := compiled.Invoke(ctx, "main.go")
fmt.Println(result.Content)
```

这个 Graph 的执行过程：
```
"main.go" 传入
  ↓
[read_file] 读文件 → 输出文件内容字符串 "package main..."
  ↓
[ai_review] 模型收到文件内容，分析后输出结果
  ↓
result = 模型的回复
```

数据会自动从上一个节点传到下一个节点，你不需要手动传。

### 9.5 加分支：根据条件走不同路线

做一个"代码审阅流水线"——模型看完代码后，如果需要修改就走修复流程，不需要就直接输出报告：

```go
graph := compose.NewGraph[string, string]()

// 4 个节点
graph.AddLambdaNode("read", func(ctx context.Context, path string) (string, error) {
    data, _ := os.ReadFile(path)
    return string(data), nil
})

graph.AddChatModelNode("review", model) // 模型分析代码

graph.AddLambdaNode("auto_fix", func(ctx context.Context, review string) (string, error) {
    return "已修复: " + review, nil
})

graph.AddLambdaNode("format", func(ctx context.Context, text string) (string, error) {
    return "=== 审阅结果 ===\n" + text, nil
})

// 固定路线部分
graph.AddEdge(compose.START, "read")
graph.AddEdge("read", "review")

// 分支：review 节点的输出决定下一步去哪
graph.AddBranch("review", compose.NewGraphBranch(
    func(ctx context.Context, msg *schema.Message) (string, error) {
        // 检查模型返回的内容是否包含"需要修改"
        if strings.Contains(msg.Content, "需要修改") {
            return "auto_fix", nil  // → 去修复节点
        }
        return "format", nil       // → 直接去输出节点
    },
    map[string]bool{"auto_fix": true, "format": true},
))

graph.AddEdge("auto_fix", "format")
graph.AddEdge("format", compose.END)

compiled, _ := graph.Compile(ctx)
result, _ := compiled.Invoke(ctx, "main.go")
fmt.Println(result)
```

数据流动图：
```
"main.go"
  ↓
[read]       读文件
  ↓
[review]     模型分析 → 返回 "代码规范，不需要修改"
  ↓
[分支判断]   包含"需要修改"吗？
  ├─ 是 → [auto_fix] → [format] → END
  └─ 否 ──────────────→ [format] → END
```

**分支函数的本质**：收到上一个节点的输出，你返回一个字符串告诉 Graph"接下来去哪个节点"。

### 9.6 Graph 核心 API 速查

前面用了很多 Graph 的 API，这里集中列出它们的函数签名，方便查阅。

**创建 Graph：**

```go
// NewGraph[I, O] 创建一个图，I 是初始输入类型，O 是最终输出类型
graph := compose.NewGraph[I, O]()
// 例：输入 string（文件路径），输出 string（分析结果）
graph := compose.NewGraph[string, string]()
```

**添加节点（两种方式）：**

```go
// 1. AddLambdaNode：添加一个普通函数作为节点
//    函数签名必须满足：func(ctx context.Context, Input) (Output, error)
//    输入输出类型要和 Graph 的泛型参数兼容
graph.AddLambdaNode(name string, fn interface{}) *GraphNode

// 例：
graph.AddLambdaNode("uppercase", func(ctx context.Context, s string) (string, error) {
    return strings.ToUpper(s), nil
})

// 2. AddChatModelNode：添加一个 ChatModel 作为节点
//    输入自动是 []*schema.Message，输出自动是 *schema.Message
graph.AddChatModelNode(name string, model ChatModel) *GraphNode

// 例：
graph.AddChatModelNode("review", model)
```

**连接节点：**

```go
// AddEdge：把两个节点连起来，数据从 from 流向 to
//   compose.START = 图的入口，compose.END = 图的出口
graph.AddEdge(from string, to string) error

// 例：
graph.AddEdge(compose.START, "read_file")   // START → read_file
graph.AddEdge("read_file", "count_lines")    // read_file → count_lines
graph.AddEdge("count_lines", compose.END)    // count_lines → END
```

**添加分支：**

```go
// AddBranch：在节点后设置分支逻辑
graph.AddBranch(name string, branch *GraphBranch) error

// NewGraphBranch：创建一个分支
//   condition: 分支条件函数，返回目标节点名
//   endNodes:  声明所有可能走到的节点名称
compose.NewGraphBranch(
    condition func(ctx context.Context, in T) (targetNodeName string, error),
    endNodes  map[string]bool,
) *GraphBranch

// 完整的 AddBranch 示例：
graph.AddBranch("review", compose.NewGraphBranch(
    func(ctx context.Context, msg *schema.Message) (string, error) {
        if strings.Contains(msg.Content, "需要修改") {
            return "auto_fix", nil
        }
        return "format", nil
    },
    map[string]bool{"auto_fix": true, "format": true},
))
// 意思是：review 节点执行完后，根据 condition 函数的返回值决定走向
```

**编译和执行：**

```go
// Compile：编译图，检查类型、环、连通性，返回 Runnable
compiled, err := graph.Compile(ctx context.Context) (*CompiledGraph[I, O], error)

// Invoke：执行编译后的图。传入初始输入，拿到最终输出。
//   和 runner.Query() 不同：没有对话历史、没有事件流、一次性返回
result, err := compiled.Invoke(ctx context.Context, input I) (O, error)

// Stream：流式执行图（如果图中有流式节点，可以逐个获取输出）
stream, err := compiled.Stream(ctx context.Context, input I) (*StreamReader[O], error)
```

**完整链路的函数签名演进——从输入到输出：**

```go
// 创建
graph := compose.NewGraph[string, string]()

// 添加节点函数 func(ctx, string) (string, error)
graph.AddLambdaNode("step1", func(ctx context.Context, s string) (string, error) { ... })

// 编译
compiled, _ := graph.Compile(ctx) // *CompiledGraph[string, string]

// 执行 func(ctx, string) (string, error)
result, _ := compiled.Invoke(ctx, "hello") // result: string
```

> **核心区别**：`compiled.Invoke()` 入参类型 = `NewGraph` 的第一个类型参数；出参类型 = `NewGraph` 的第二个类型参数。泛型让输入输出类型在编译时确定。

**Graph 各 API 速查表：**

| API | 作用 | 返回值 |
|---|---|---|
| `NewGraph[I, O]()` | 创建一张新图 | `*Graph[I, O]` |
| `AddLambdaNode(name, fn)` | 添加函数节点 | `*GraphNode` |
| `AddChatModelNode(name, model)` | 添加模型节点 | `*GraphNode` |
| `AddBranch(name, branch)` | 在节点后加分支 | `error` |
| `AddEdge(from, to)` | 连接两个节点 | `error` |
| `Compile(ctx)` | 编译图 | `(*CompiledGraph[I, O], error)` |
| `compiled.Invoke(ctx, input)` | 同步执行 | `(O, error)` |
| `compiled.Stream(ctx, input)` | 流式执行 | `(*StreamReader[O], error)` |



---

## 十、Agent 和 Graph 组合使用

### 10.1 场景：AI 助手需要执行一个不能出错的流程

回到迷你 Claude Code。你的 AI 助手很灵活，用户说"帮我提交代码"，它就自己决定干什么。

但问题是："提交代码"这个操作很危险，不能让模型自由决定步骤。你必须确保**先测试→再检查规范→最后提交**，一步都不能少，一步都不能跳过。

解决方案：把"安全提交"写成 Graph，然后包装成一个 Tool，交给 Agent。

### 10.2 第一步：写出"安全提交"的 Graph

```go
commitGraph := compose.NewGraph[string, string]()

commitGraph.AddLambdaNode("run_tests", func(ctx context.Context, dir string) (string, error) {
    cmd := exec.Command("go", "test", "./...")
    cmd.Dir = dir
    output, err := cmd.CombinedOutput()
    if err != nil {
        return "", fmt.Errorf("测试失败，终止提交:\n%s", output)
    }
    return "测试通过 ✓", nil
})

commitGraph.AddLambdaNode("run_lint", func(ctx context.Context, dir string) (string, error) {
    cmd := exec.Command("golangci-lint", "run")
    cmd.Dir = dir
    output, err := cmd.CombinedOutput()
    if err != nil {
        return "", fmt.Errorf("规范检查失败，终止提交:\n%s", output)
    }
    return "规范检查通过 ✓", nil
})

commitGraph.AddLambdaNode("do_commit", func(ctx context.Context, dir string) (string, error) {
    cmd := exec.Command("git", "add", ".")
    cmd.Dir = dir
    cmd.Run()
    cmd = exec.Command("git", "commit", "-m", "自动提交")
    cmd.Dir = dir
    output, _ := cmd.CombinedOutput()
    return "提交成功 ✓\n" + string(output), nil
})

// 死顺序，不可跳过
commitGraph.AddEdge(compose.START, "run_tests")
commitGraph.AddEdge("run_tests", "run_lint")
commitGraph.AddEdge("run_lint", "do_commit")
commitGraph.AddEdge("do_commit", compose.END)

compiledCommit, _ := commitGraph.Compile(ctx)
```

### 10.3 第二步：把 Graph 包装成 Tool，加入 Agent

```go
// 把一个编译好的 Graph 变成一个 Tool
commitTool := graphtool.NewInvokableGraphTool(
    "safe_commit",                                                 // 工具名
    "安全提交代码：依次运行测试、检查规范、git提交（不可跳过任何步骤）",  // 描述
    compiledCommit,                                                // 编译好的 Graph
)

// 把 commitTool 像普通 Tool 一样放进 Agent
agent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Model: model,
    ToolsConfig: adk.ToolsConfig{
        ToolsNodeConfig: compose.ToolsNodeConfig{
            Tools: []tool.BaseTool{
                readFileTool,
                searchTool,
                shellTool,
                commitTool,  // GraphTool 和普通 Tool 一样用！
            },
        },
    },
})
```

### 10.4 运行时发生了什么

```
用户说："帮我提交代码"

Agent（内部 ReAct 循环）：
  模型思考 → "用户要提交代码，我需要用 safe_commit 工具"
  → Agent 调用 commitTool
    → commitTool 内部严格按 Graph 执行：
      测试 → 通过 → 检查规范 → 通过 → git commit → 成功
    → 返回 "提交成功 ✓"
  → Agent 把结果发给模型
  → 模型回答："代码已安全提交，所有测试和规范检查都已通过"
```

**这个设计的好处**：Agent 保持了灵活性（模型决定什么时候该提交），但"提交"这个动作本身是不可跳过的死流程（Graph 保证）。

---

## 十一、多 Agent 协作：一个人不够，组个团队

### 11.1 Runner 只有一个 Agent，但 Agent 可以是个"团队"

前面我们一直是一个 Agent 干所有事。但当你写一个真正的 CLI 助手时，会发现有些任务需要**分工协作**——

比如用户说"帮我查一下 Eino 框架里 Interrupt 的用法，然后写个示例"：

- 需要有人去**搜索代码**（找到 Interrupt 相关源码）
- 需要有人去**读文档**（理解用法）
- 需要有人去**写代码**（生成示例）

一个人干这三件事就乱了。最好有个分工：**搜索专家、文档专家、编码专家**，各司其职。

Eino 的做法：**Runner 只管一个 Agent，但这个 Agent 内部可以管理多个子 Agent。**

```
Runner
  └─ 主 Agent（DeepAgent 或 Supervisor）
       ├─ 子 Agent: 搜索专家
       ├─ 子 Agent: 文档专家
       └─ 子 Agent: 编码专家
```

Eino 提供了三种多 Agent 协作模式，选哪个取决于你的场景。

### 11.2 方式一：DeepAgent —— 主 Agent 调子 Agent 干活

**适合**：你有一个主 Agent 做决策，某些具体任务委派给专家 Agent 去做，做完结果返回给主 Agent。

**打个比方**：你（主 Agent）让同事帮你搜资料，同事搜完把结果交给你，你根据结果决定怎么回答。

```go
import "github.com/cloudwego/eino/adk/prebuilt/deep"

// 1. 创建子 Agent：搜索专家
searchAgent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name:        "SearchAgent",
    Description: "搜索代码和文档的专家",  // ← 主 Agent 根据这个描述决定什么时候用它
    Instruction: "你是代码搜索专家，用 search_code 和 read_file 工具找到相关内容",
    Model:       model,
    ToolsConfig: adk.ToolsConfig{
        ToolsNodeConfig: compose.ToolsNodeConfig{
            Tools: []tool.BaseTool{searchCodeTool, readFileTool},
        },
    },
})

// 2. 创建子 Agent：编码专家
codeAgent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name:        "CodeAgent",
    Description: "编写和修改代码的专家",
    Instruction: "你是Go编程专家，根据需求编写代码",
    Model:       model,
})

// 3. 创建 DeepAgent（主 Agent）——把子 Agent 放进去
mainAgent, _ := deep.New(ctx, &deep.Config{
    Name:        "MainAgent",
    Description: "编程助手主控",
    ChatModel:   model,
    SubAgents:   []adk.Agent{searchAgent, codeAgent}, // ← 子 Agent 列表
    Instruction: `你是编程助手主控。工作方式：
1. 收到用户需求后，先分析需要哪些专家
2. 把具体任务委派给合适的专家去执行
3. 汇总专家的结果，给出最终回答`,
})

// 4. 运行——和普通 Agent 完全一样！
runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: mainAgent})
iter := runner.Query(ctx, "查一下项目中 Interrupt 的用法，写个示例")

for {
    event, ok := iter.Next()
    if !ok { break }
    fmt.Print(event.Message.Content)
}
```

**运行时发生了什么？** 主 Agent 内部有一个叫 `task` 的工具，当模型判断需要专家帮忙时，会自动调用：

```
用户: "查一下 Interrupt 的用法并写示例"
  ↓
主 Agent（模型思考）: "这事需要两步：先搜索，再写代码"
  第1步: 调用 task 工具 {"subagent_type":"SearchAgent", "description":"搜索 Interrupt 用法"}
    → SearchAgent 启动，搜索代码，返回结果给主 Agent
  第2步: 调用 task 工具 {"subagent_type":"CodeAgent", "description":"根据搜索结果写示例"}
    → CodeAgent 启动，写代码，返回结果给主 Agent
  第3步: 主 Agent 汇总结果，输出给用户
```

**关键特性**：
- **上下文隔离**：子 Agent 只收到委派的任务描述，不会看到整个对话历史（保持专注）
- **自动判断**：模型自己决定什么时候用哪个专家，你不需要写 if-else
- **Session 共享**：主 Agent 的会话状态会自动传递给子 Agent

### 11.3 方式二：AgentTool —— 把 Agent 当 Tool 用

**和 DeepAgent 的区别**：DeepAgent 是框架帮你管子 Agent。AgentTool 是你手动把一个 Agent 包装成 Tool，然后放进另一个 Agent 的工具列表。

**适合**：你已经有了一些 Agent，想以更细粒度的方式控制它们。

```go
// 1. 创建子 Agent
codeAgent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name: "CodeAgent",
    // ...
})

// 2. 把 Agent 包装成 Tool  ← 核心：Agent → Tool
codeTool, _ := adk.AgentAsTool(ctx, codeAgent,
    "call_code_expert",       // Tool 名称
    "让编码专家写代码",         // Tool 描述
)

// 3. 放进另一个 Agent 的工具列表，和普通 Tool 一样用
mainAgent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name:  "MainAgent",
    Model: model,
    ToolsConfig: adk.ToolsConfig{
        ToolsNodeConfig: compose.ToolsNodeConfig{
            Tools: []tool.BaseTool{
                readFileTool,
                searchTool,
                codeTool,  // ← Agent 包装的 Tool，和普通 Tool 混用
            },
        },
    },
})

runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: mainAgent})
// 运行时模型会像调普通工具一样调用 call_code_expert
```

### 11.4 方式三：Supervisor —— 监工模式，自动来回调度

**和 DeepAgent 的区别**：DeepAgent 是"主 Agent 调子 Agent，拿到结果自己用"。Supervisor 是"监工一轮一轮地指挥，子 Agent 做完自动回报给监工，监工再决定下一步"。

**适合**：复杂的多步骤任务，需要反复调度多个 Agent。

```go
import "github.com/cloudwego/eino/adk/prebuilt/supervisor"

// 1. 创建子 Agent
researcher, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name:        "Researcher",
    Description: "搜索和整理资料",
    Instruction: "你是研究员，负责搜索相关信息并整理成文档",
    Model:       model,
    ToolsConfig: /* 搜索工具 */,
})

writer, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name:        "Writer",
    Description: "撰写报告",
    Instruction: "你是写手，根据研究资料撰写正式报告",
    Model:       model,
})

// 2. 创建 Supervisor
supervisor, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    Name:  "Supervisor",
    Model: model,
    Instruction: `你是项目监工。工作方式：
- 收到主题后，先转交给 Researcher 搜索资料
- Researcher 完成后，转交给 Writer 撰写报告
- Writer 完成后，输出最终报告
- 不要自己干活，始终委派给子 Agent`,
})

// 3. 组装
supervisorAgent, _ := supervisor.New(ctx, &supervisor.Config{
    Supervisor: supervisor,
    SubAgents:  []adk.Agent{researcher, writer},
})

// 4. 运行
runner := adk.NewRunner(ctx, adk.RunnerConfig{Agent: supervisorAgent})
iter := runner.Query(ctx, "写一份关于 Go 语言并发模型的报告")
```

**Supervisor 的核心机制——Transfer（转交）**：

```
Runner 启动 Supervisor
  ↓
Supervisor 分析任务 → 决定调 Researcher
  → [Transfer 事件] 转交给 Researcher
  ↓
Researcher 搜索完成 → [Transfer 事件] 自动回报 Supervisor
  ↓
Supervisor 看到结果 → 决定调 Writer
  → [Transfer 事件] 转交给 Writer
  ↓
Writer 写完 → [Transfer 事件] 自动回报 Supervisor
  ↓
Supervisor 输出最终报告
```

**关键**：子 Agent 完成后会**自动 Transfer 回 Supervisor**（框架帮你做了），Supervisor 看到回报后决定下一步。这个"自动回报"机制让 Supervisor 能持续调度。

### 11.5 三种方式对比

| | DeepAgent | AgentTool | Supervisor |
|---|---|---|---|
| **比喻** | 经理安排下属干活，下属汇报结果 | 工具箱里有个"机器人助手"，按需取用 | 监工来回指挥，工人做完自动回报 |
| **子Agent返回** | 结果返回主Agent，主Agent继续 | 结果返回调用方 | 自动Transfer回报给Supervisor |
| **适合场景** | 委派具体任务，主Agent汇总结果 | 自定义控制粒度 | 多步骤多轮调度 |
| **复杂度** | 低，开箱即用 | 中，手动管理 | 中，需设计调度流程 |
| **谁做决策** | 模型自己判断何时调子Agent | 模型判断何时调工具 | Supervisor指令里写好的流程 + 模型判断 |

### 11.6 迷你 Claude Code 用哪种？

对于 CLI 编程助手，推荐 **DeepAgent**：

```go
// 迷你CC的专家团队
searchAgent  // 搜索代码、读文件
codeAgent    // 写代码、改代码
shellAgent   // 执行命令、运行测试

mainAgent := deep.New(ctx, &deep.Config{
    ChatModel: model,
    SubAgents: []adk.Agent{searchAgent, codeAgent, shellAgent},
})
```

模型会自动判断什么时候该搜索、什么时候该写代码、什么时候该执行命令。

### 11.7 更多预置模式

除了上面三种，Eino 还内置了这些模式，全部可以直接用：

| 模式 | 做什么 | 一句话 |
|---|---|---|
| **SequentialAgent** | 顺序执行 | A做完→B拿到A的结果继续做→C拿到B的结果继续做 |
| **ParallelAgent** | 并行执行 | A、B、C 同时干活，互不等待 |
| **LoopAgent** | 循环打磨 | A 写完 → B 审阅 → 不通过就回去改 → 通过才输出 |

用法都一样——创建、放进 Runner、Query。你只需要选哪个模式适合你的场景。

---

## 十二、Callback：给一切装上监控

### 12.1 Callback 能用在两个地方

Callback 可以注入到**所有 Runnable**——不管是 Agent 还是 Graph。

它的作用：在执行过程中插入你自己的逻辑，比如打印日志、记录耗时、发告警。

### 12.2 在 Agent 上用 Callback

```go
// 创建一个日志 Callback
handler := compose.NewHandlerBuilder().
    OnStartFn(func(ctx context.Context, info *compose.RunInfo, input compose.CallbackInput) context.Context {
        fmt.Printf("[%s] 开始\n", info.Name)
        return ctx
    }).
    OnEndFn(func(ctx context.Context, info *compose.RunInfo, output compose.CallbackOutput) context.Context {
        fmt.Printf("[%s] 完成\n", info.Name)
        return ctx
    }).
    Build()

// 方式1：注册为全局，所有 Agent 和 Graph 都生效
callbacks.AppendGlobalHandlers(handler)

// 方式2：在单次 Query 时带上
iter := runner.Query(ctx, "帮我查个bug", compose.WithCallbacks(handler))
```

运行时会看到 Agent 内部的每一步：

```text
[ChatModel] 开始          ← 模型开始思考
[ChatModel] 完成          ← 模型决定调 read_file
[Tool: read_file] 开始    ← 执行读文件
[Tool: read_file] 完成    ← 读完了
[ChatModel] 开始          ← 模型看到文件，继续思考
[ChatModel] 完成          ← 模型给出最终回答
```

### 12.3 在 Graph 上用 Callback

```go
// 同样的 handler，用在 Graph 上
result, _ := compiled.Invoke(ctx, "main.go", compose.WithCallbacks(handler))

// 运行时输出：
// [read_file] 开始
// [read_file] 完成
// [count_lines] 开始
// [count_lines] 完成
```

### 12.4 Callback 的三种精度

```go
// 精度1：全局，所有节点都触发
callbacks.AppendGlobalHandlers(handler)

// 精度2：只对模型节点生效
compiled.Invoke(ctx, input, compose.WithChatModelOption(model.WithTemperature(0.5)))

// 精度3：只对名字叫 "read_file" 的节点生效
compiled.Invoke(ctx, input, compose.WithCallbacks(handler).DesignateNode("read_file"))
```

### 12.5 生产级：集成 Langfuse 做链路追踪

自己写 Callback 只能打 log。要追踪 Token、延迟、费用，用 Eino 集成的 Langfuse：

```go
import "github.com/cloudwego/eino-ext/callbacks/langfuse"

cbh, flusher := langfuse.NewLangfuseHandler(&langfuse.Config{
    Host:      "https://cloud.langfuse.com",
    PublicKey: "pk-xxx",
    SecretKey: "sk-xxx",
})

callbacks.AppendGlobalHandlers(cbh) // 注册为全局

// 正常运行你的 Agent 或 Graph
// 所有调用自动上报到 Langfuse 面板
runner.Query(ctx, "帮我分析代码")

flusher() // 程序退出前确保数据都上传了
```

---

## 十三、进阶特性速览

前面十一章已经覆盖了构建 CLI 助手的全部核心知识。以下特性用到时再回来查即可：

### 13.1 Interrupt/Resume：中途暂停等用户确认

**场景**：Agent 要执行删除文件的操作，暂停等你点"确认"再继续。

```go
// 在 Tool 里触发中断
func (t *DeleteTool) InvokableRun(ctx context.Context, args string) (string, error) {
    return "", compose.Interrupt(ctx, "确认删除文件："+args, "confirm_delete")
}

// 第一次运行，走到这里会暂停
id := uuid.New().String()
iter := runner.Query(ctx, "删除临时文件", compose.WithCheckPointID(id))
// → 返回中断信息，程序暂停

// 用户确认后，用同一个 ID 恢复
iter = runner.Query(ctx, "确认",
    compose.WithCheckPointID(id),
    compose.WithStateModifier(func(ctx context.Context, path compose.NodePath, state any) error {
        state.(*myState).Confirmed = true
        return nil
    }),
)
// → 从断点继续执行
```

### 13.2 Middleware：比 Callback 更强的拦截能力

Callback 只能**观察**（看发生了什么）。Middleware 可以**干预**（修改消息、改写返回值）。

内置的 Middleware 开箱即用：

```go
agent, _ := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
    // ... 常规配置
    Middlewares: []adk.ChatModelAgentMiddleware{
        summarization.NewMiddleware(nil), // 对话太长时自动摘要压缩
    },
})
```

| 内置 Middleware | 作用 |
|---|---|
| `Summarization` | 对话历史太长时自动压缩 |
| `ToolReduction` | 工具返回的结果太长时自动截断 |
| `Filesystem` | 提供文件读写工具集 |
| `Skill` | 动态加载技能模块 |

### 13.3 其他特性

| 特性 | 一句话 |
|---|---|
| **Memory/Session** | Runner 默认就有，自动记住对话历史 |
| **DeepAgent** | 一个主 Agent 调度多个子 Agent（搜索专家、编码专家…） |
| **Workflow** | Graph 的增强版，支持字段级别精细映射（一般用不到） |
| **AgentTool** | 把一个 Agent 变成另一个 Agent 的工具 |

---

## 十四、总结

### 14.1 一张图记住 Eino 的所有用法

```text
             你的需求是什么？
              /            \             \
             /              \             \
    开放式对话               固定流程        复杂任务
    "帮我查bug"             "每天备份"      "搜代码→写报告"
         |                       |              |
         ▼                       ▼              ▼
   Agent + Runner              Graph        DeepAgent
         |                       |         /    |    \
    runner.Query()         compiled.Invoke()  /     |     \
         |                       |           ▼      ▼      ▼
    返回事件流                返回最终结果  搜索专家  编码专家  审查专家
    (逐字流式)               (一次性)        \      |      /
         |                       |            \     |     /
         └───────┬───────────────┘              ▼    ▼    ▼
                 |                         Runner.Query()
         可以组合：Graph → Tool → Agent    → 返回事件流
         DeepAgent/AgentTool/Supervisor   (和单Agent用法一样)
```

### 14.2 你的迷你 Claude Code 完整架构

```
┌─────────────────────────────────────────┐
│          CLI 交互循环                     │
│  scanner.Scan() → runner.Query()        │
│  → 打印 event.Message.Content           │
└────────────────┬────────────────────────┘
                 │
      ┌──────────▼──────────┐
      │       Runner        │  管理对话生命周期、保存历史
      └──────────┬──────────┘
                 │
      ┌──────────▼──────────┐
      │   DeepAgent (主控)  │  多Agent协作，自动调度专家
      │                     │
      │  模型：gpt-4o       │  ← 决策：说话、调工具、还是委派专家？
      │                     │
      │  工具 & 专家：       │
      │  ├ read_file (Tool) │  ← 读文件
      │  ├ search_code (Tool)│ ← 搜索代码
      │  ├ run_command (Tool)│ ← 执行命令
      │  ├ safe_commit (GraphTool)│ ← Graph包装的工具
      │  ├ SearchAgent (子Agent)│ ← 搜索专家
      │  ├ CodeAgent (子Agent) │ ← 编码专家
      │  └ ShellAgent (子Agent)│ ← 命令执行专家
      │                     │
      │  Callback:          │  ← 监控：日志、Token统计
      │  └ Langfuse         │
      └─────────────────────┘
```

### 14.3 一次工具调用的完整过程（最重要的一张图）

```
用户输入："帮我查看 main.go"
  │
  ▼
runner.Query() ──→ Agent 启动 ReAct 循环
  │
  ▼
┌─ 第1轮 ──────────────────────────────────────┐
│                                               │
│ → 发给模型的消息：                              │
│   SystemMsg("你是编程助手")                     │
│   UserMsg("帮我查看 main.go")                  │
│                                               │
│ ← 模型返回 Message{                            │
│     Content: "",   // 空的！不说话              │
│     ToolCalls: [{Name:"read_file", Args:"main.go"}]│
│   }                                           │
│   意思：模型不回答，它要调用工具                   │
│                                               │
│ → Agent 执行 read_file("main.go")              │
│   返回结果："package main\nfunc main() {...}"   │
│                                               │
│ → 消息历史现在是 3 条：                          │
│   ① UserMsg("帮我查看main.go")                 │
│   ② AssistantMsg(ToolCall: read_file)         │
│   ③ ToolMsg("package main...", read_file)     │
└───────────────────────────────────────────────┘
  │
  ▼
┌─ 第2轮 ──────────────────────────────────────┐
│                                               │
│ → 发给模型的消息：上面 3 条                      │
│                                               │
│ ← 模型返回 Message{                            │
│     Content: "main.go 的内容是...",             │
│     ToolCalls: []  // 空的！不再需要工具了        │
│   }                                           │
│   意思：模型看到工具结果，决定直接回答              │
│                                               │
│ → Agent 发现 ToolCalls 为空，退出循环            │
└───────────────────────────────────────────────┘
  │
  ▼
Runner 把模型回复包装成 Event，通过迭代器返回
  │
  ▼
你的代码：fmt.Print(event.Message.Content)
  │
  ▼
终端显示："main.go 的内容是：package main..."
```

### 14.4 四个核心原则

1. **Agent 就是"模型+工具+循环"的打包**。你给工具，Agent 跑循环，Runner 管理对话。
2. **Graph 就是"固定步骤+固定顺序"的图纸**。没有自由发挥，一步接一步，执行完返回结果。
3. **多 Agent 就是"给主 Agent 配团队"**。DeepAgent 开箱即用，AgentTool 手动控制，Supervisor 监工调度。Runner 只管一个 Agent，但那个 Agent 内部可以是一个团队。
4. **Graph、Agent、多 Agent 不是先后关系，是不同场景的选择**。简单任务用 Agent，固定流程用 Graph，复杂任务用 DeepAgent。它们可以组合：Graph 变 Tool、Agent 变 Tool。最终都通过 Runner.Query() 运行。

---

> **参考资料**
> - Eino 主仓库：https://github.com/cloudwego/eino
> - 组件扩展库：https://github.com/cloudwego/eino-ext
> - 官方快速入门：https://www.cloudwego.io/zh/docs/eino/quick_start/
> - 示例项目（含10章渐进教程）：https://github.com/cloudwego/eino-examples
