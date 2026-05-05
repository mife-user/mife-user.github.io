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

到这里你已经能和大模型对话了。但这就是全部吗？显然不是——真正的编程助手需要**读取文件、搜索代码、执行命令**。这就要用到 Tool。

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

---

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

---

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

## 十一、Callback：给一切装上监控

### 11.1 Callback 能用在两个地方

Callback 可以注入到**所有 Runnable**——不管是 Agent 还是 Graph。

它的作用：在执行过程中插入你自己的逻辑，比如打印日志、记录耗时、发告警。

### 11.2 在 Agent 上用 Callback

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

### 11.3 在 Graph 上用 Callback

```go
// 同样的 handler，用在 Graph 上
result, _ := compiled.Invoke(ctx, "main.go", compose.WithCallbacks(handler))

// 运行时输出：
// [read_file] 开始
// [read_file] 完成
// [count_lines] 开始
// [count_lines] 完成
```

### 11.4 Callback 的三种精度

```go
// 精度1：全局，所有节点都触发
callbacks.AppendGlobalHandlers(handler)

// 精度2：只对模型节点生效
compiled.Invoke(ctx, input, compose.WithChatModelOption(model.WithTemperature(0.5)))

// 精度3：只对名字叫 "read_file" 的节点生效
compiled.Invoke(ctx, input, compose.WithCallbacks(handler).DesignateNode("read_file"))
```

### 11.5 生产级：集成 Langfuse 做链路追踪

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

## 十二、进阶特性速览

前面十一章已经覆盖了构建 CLI 助手的全部核心知识。以下特性用到时再回来查即可：

### 12.1 Interrupt/Resume：中途暂停等用户确认

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

### 12.2 Middleware：比 Callback 更强的拦截能力

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

### 12.3 其他特性

| 特性 | 一句话 |
|---|---|
| **Memory/Session** | Runner 默认就有，自动记住对话历史 |
| **DeepAgent** | 一个主 Agent 调度多个子 Agent（搜索专家、编码专家…） |
| **Workflow** | Graph 的增强版，支持字段级别精细映射（一般用不到） |
| **AgentTool** | 把一个 Agent 变成另一个 Agent 的工具 |

---

## 十三、总结

### 13.1 一张图记住 Eino 的两种用法

```text
             你的需求是什么？
              /            \
             /              \
    开放式对话               固定流程
    "帮我查bug"             "每天备份+发报告"
         |                       |
         ▼                       ▼
   Agent + Runner              Graph
         |                       |
    runner.Query()         compiled.Invoke()
         |                       |
    返回事件流                返回最终结果
    (逐字流式)               (一次性)
         |                       |
         └───────┬───────────────┘
                 |
         可以组合：Graph → Tool → Agent
         (把固定流程包装成工具交给 Agent)
```

### 13.2 你的迷你 Claude Code 完整架构

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
      │   ChatModelAgent    │  内置 ReAct 循环
      │                     │
      │  模型：gpt-4o       │  ← 决策：说话 or 调工具？
      │                     │
      │  工具：             │  ← 执行：真的干活
      │  ├ read_file        │
      │  ├ search_code      │
      │  ├ run_command      │
      │  └ safe_commit (GraphTool) │ ← Graph 包装的工具
      │                     │
      │  Callback:          │  ← 监控：日志、Token统计
      │  └ Langfuse         │
      └─────────────────────┘
```

### 13.3 一次工具调用的完整过程（最重要的一张图）

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

### 13.4 三个核心原则

1. **Agent 就是"模型+工具+循环"的打包**。你给工具，Agent 跑循环，Runner 管理对话。
2. **Graph 就是"固定步骤+固定顺序"的图纸**。没有自由发挥，一步接一步，执行完返回结果。
3. **Graph 和 Agent 不是先后关系，是平行关系**。选哪个取决于你的场景。可以组合：把 Graph 变成 Tool 给 Agent 用。

---

> **参考资料**
> - Eino 主仓库：https://github.com/cloudwego/eino
> - 组件扩展库：https://github.com/cloudwego/eino-ext
> - 官方快速入门：https://www.cloudwego.io/zh/docs/eino/quick_start/
> - 示例项目（含10章渐进教程）：https://github.com/cloudwego/eino-examples
