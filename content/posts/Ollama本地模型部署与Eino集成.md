---
title: 'Ollama 实战：本地模型部署、Go 调用与 Eino 框架集成'
date: 2026-05-20T11:00:00+08:00
draft: false
tags: ["Ollama", "Go", "Eino", "LLM", "Docker", "本地模型"]
---

## 前言：为什么需要本地模型？

使用 OpenAI / DeepSeek 的云端 API 很方便，但有些场景你不得不考虑本地部署：

- **数据安全**：处理敏感代码或内部文档时，数据不能离开公司网络
- **离线环境**：开发机没有外网，或者想在飞机/高铁上写代码
- **成本控制**：频繁调用 API 的账单让你怀疑人生
- **隐私保护**：不想让自己的代码被第三方模型提供商记录

Ollama 就是为解决这些问题而生的——它让你在本地一键运行 Llama、Qwen、DeepSeek 等开源模型，而且提供了和 OpenAI 兼容的 API。

**本文会从安装开始，逐步覆盖 Docker 部署、Go SDK 调用，最后演示如何用 Eino 框架对接 Ollama，让你用本地模型构建 AI 应用。**

---

## 一、Ollama 是什么？

一句话：**Ollama 是本地大模型的 Docker。**

就像 Docker 让你用 `docker run nginx` 一行命令跑起 Web 服务器，Ollama 让你用 `ollama run qwen3` 一行命令跑起大模型。

它帮你处理了：
- 模型下载与管理（自动下载、版本管理、存储优化）
- GPU 加速（自动检测 CUDA / ROCm / Metal）
- API 服务（启动后自带 HTTP API，兼容 OpenAI 格式）
- 量化支持（自动选择适合你硬件的量化版本）

### 1.1 支持的主流模型

| 模型 | 特点 | 适用场景 |
|---|---|---|
| `llama3.3` | Meta 最新开源模型，综合能力强 | 通用对话、文本生成 |
| `qwen3` | 阿里出品，中文能力优秀 | 中文对话、文档处理 |
| `deepseek-r1` | 推理特化，带思考链 | 复杂推理、代码分析 |
| `codellama` | 代码生成专用 | 代码补全、代码审查 |
| `mistral` | 轻量高效 | 资源受限环境 |
| `phi4` | 微软出品，体积小 | 本地轻量级推理 |
| `gemma3` | Google 开源 | 多语言、多模态 |

---

## 二、安装 Ollama 并运行第一个模型

### 2.1 安装

**Linux / WSL：**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS：**

```bash
brew install ollama
```

**Windows：**

直接下载安装包：`https://ollama.com/download/windows`

也可以一行命令安装：

```powershell
winget install Ollama.Ollama
```

**Docker：**

```bash
docker pull ollama/ollama
```

### 2.2 启动服务

安装完成后，Ollama 默认以后台服务运行。检查状态：

```bash
# 查看服务状态
systemctl status ollama   # Linux
brew services info ollama # macOS

# 或者直接测试
curl http://localhost:11434/api/tags
```

默认端口是 `11434`，这个值后面会频繁用到。

### 2.3 跑你的第一个模型

```bash
# 下载并运行 qwen3（阿里通义千问3，中文能力很好）
ollama run qwen3:8b

# 或者更轻量的版本
ollama run qwen3:4b
```

第一次运行会自动下载模型（几 GB），之后就直接启动了。你会看到一个交互式对话界面：

```
>>> 用Go写一个斐波那契函数

好的，这是一个Go语言实现的斐波那契函数：

package main

import "fmt"

func fibonacci(n int) []int {
    if n <= 0 {
        return []int{}
    }
    ...
```

输入 `/bye` 退出。

### 2.4 管理模型

```bash
# 列出已下载的模型
ollama list

# 输出示例：
# NAME            ID              SIZE      MODIFIED
# qwen3:8b        a1b2c3d4e5f6    4.9 GB    2 hours ago
# llama3.3:latest  x1y2z3a4b5c6    4.7 GB    3 days ago

# 查看模型详情
ollama show qwen3:8b

# 删除模型
ollama rm qwen3:8b

# 查看运行日志
journalctl -u ollama -f   # Linux
```

---

## 三、Ollama HTTP API：用 curl 先试一下

在写 Go 代码之前，先用 curl 熟悉 Ollama 的 API——它和 OpenAI 的接口几乎一样。

### 3.1 非流式对话（一次性返回）

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:8b",
  "stream": false,
  "messages": [
    {"role": "system", "content": "你是一个Go语言助手，用中文回答"},
    {"role": "user", "content": "什么是 defer？"}
  ]
}'
```

返回：

```json
{
  "model": "qwen3:8b",
  "created_at": "2026-05-20T10:00:00Z",
  "message": {
    "role": "assistant",
    "content": "defer 是 Go 语言中的一个关键字，用于延迟执行一个函数调用..."
  },
  "done": true
}
```

### 3.2 流式对话（逐字返回）

把 `"stream": true`（默认就是 true），每个 chunk 会单独返回：

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:8b",
  "messages": [
    {"role": "user", "content": "你好，用一句话介绍自己"}
  ]
}'
```

你会看到响应一行一行地流式输出（Server-Sent Events 格式），每行一个 JSON：

```
{"message":{"role":"assistant","content":"我"}}
{"message":{"role":"assistant","content":"是"}}
{"message":{"role":"assistant","content":"通"}}
...
```

### 3.3 Embedding 接口

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "nomic-embed-text",
  "input": "Go语言是Google开发的静态强类型语言"
}'
```

Ollama 也支持生成向量（用于 RAG / 语义搜索），但要先拉一个 embedding 专用模型：

```bash
ollama pull nomic-embed-text
```

---

## 四、Docker 部署 Ollama

如果你的开发环境本身就是容器化的，或者想在服务器上干净地部署，用 Docker 是最佳选择。

### 4.1 基础部署

```bash
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama/ollama
```

`-v ollama_data:/root/.ollama` 把模型文件挂到 Docker Volume，这样容器重建后模型还在，不用重新下载。

### 4.2 挂载 GPU（强烈推荐）

纯 CPU 跑模型很慢，用 `--gpus` 把 GPU 透传给容器：

```bash
# NVIDIA GPU
docker run -d \
  --name ollama \
  --gpus all \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama/ollama

# 只指定一张卡
docker run -d \
  --name ollama \
  --gpus '"device=0"' \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama/ollama
```

macOS 上不需要 `--gpus`，Ollama 会自动使用 Metal。

### 4.3 进入容器拉模型

容器跑起来后，用 `exec` 进去拉模型：

```bash
# 进入容器
docker exec -it ollama bash

# 拉几个模型
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

也可以一行搞定：

```bash
docker exec -it ollama ollama pull qwen3:8b
```

### 4.4 Docker Compose 一键部署

如果你想把 Ollama 和一个 Web UI 一起跑，用 Compose 最方便：

```yaml
# docker-compose.yml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    ports:
      - "3000:8080"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - webui_data:/app/backend/data
    depends_on:
      - ollama
    restart: unless-stopped

volumes:
  ollama_data:
  webui_data:
```

`docker compose up -d` 后访问 `http://localhost:3000` 就能看到一个类似 ChatGPT 的聊天界面，背后跑的是你自己的本地模型。再也不用给 ChatGPT 交月费了。

### 4.5 Docker 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `OLLAMA_HOST` | 监听地址 | `127.0.0.1:11434` |
| `OLLAMA_NUM_PARALLEL` | 并行请求数 | `1` |
| `OLLAMA_MAX_LOADED_MODELS` | 同时加载的最大模型数 | `1` |
| `OLLAMA_KEEP_ALIVE` | 模型在内存中保留时间 | `5m` |
| `OLLAMA_MAX_QUEUE` | 最大排队请求数 | `512` |
| `OLLAMA_DEBUG` | 调试模式 | `false` |

示例：允许并行处理多个请求，让模型常驻内存：

```bash
docker run -d \
  --name ollama \
  --gpus all \
  -p 11434:11434 \
  -e OLLAMA_NUM_PARALLEL=4 \
  -e OLLAMA_MAX_LOADED_MODELS=2 \
  -e OLLAMA_KEEP_ALIVE=24h \
  -v ollama_data:/root/.ollama \
  ollama/ollama
```

---

## 五、Go 语言调用 Ollama

Ollama 提供了官方的 Go SDK：`github.com/ollama/ollama`。

### 5.1 安装 SDK

```bash
go get github.com/ollama/ollama
```

### 5.2 最简对话

Ollama Go SDK 的使用方式和 OpenAI SDK 很像：

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/ollama/ollama/api"
)

func main() {
    client, err := api.ClientFromEnvironment()
    if err != nil {
        log.Fatal(err)
    }

    ctx := context.Background()

    messages := []api.Message{
        {Role: "system", Content: "你是一个Go语言助手，用中文回答"},
        {Role: "user", Content: "什么是 context？"},
    }

    req := &api.ChatRequest{
        Model:    "qwen3:8b",
        Messages: messages,
    }

    resp := ""
    err = client.Chat(ctx, req, func(resp api.ChatResponse) error {
        fmt.Print(resp.Message.Content)
        resp += resp.Message.Content
        return nil
    })

    if err != nil {
        log.Fatal(err)
    }
    fmt.Println()
}
```

`client.Chat` 的回调方式默认是流式的——每生成一小段文本就回调一次。要实现非流式（一次性返回），只需在回调中累积：

```go
func chatSync(ctx context.Context, client *api.Client, req *api.ChatRequest) (string, error) {
    var fullContent strings.Builder

    req.Stream = &[]bool{false}[0] // 关闭流式
    err := client.Chat(ctx, req, func(resp api.ChatResponse) error {
        fullContent.WriteString(resp.Message.Content)
        return nil
    })

    return fullContent.String(), err
}
```

### 5.3 带工具调用（Function Calling）的对话

Ollama 也支持 Function Calling（从 0.4 版本开始）。让模型调用你的 Go 函数：

```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "time"

    "github.com/ollama/ollama/api"
)

// 定义一个"获取当前时间"的工具
func getCurrentTime() string {
    return time.Now().Format("2006-01-02 15:04:05")
}

func getWeather(city string) string {
    weather := map[string]string{
        "北京": "晴天，25°C",
        "上海": "多云，28°C",
        "深圳": "阵雨，30°C",
    }
    if w, ok := weather[city]; ok {
        return fmt.Sprintf("%s：%s", city, w)
    }
    return fmt.Sprintf("%s：暂未查询到天气信息", city)
}

func main() {
    client, err := api.ClientFromEnvironment()
    if err != nil {
        log.Fatal(err)
    }

    ctx := context.Background()

    // 定义工具列表
    tools := []api.Tool{
        {
            Type: "function",
            Function: api.ToolFunction{
                Name:        "get_current_time",
                Description: "获取当前的日期和时间",
                Parameters: api.ToolFunctionParams{
                    Type:       "object",
                    Properties: map[string]api.ToolProperty{},
                },
            },
        },
        {
            Type: "function",
            Function: api.ToolFunction{
                Name:        "get_weather",
                Description: "获取指定城市的天气信息",
                Parameters: api.ToolFunctionParams{
                    Type: "object",
                    Properties: map[string]api.ToolProperty{
                        "city": {
                            Type:        "string",
                            Description: "城市名称，如：北京、上海、深圳",
                        },
                    },
                    Required: []string{"city"},
                },
            },
        },
    }

    messages := []api.Message{
        {Role: "user", Content: "现在北京几点了？天气怎么样？"},
    }

    req := &api.ChatRequest{
        Model:    "qwen3:8b",
        Messages: messages,
        Tools:    tools,
    }

    // 第一轮：模型决定调用哪个工具
    var toolCalls []api.ToolCall
    err = client.Chat(ctx, req, func(resp api.ChatResponse) error {
        if len(resp.Message.ToolCalls) > 0 {
            toolCalls = resp.Message.ToolCalls
            for _, tc := range resp.Message.ToolCalls {
                fmt.Printf("模型请求调用工具: %s(%v)\n",
                    tc.Function.Name, tc.Function.Arguments)
            }
        } else {
            fmt.Print(resp.Message.Content)
        }
        return nil
    })
    if err != nil {
        log.Fatal(err)
    }

    if len(toolCalls) == 0 {
        return
    }

    // 添加模型的工具调用记录
    messages = append(messages, api.Message{
        Role:      "assistant",
        ToolCalls: toolCalls,
    })

    // 执行工具并添加结果
    for _, tc := range toolCalls {
        var result string
        switch tc.Function.Name {
        case "get_current_time":
            result = getCurrentTime()
        case "get_weather":
            var args map[string]string
            json.Unmarshal(tc.Function.Arguments, &args)
            result = getWeather(args["city"])
        }

        messages = append(messages, api.Message{
            Role:      "tool",
            Content:   result,
            ToolCalls: []api.ToolCall{tc},
        })
    }

    // 第二轮：把工具结果发回模型，获取最终回复
    req.Messages = messages
    fmt.Print("\n最终回复: ")
    err = client.Chat(ctx, req, func(resp api.ChatResponse) error {
        fmt.Print(resp.Message.Content)
        return nil
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println()
}
```

运行结果大致是：

```
模型请求调用工具: get_current_time({})
模型请求调用工具: get_weather({"city":"北京"})

最终回复: 现在是2026年5月20日，北京时间10点30分。北京今天晴天，气温25°C，非常适合外出。
```

这个流程和 OpenAI 的 Function Calling 完全一样：模型先告诉你"我要用哪个工具"，你执行后把结果发回去，模型再总结。

---

## 六、Ollama + Eino 框架：用本地模型构建 AI 应用

前面用 Ollama SDK 直接调用，流程控制需要自己写（发消息→收 ToolCall→执行工具→发回去→循环）。而 [Eino 框架](https://github.com/cloudwego/eino) 把这些复杂的流程控制封装好了。

关键在于：**Eino 通过 OpenAI 兼容接口连接 Ollama**。Ollama 的内置 HTTP API 完全兼容 OpenAI 的 `/v1/chat/completions` 格式，所以 Eino 的 `openai` 组件可以直接指向 Ollama。

### 6.1 架构图

```
┌──────────────────────────────────────────────┐
│                  你的 Go 应用                  │
│  ┌────────────────────────────────────────┐  │
│  │              Eino 框架                  │  │
│  │  ┌──────────┐  ┌────────┐  ┌────────┐  │  │
│  │  │ ChatModel│  │  Tool  │  │ReAct   │  │  │
│  │  │ (openai) │  │  List  │  │ Agent  │  │  │
│  │  └─────┬────┘  └────────┘  └────────┘  │  │
│  └────────┼───────────────────────────────┘  │
│           │ OpenAI 兼容 API                   │
│           │ BaseURL: http://localhost:11434   │
└───────────┼───────────────────────────────────┘
            │
    ┌───────▼────────┐
    │    Ollama       │
    │  (本地服务)      │
    │  端口: 11434    │
    │  模型: qwen3:8b │
    └────────────────┘
```

### 6.2 配置 Eino 连接 Ollama

把 BaseURL 指向 Ollama，把 APIKey 设为 `ollama`（Ollama 不需要真正的 API Key，但字段必须填）：

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "github.com/cloudwego/eino/schema"
    "github.com/cloudwego/eino-ext/components/model/openai"
)

func main() {
    ctx := context.Background()

    // 关键：BaseURL 指向 Ollama，APIKey 随便填一个非空值
    model, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
        Model:   "qwen3:8b",                     // Ollama 中的模型名
        BaseURL: "http://localhost:11434/v1",     // Ollama 的 OpenAI 兼容端点
        APIKey:  "ollama",                         // Ollama 不需要 key，但不能为空
    })
    if err != nil {
        log.Fatal(err)
    }

    // 同之前的 Eino 代码一样使用
    messages := []*schema.Message{
        schema.SystemMessage("你是一个Go语言助手，用中文回答"),
        schema.UserMessage("解释一下 Go 的 slice 和 array 的区别"),
    }

    reply, err := model.Generate(ctx, messages)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(reply.Content)
}
```

就这么简单——把 `BaseURL` 从 `https://api.openai.com/v1` 换成 `http://localhost:11434/v1`，就能用本地模型替代 OpenAI。

### 6.3 本地模型的工具调用（Function Calling）

Ollama 从 0.4 版本开始支持 Function Calling，但需要使用支持工具调用的模型（如 `qwen3:8b`、`llama3.3`）。配置好 Eino 模型后，工具的绑定和使用和云端模型完全一样：

```go
package main

import (
    "context"
    "fmt"
    "log"
    "strings"
    "time"

    "github.com/cloudwego/eino/components/tool"
    "github.com/cloudwego/eino/compose"
    "github.com/cloudwego/eino/schema"
    "github.com/cloudwego/eino-ext/components/model/openai"
)

// 文件读取工具
type FileReader struct{}

func (f *FileReader) Info(ctx context.Context) (*schema.ToolInfo, error) {
    return &schema.ToolInfo{
        Name: "read_file",
        Desc: "读取指定文件的内容",
        ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
            "path": {
                Type:     "string",
                Desc:     "要读取的文件路径",
                Required: true,
            },
        }),
    }, nil
}

func (f *FileReader) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    // 简化示例，实际应做路径安全检查
    var params struct{ Path string `json:"path"` }
    ctx, _ = schema.UnmarshalArguments(ctx, args, &params)

    content := map[string]string{
        "main.go": `package main

import "fmt"

func main() {
    fmt.Println("Hello, Eino + Ollama!")
}`,
        "go.mod": `module myapp

go 1.23

require github.com/cloudwego/eino v0.5.0`,
    }

    if c, ok := content[params.Path]; ok {
        return c, nil
    }
    return "", fmt.Errorf("文件不存在: %s", params.Path)
}

// 执行命令工具
type CommandRunner struct{}

func (c *CommandRunner) Info(ctx context.Context) (*schema.ToolInfo, error) {
    return &schema.ToolInfo{
        Name: "run_command",
        Desc: "执行系统命令并返回输出",
        ParamsOneOf: schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
            "cmd": {
                Type:     "string",
                Desc:     "要执行的命令",
                Required: true,
            },
        }),
    }, nil
}

func (c *CommandRunner) InvokableRun(ctx context.Context, args string, opts ...tool.Option) (string, error) {
    // 简化示例，实际应做命令白名单校验
    if strings.Contains(args, "go version") {
        return "go version go1.23.0 linux/amd64", nil
    }
    if strings.Contains(args, "date") {
        return time.Now().String(), nil
    }
    return "命令执行完成（演示模式）", nil
}

func main() {
    ctx := context.Background()

    // 创建模型连接（指向本地 Ollama）
    temp := float32(0.3)
    model, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
        Model:       "qwen3:8b",
        BaseURL:     "http://localhost:11434/v1",
        APIKey:      "ollama",
        Temperature: &temp,
        Timeout:     120 * time.Second,
    })
    if err != nil {
        log.Fatal(err)
    }

    // 注册工具
    tools := []tool.InvokableTool{
        &FileReader{},
        &CommandRunner{},
    }

    // 绑定工具
    if err := model.BindTools(schema.ToolInfos(tools)); err != nil {
        log.Fatal(err)
    }

    // 构建 ReAct Agent
    agent, err := compose.NewReActAgent(ctx, &compose.ReActAgentConfig{
        Model: model,
        Tools: tools,
        // 给 Agent 的系统提示词
        SystemPrompt: "你是一个编程助手，可以读取文件和执行命令。用中文回答。",
    })
    if err != nil {
        log.Fatal(err)
    }

    // 和本地 Agent 对话
    messages := []*schema.Message{
        schema.UserMessage("读取 main.go 的内容，告诉我它的包名是什么"),
    }

    reply, err := agent.Generate(ctx, messages)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Agent 回答: %s\n", reply.Content)
}
```

### 6.4 流式输出：让本地模型逐字输出

用 Eino 的 `Stream` 方法结合 Ollama，做打字机效果：

```go
func streamChat(ctx context.Context, model *openai.ChatModel, question string) error {
    messages := []*schema.Message{
        schema.SystemMessage("你是一个Go语言助手"),
        schema.UserMessage(question),
    }

    streamReader, err := model.Stream(ctx, messages)
    if err != nil {
        return err
    }

    fmt.Print("AI: ")
    for {
        chunk, err := streamReader.Recv()
        if err != nil {
            break
        }
        fmt.Print(chunk.Content) // 逐字输出
    }
    fmt.Println()

    return nil
}
```

### 6.5 本地模型 vs 云端模型的切换

Eino 的最大好处：切换模型不需要改业务代码。把模型配置放在环境变量中：

```go
func createModel(ctx context.Context) (*openai.ChatModel, error) {
    useLocal := os.Getenv("USE_LOCAL_MODEL")

    var baseURL, apiKey, modelName string

    if useLocal == "true" {
        baseURL = os.Getenv("OLLAMA_BASE_URL")
        if baseURL == "" {
            baseURL = "http://localhost:11434/v1"
        }
        apiKey = "ollama"
        modelName = os.Getenv("OLLAMA_MODEL")
        if modelName == "" {
            modelName = "qwen3:8b"
        }
    } else {
        baseURL = os.Getenv("OPENAI_BASE_URL")
        if baseURL == "" {
            baseURL = "https://api.openai.com/v1"
        }
        apiKey = os.Getenv("OPENAI_API_KEY")
        modelName = "gpt-4o-mini"
    }

    return openai.NewChatModel(ctx, &openai.ChatModelConfig{
        Model:   modelName,
        BaseURL: baseURL,
        APIKey:  apiKey,
    })
}
```

开发时用本地模型（免费、隐私），上线时切换到云端模型（性能更强），一行配置切换。

### 6.6 完整项目结构示例

一个基于 Ollama + Eino 的 CLI 编程助手：

```
local-claude/
├── main.go              # 入口
├── go.mod
├── model/
│   └── factory.go       # 模型工厂（本地/云端切换）
├── tools/
│   ├── file_reader.go   # 文件读取工具
│   ├── file_writer.go   # 文件写入工具
│   ├── command.go       # 命令执行工具
│   └── search.go        # 文件搜索工具
└── config/
    └── config.go        # 配置读取
```

```go
// main.go
package main

import (
    "bufio"
    "context"
    "fmt"
    "log"
    "os"
    "strings"

    "github.com/cloudwego/eino/components/tool"
    "github.com/cloudwego/eino/compose"
    "github.com/cloudwego/eino/schema"
    "github.com/cloudwego/eino-ext/components/model/openai"
)

func main() {
    ctx := context.Background()

    // 连接本地 Ollama
    model, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
        Model:   "qwen3:8b",
        BaseURL: "http://localhost:11434/v1",
        APIKey:  "ollama",
    })
    if err != nil {
        log.Fatal(err)
    }

    // 注册工具
    tools := []tool.InvokableTool{
        &FileReaderTool{},
        &CommandTool{},
        &FileSearchTool{},
    }

    model.BindTools(schema.ToolInfos(tools))

    // 创建 Agent
    agent, err := compose.NewReActAgent(ctx, &compose.ReActAgentConfig{
        Model: model,
        Tools: tools,
        SystemPrompt: `你是一个本地编程助手，运行在用户的电脑上。
你可以：
- 读取项目中的文件
- 搜索文件内容
- 执行安全的系统命令
用中文回答，代码风格简洁。`,
    })
    if err != nil {
        log.Fatal(err)
    }

    // 获取工作目录
    workspace, _ := os.Getwd()
    fmt.Printf("本地 AI 编程助手已启动\n工作目录: %s\n", workspace)
    fmt.Println("输入问题开始对话，输入 /bye 退出")
    fmt.Println(strings.Repeat("─", 50))

    scanner := bufio.NewScanner(os.Stdin)
    for {
        fmt.Print("\n> ")
        if !scanner.Scan() {
            break
        }
        input := strings.TrimSpace(scanner.Text())
        if input == "" {
            continue
        }
        if input == "/bye" {
            fmt.Println("再见！")
            break
        }

        messages := []*schema.Message{
            schema.UserMessage(input),
        }

        reply, err := agent.Generate(ctx, messages)
        if err != nil {
            fmt.Printf("错误: %v\n", err)
            continue
        }
        fmt.Printf("\n%s\n", reply.Content)
    }
}
```

---

## 七、常见问题与性能调优

### 7.1 模型太大，下载慢/放不下

```bash
# 用更小的量化版本
ollama pull qwen3:4b          # 4B 参数量化版，约 2.5GB
ollama pull qwen3:1.8b        # 更小，约 1GB

# 或者用专为轻量设计的模型
ollama pull phi4:mini          # 微软 Phi-4-mini，极轻量
```

### 7.2 响应太慢

```bash
# 1. 检查 GPU 是否被用上
nvidia-smi                     # 看 ollama 进程有没有占用 GPU

# 2. 调小模型上下文长度，减少计算量
# 在 Modelfile 中设置
ollama show qwen3:8b --modelfile | sed 's/num_ctx.*/num_ctx 2048/' | ollama create qwen3:8b-short -f -

# 3. 降低并发，避免 GPU OOM
# 环境变量 OLLAMA_NUM_PARALLEL=1（默认）
```

### 7.3 模型不释放显存

默认情况下，模型在最后一次使用后 5 分钟会从内存中卸载。如果希望模型常驻：

```bash
# 环境变量设置
OLLAMA_KEEP_ALIVE=24h ollama serve

# 或者启动时预加载
ollama run qwen3:8b ""    # 空输入，让模型加载到内存
```

### 7.4 局域网内共享 Ollama

```bash
# 监听所有网络接口
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

然后局域网内其他机器就能通过 `http://你的IP:11434` 访问。

---

## 八、总结

| 对比维度 | 云端 API（OpenAI/DeepSeek） | Ollama 本地部署 |
|---|---|---|
| 数据安全 | 数据发送到第三方 | 数据完全在本地 |
| 离线使用 | 不可用 | 可用 |
| 成本 | 按 Token 付费 | 免费（硬件成本） |
| 模型能力 | 顶级（GPT-4o 等） | 中等（开源模型） |
| 响应速度 | 取决于网络 | 取决于本地 GPU |
| 运维 | 零维护 | 需要管理服务 |

**关键结论**：

1. **Ollama 是本地 LLM 的最佳入口**——安装、模型管理、API 服务一条龙，体验极佳
2. **Go SDK 简洁**——API 风格和 OpenAI 一致，学习成本低
3. **Docker 部署**——用 GPU 透传 + Volume 持久化，生产环境可用
4. **与 Eino 框架完美配合**——改一行 `BaseURL` 就能从云端切换到本地模型，工具调用、ReAct Agent 等高级功能全部可用

适合的场景：本地开发调试、敏感数据处理、离线环境、学习 LLM 应用开发。不适合的场景：需要顶级推理能力的生产环境——那个还是交给 GPT-4o 或 Claude。

**下一步**：如果你还没看过 Eino 框架的文章，可以先读[《Eino框架详解》](https://mife-user.github.io/posts/eino%E6%A1%86%E6%9E%B6%E8%AF%A6%E8%A7%A3/)了解 Agent 和 Tool 的实现细节，再回过头来用本地 Ollama 跑这些示例。
