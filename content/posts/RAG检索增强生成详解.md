---
title: 'RAG 检索增强生成详解：概念、原理与 Eino 框架实战'
date: 2026-05-22T12:00:00+08:00
draft: false
tags: ["Go", "Eino", "RAG", "LLM", "AI", "向量数据库", "Embedding", "Redis", "Milvus"]
---

假设你想做一个能回答项目文档问题的 AI 助手——比如"这个函数的参数是什么？""如何配置 Redis 连接？"——直接把全部文档塞进 ChatGPT 上下文窗口？太贵、太长、还会被截断。这就是 RAG 的用武之地。

**本文从 RAG 的核心概念和原理出发，结合 Eino 框架的完整组件体系，带你一步步构建可持久化的知识库问答系统。覆盖 Embedding 模型选型、Redis/Milvus/Chroma/PGVector 等向量数据库持久化方案对比，以及一个完整的本地文档问答实战案例。**

---

## 目录

- [一、RAG 概念基础](#一rag-概念基础)
  - [1.1 什么是 RAG](#11-什么是-rag)
  - [1.2 为什么需要 RAG](#12-为什么需要-rag)
  - [1.3 RAG 工作流程全景](#13-rag-工作流程全景)
- [二、RAG 核心原理](#二rag-核心原理)
  - [2.1 文档加载与解析](#21-文档加载与解析)
  - [2.2 文档分割策略](#22-文档分割策略)
  - [2.3 文本向量化](#23-文本向量化)
  - [2.4 向量相似度检索](#24-向量相似度检索)
  - [2.5 上下文增强生成](#25-上下文增强生成)
- [三、Eino 框架 RAG 组件详解](#三eino-框架-rag-组件详解)
  - [3.1 document.Loader —— 文档加载](#31-documentloader--文档加载)
  - [3.2 document.Transformer —— 文档分割](#32-documenttransformer--文档分割)
  - [3.3 embedding.Embedder —— 向量化](#33-embeddingembedder--向量化)
  - [3.4 indexer.Indexer —— 向量存储](#34-indexerindexer--向量存储)
  - [3.5 retriever.Retriever —— 检索](#35-retrieverretriever--检索)
  - [3.6 完整 Pipeline 串联](#36-完整-pipeline-串联)
- [四、Embedding 模型选型](#四embedding-模型选型)
  - [4.1 云端 vs 本地对比](#41-云端-vs-本地对比)
  - [4.2 主流模型介绍与 Eino 配置](#42-主流模型介绍与-eino-配置)
  - [4.3 动态切换 Embedding 模型](#43-动态切换-embedding-模型)
- [五、向量数据库与持久化方案](#五向量数据库与持久化方案)
  - [5.1 为什么 Redis 重启后知识库就没了](#51-为什么-redis-重启后知识库就没了)
  - [5.2 Redis Stack 持久化 —— RDB 与 AOF](#52-redis-stack-持久化--rdb-与-aof)
  - [5.3 Milvus —— 专业向量数据库](#53-milvus--专业向量数据库)
  - [5.4 Chroma —— 轻量嵌入式向量库](#54-chroma--轻量嵌入式向量库)
  - [5.5 PGVector —— PostgreSQL 扩展](#55-pgvector--postgresql-扩展)
  - [5.6 本地文件方案](#56-本地文件方案)
  - [5.7 全方案对比选型表](#57-全方案对比选型表)
- [六、完整实战：本地文档问答系统](#六完整实战本地文档问答系统)
  - [6.1 需求与架构](#61-需求与架构)
  - [6.2 环境准备](#62-环境准备)
  - [6.3 完整代码实现](#63-完整代码实现)
  - [6.4 运行与验证](#64-运行与验证)
  - [6.5 重启后验证持久化](#65-重启后验证持久化)
- [七、总结与展望](#七总结与展望)

---

## 一、RAG 概念基础

### 1.1 什么是 RAG

**RAG（Retrieval-Augmented Generation，检索增强生成）** 是一种让大语言模型在回答问题时，先到外部知识库中"翻找"相关资料，再将资料连同问题一起交给模型生成答案的技术。

一句话概括：**先检索，再生成。**

打个比方：把 LLM 想象成一个博学但健忘的学者。他脑子里有海量知识，但无法记住你昨天才给他的项目文档。RAG 相当于在他桌前放了一个书架——每次你提问，他先翻书架找到相关章节，再看问题回答。书架就是你的知识库，翻阅的过程就是检索。

数据结构上，这个"书架"的索引不是按目录页码，而是按**向量相似度**。当你问"Redis 怎么持久化"时，系统把你的问题转换成一个向量，在知识库中找到向量最相近的几个文档片段，把这些片段作为"参考资料"注入到 LLM 的 Prompt 中。

### 1.2 为什么需要 RAG

直接问 LLM 不好吗？三个核心痛点：

| 问题 | 说明 |
|------|------|
| **幻觉（Hallucination）** | LLM 会自信地编造不存在的事实。问它"我们项目的 Redis 配置是什么"，它不知道，但会编一个。 |
| **知识截止（Knowledge Cutoff）** | 训练数据有截止日期。模型不知道 2025 年新发布的框架、你刚写的代码。 |
| **领域知识缺失** | 你的内部文档、API 规范、设计决策记录——这些都从未出现在模型的训练数据中。 |

RAG 通过**外部知识注入**一次性解决这三个问题：检索到的片段是真实的、最新的、领域专属的。LLM 的角色从"全知全能的回答者"转变为"基于给定资料的总结者"——可信度大幅提升。

### 1.3 RAG 工作流程全景

一个完整的 RAG 系统分为**离线索引**和**在线查询**两个阶段：

```
┌─────────────────────────────────────────────────┐
│                  离线索引阶段                      │
│                                                 │
│  [文档] → [加载] → [分割] → [向量化] → [存储]     │
│                                                 │
│  PDF/MD   读取    切片     Embedding   向量数据库  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│                  在线查询阶段                      │
│                                                 │
│  [问题] → [向量化] → [检索] → [拼接Prompt] → [LLM] │
│                                                 │
│  用户输入  Embedding  Top-K获取  问题+上下文   生成答案 │
└─────────────────────────────────────────────────┘
```

两个阶段共享同一个 Embedding 模型和向量数据库。索引阶段把文档"写入"知识库，查询阶段从知识库"读出"相关内容。

---

## 二、RAG 核心原理

### 2.1 文档加载与解析

一切从文档开始。你的知识库可能包含各种格式：

- **纯文本**（.txt, .md）—— 直接读取
- **PDF** —— 需要解析文本层（非扫描版）或 OCR（扫描版）
- **HTML** —— 提取 body 文本，去除标签
- **代码文件** —— 保留语法结构，按函数/类分割
- **Office 文档** —— docx/xlsx 需要专门的解析库

在 Eino 中，文档加载由 `document.Loader` 抽象。它接受一个 Source（文件路径、URL、Reader），返回 `[]*schema.Document`。每个 Document 包含内容、元数据（来源、页码等）。

### 2.2 文档分割策略

大模型有上下文窗口限制，且检索精度在长文本中会下降。因此文档需要被切分为合适大小的**Chunk（文档片段）**。

**三种主流分割策略：**

**① 固定大小分割（Fixed-size Splitting）**

按字符数或 Token 数等分。最简单，但可能在句子中间切断，破坏语义。

```
文档：Go 是一门静态类型语言。它由 Google 开发。语法简洁高效。
分割（每 15 字）：
  Chunk1: "Go 是一门静态类型语言。它"
  Chunk2: "由 Google 开发。语法简洁高效。"
```

Chunk2 开头缺少主语，语义不完整。解决办法是加 overlap（重叠窗口）：

```
  Chunk1: "Go 是一门静态类型语言。它由 Google 开发。"
  Chunk2: "它由 Google 开发。语法简洁高效。"
```

**② 递归字符分割（Recursive Character Splitting）**

按优先级依次尝试分隔符：`\n\n` → `\n` → `。` → `.` → ` ` → `""`。优先在段落、句子边界切分，语义完整性远优于固定大小。

这是 Eino 和 LangChain 的**默认策略**，推荐首选。

**③ 语义分割（Semantic Splitting）**

用 Embedding 模型计算相邻句子的相似度，在相似度骤降处切分。效果最好但计算成本最高。

> **选型建议**：递归字符分割是性价比最优的选择，覆盖 90% 的场景。只有处理高度非结构化的长文本时才考虑语义分割。

### 2.3 文本向量化

**向量化（Embedding）** 是将文本映射到高维向量空间的过程。语义相近的文本，向量距离也相近。

```
"Redis 持久化" → [0.12, -0.34, 0.78, ..., 0.05]  (768维)
"Redis 数据保存" → [0.14, -0.31, 0.75, ..., 0.03]  (768维)
"今天天气很好" → [-0.42, 0.67, -0.11, ..., 0.58]   (768维)
```

前两个向量的余弦相似度很高（接近 1），第三个与前两个相差很远（接近 0）。

**数学直觉（不需要深入，理解即可）：**

- 每个维度代表一种"语义特征"（比如"是否是技术术语""情感倾向""主题分类"）
- Embedding 模型通过大规模预训练学会了将文本映射到有意义的向量空间
- 这种映射是**不可解释的**（你不知道第 42 维代表什么），但**有效的**（距离确实反映语义关系）

常用的 Embedding 维度：384（轻量）、768（标准）、1536（OpenAI）、1024（BGE-M3）。

### 2.4 向量相似度检索

知识库中存储了成千上万个文档片段的向量。检索就是找到与问题向量最相似的 K 个。

**三种相似度度量：**

| 度量方式 | 公式直觉 | 适用场景 |
|----------|----------|----------|
| **余弦相似度** | 两个向量夹角的余弦值，只关心方向不关心长度 | 文本检索（最常用） |
| **欧氏距离** | 向量空间中的直线距离 | 需要同时考虑方向和大小 |
| **内积（Dot Product）** | 向量投影长度，大小和方向都重要 | 某些 Embedding 模型优化了内积 |

检索优化技术：

- **MMR（最大边际相关性）**：在选择 Top-K 时平衡相关性与多样性，避免返回高度重复的片段
- **重排序（Rerank）**：粗检索（ANN 近似最近邻）+ 精排序（Cross-encoder），先召回 Top-N，再用更精确的模型重新排序

### 2.5 上下文增强生成

检索到相关片段后，将它们拼接到 Prompt 中，交给 LLM 生成答案。

```
Prompt 模板：
┌────────────────────────────────────────────┐
│  你是一个技术支持助手。请根据以下参考资料    │
│  回答用户的问题。如果参考资料中没有相关信息，│
│  请如实告知。                              │
│                                            │
│  参考资料：                                │
│  ┌──────────────────────────────────────┐  │
│  │ {检索到的文档片段 1}                  │  │
│  │ {检索到的文档片段 2}                  │  │
│  │ {检索到的文档片段 3}                  │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  用户问题：{用户输入的问题}                 │
│  回答：                                    │
└────────────────────────────────────────────┘
```

这个 Prompt 设计有几个关键点：

1. **角色设定**：明确助手的职责边界
2. **边界声明**：告诉模型"不知道就说不知道"，减少幻觉
3. **上下文在前**：参考资料放在问题前面，模型处理更准确
4. **格式约束**：清晰的段落分隔，帮助模型区分参考资料和用户输入

---

## 三、Eino 框架 RAG 组件详解

Eino（CloudWeGo 出品）将 RAG 的每个环节抽象为独立的组件接口，通过组合模式串联成完整 Pipeline。下面逐一拆解每个组件的作用、接口和使用方法。

### 3.1 document.Loader —— 文档加载

负责从不同来源读取文档内容：

```go
import "github.com/cloudwego/eino/components/document"

// 从文件加载
loader, err := document.NewLoader(ctx, &document.LoaderConfig{
    Source: document.Source{Type: "file", URI: "./docs/"},
    // 支持：file, url, reader
})

// 返回 []*schema.Document
docs, err := loader.Load(ctx, document.LoaderInput{})
```

每个 `schema.Document` 结构：

```go
type Document struct {
    ID       string                 // 文档唯一标识
    Content  string                 // 文档内容
    MetaData map[string]interface{} // 元数据（来源路径、页码、时间等）
}
```

### 3.2 document.Transformer —— 文档分割

负责将长文档切分为语义独立的 Chunk：

```go
import "github.com/cloudwego/eino/components/document"

// 使用递归字符分割器
splitter, err := document.NewTransformer(ctx, &document.TransformerConfig{
    Splitter: &document.RecursiveCharSplitter{
        ChunkSize:    500,  // 每个 Chunk 最大字符数
        ChunkOverlap: 50,   // 相邻 Chunk 的重叠字符数
        Separators:   []string{"\n\n", "\n", "。", ".", " ", ""}, // 分隔符优先级
    },
})

// 输入 []*schema.Document，输出 []*schema.Document
chunks, err := splitter.Transform(ctx, docs)
```

`ChunkOverlap` 的作用是让相邻 Chunk 共享部分文本，避免关键信息恰好落在切分边界上被割裂。

### 3.3 embedding.Embedder —— 向量化

将文本转为向量，Eino 支持多种 Embedding 后端：

```go
import "github.com/cloudwego/eino/components/embedding"

// 使用 OpenAI Embedding
emb, err := embedding.NewEmbedder(ctx, &embedding.Config{
    Model: "text-embedding-3-small",
    APIKey: os.Getenv("OPENAI_API_KEY"),
})

// 对单段文本向量化
result, err := emb.EmbedStrings(ctx, []string{"Go 是一门静态类型语言"})
// result[i] 是 []float64，即该文本的向量表示
```

Eino 支持的后端：OpenAI / Ark（字节跳动）/ Ollama（本地）/ HuggingFace TEI 等。切换后端只需修改 Config 字段，**代码逻辑完全不变**。

### 3.4 indexer.Indexer —— 向量存储

将向量和原始文档片段存入向量数据库：

```go
import "github.com/cloudwego/eino/components/indexer"

// 使用 Redis 作为向量存储
indexer, err := indexer.NewIndexer(ctx, &indexer.Config{
    Store: &indexer.RedisStore{
        Addr:     "localhost:6379",
        Password: "",
        DB:       0,
        Index:    "my_knowledge_base", // 索引名称
        VectorField: "embedding",      // 向量字段名
        Dim:      768,                 // 向量维度
    },
})

// 将文档片段及其向量存入数据库
err := indexer.Store(ctx, &indexer.StoreRequest{
    Documents: chunks,       // 文档片段
    Embeddings: embeddings,  // 对应的向量
})
```

其他支持的 Store 类型：`MilvusStore`、`ChromaStore`、`PGVectorStore`、`VolcVikingDBStore` 等。

### 3.5 retriever.Retriever —— 检索

根据用户问题从知识库中检索最相关的文档片段：

```go
import "github.com/cloudwego/eino/components/retriever"

retriever, err := retriever.NewRetriever(ctx, &retriever.Config{
    Store:      indexer.GetStore(), // 复用 Indexer 的 Store 连接
    Embedder:   emb,                // 用于将查询文本向量化
    TopK:       3,                  // 返回最相似的前 K 个结果
    ScoreThreshold: 0.7,            // 最低相似度阈值（可选）
})

// 检索相关文档
docs, err := retriever.Retrieve(ctx, "Redis 的持久化机制是什么？")
// 返回 Top-K 个最相关的 schema.Document
```

检索流程内部做的事：将查询文本向量化 → 在向量数据库执行 ANN 搜索 → 按相似度排序 → 返回 Top-K。

### 3.6 完整 Pipeline 串联

将上述组件串联为一个端到端的 RAG Pipeline：

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/cloudwego/eino/components/document"
    "github.com/cloudwego/eino/components/embedding"
    "github.com/cloudwego/eino/components/indexer"
    "github.com/cloudwego/eino/components/model"
    "github.com/cloudwego/eino/components/prompt"
    "github.com/cloudwego/eino/components/retriever"
    "github.com/cloudwego/eino/schema"
)

func main() {
    ctx := context.Background()

    // 1. 加载文档
    loader, _ := document.NewLoader(ctx, &document.LoaderConfig{
        Source: document.Source{Type: "file", URI: "./docs/"},
    })
    docs, _ := loader.Load(ctx, document.LoaderInput{})

    // 2. 分割文档
    splitter, _ := document.NewTransformer(ctx, &document.TransformerConfig{
        Splitter: &document.RecursiveCharSplitter{
            ChunkSize:    500,
            ChunkOverlap: 50,
        },
    })
    chunks, _ := splitter.Transform(ctx, docs)

    // 3. 向量化所有 Chunk
    emb, _ := embedding.NewEmbedder(ctx, &embedding.Config{
        Model:  "text-embedding-3-small",
        APIKey: "...",
    })
    var texts []string
    for _, c := range chunks {
        texts = append(texts, c.Content)
    }
    vectors, _ := emb.EmbedStrings(ctx, texts)

    // 4. 存入向量数据库
    idx, _ := indexer.NewIndexer(ctx, &indexer.Config{
        Store: &indexer.RedisStore{
            Addr:  "localhost:6379",
            Index: "my_kb",
            Dim:   1536,
        },
    })
    idx.Store(ctx, &indexer.StoreRequest{
        Documents:  chunks,
        Embeddings: vectors,
    })

    // 5. 创建检索器
    ret, _ := retriever.NewRetriever(ctx, &retriever.Config{
        Store:    idx.GetStore(),
        Embedder: emb,
        TopK:     3,
    })

    // 6. 检索 + 生成
    question := "如何配置 Redis 持久化？"
    retrievedDocs, _ := ret.Retrieve(ctx, question)

    // 拼接上下文
    var contextText string
    for i, d := range retrievedDocs {
        contextText += fmt.Sprintf("参考资料%d:\n%s\n\n", i+1, d.Content)
    }

    // 7. 使用 ChatTemplate 构建 Prompt
    tmpl, _ := prompt.FromMessages(ctx,
        schema.SystemMessage("根据参考资料回答用户问题。如果资料中没有相关信息，请如实告知。"),
        schema.UserMessage("参考资料：\n{context}\n\n用户问题：{question}"),
    )
    messages, _ := tmpl.Format(ctx, map[string]any{
        "context":  contextText,
        "question": question,
    })

    // 8. 调用 LLM 生成答案
    chatModel, _ := model.NewChatModel(ctx, &model.Config{
        Model:  "gpt-4o",
        APIKey: "...",
    })
    response, _ := chatModel.Generate(ctx, messages)

    fmt.Println(response.Content)
}
```

这就是一个完整的 Eino RAG Pipeline。核心流程 8 步，每个组件职责清晰、可独立替换。

---

## 四、Embedding 模型选型

### 4.1 云端 vs 本地对比

| 维度 | 云端（OpenAI 等） | 本地（Ollama/HuggingFace） |
|------|-------------------|---------------------------|
| **精度** | 高，持续优化 | 取决于模型，BGE 系列接近云端 |
| **速度** | 受网络延迟影响 | 本地推理，延迟可控 |
| **成本** | 按 Token 计费 | 免费，但占用本地 GPU/CPU |
| **隐私** | 数据上传到云端 | 数据不离开本机 |
| **部署** | 无需部署 | 需要拉取模型、配置服务 |
| **离线能力** | 不可用 | 可用 |

### 4.2 主流模型介绍与 Eino 配置

**① OpenAI text-embedding-3-small（推荐云端场景）**

```go
emb, err := embedding.NewEmbedder(ctx, &embedding.Config{
    Model:      "text-embedding-3-small",
    APIKey:     os.Getenv("OPENAI_API_KEY"),
    Dimensions: 1536, // 可选：指定输出维度
})
```

特点：1536 维（或可裁剪到 512），多语言支持良好，MTEB 基准排名靠前。按 Token 计费，约 $0.02/1M tokens。

**② BGE-M3（推荐中文场景）**

BAAI 出品，支持中英双语，1024 维。通过 Ollama 本地部署：

```bash
ollama pull bge-m3
```

```go
// Eino 中通过 Ollama 接入
emb, err := embedding.NewEmbedder(ctx, &embedding.Config{
    Model:    "bge-m3",
    BaseURL:  "http://localhost:11434",
    Provider: "ollama",
})
```

**③ nomic-embed-text（推荐轻量本地场景）**

137M 参数，768 维，CPU 可运行，速度极快：

```bash
ollama pull nomic-embed-text
```

```go
emb, err := embedding.NewEmbedder(ctx, &embedding.Config{
    Model:    "nomic-embed-text",
    BaseURL:  "http://localhost:11434",
    Provider: "ollama",
})
```

**④ 火山引擎 Ark Embedding（字节体系首选）**

如果用了 Eino + 豆包大模型，Ark Embedding 是同生态的自然选择：

```go
emb, err := embedding.NewEmbedder(ctx, &embedding.Config{
    Model:    "doubao-embedding",
    APIKey:   os.Getenv("ARK_API_KEY"),
    Provider: "ark",
})
```

### 4.3 动态切换 Embedding 模型

Eino 的组件化设计使得切换 Embedding 模型只需修改 Config，不涉及业务代码：

```go
// 根据环境变量决定用哪个模型
func newEmbedder(ctx context.Context) (embedding.Embedder, error) {
    provider := os.Getenv("EMBEDDING_PROVIDER") // "openai" / "ollama" / "ark"

    switch provider {
    case "openai":
        return embedding.NewEmbedder(ctx, &embedding.Config{
            Model:  "text-embedding-3-small",
            APIKey: os.Getenv("OPENAI_API_KEY"),
        })
    case "ollama":
        return embedding.NewEmbedder(ctx, &embedding.Config{
            Model:    "bge-m3",
            BaseURL:  "http://localhost:11434",
            Provider: "ollama",
        })
    default:
        return embedding.NewEmbedder(ctx, &embedding.Config{
            Model:    "nomic-embed-text",
            BaseURL:  "http://localhost:11434",
            Provider: "ollama",
        })
    }
}
```

**Embedding 模型与向量数据库维度必须一致**。切换模型时，如果新旧模型输出维度不同，需要重建索引（清空旧向量，用新模型重新向量化所有文档）。

---

## 五、向量数据库与持久化方案

这是本文最核心的实战部分。很多开发者在做 RAG POC 时发现：Redis 存的知识库，一重启就没了。下面逐一剖析各种方案如何解决持久化问题。

### 5.1 为什么 Redis 重启后知识库就没了

Redis 是**内存数据库**。默认配置下，所有数据只存在内存中。进程重启、服务器重启、Docker 容器重建——数据即刻消失。

```bash
# 存入知识
redis-cli FT.CREATE idx ON HASH PREFIX 1 doc: ...
redis-cli HSET doc:1 content "Redis 持久化方案..." embedding [向量数据]

# 重启 Redis
docker restart redis

# 什么都没了
redis-cli FT.SEARCH idx "*"  # 返回空
```

对于 RAG 知识库来说，索引上百个文档可能需要几分钟，花几十万 Token（==钱）。每次重启都重建索引是**不可接受的浪费**。

**解决思路**：让向量数据库自带持久化能力，或者使用外存方案。

### 5.2 Redis Stack 持久化 —— RDB 与 AOF

好消息：Redis Stack（带 RediSearch 模块）支持 RAG 所需的所有持久化机制。只需要**正确配置**。

**RDB（快照持久化）**

每隔 N 秒/次修改，将内存数据全量写入磁盘 `.rdb` 文件。

```bash
# redis.conf
save 900 1      # 900 秒内至少 1 次修改则保存
save 300 10     # 300 秒内至少 10 次修改则保存
save 60 10000   # 60 秒内至少 10000 次修改则保存
```

优点：恢复速度快，文件紧凑。缺点：两次快照之间的数据可能丢失。

**AOF（追加文件持久化）**

将每条写命令追加到 `.aof` 日志文件。重启时回放命令重建数据。

```bash
# redis.conf
appendonly yes                  # 开启 AOF
appendfsync everysec            # 每秒刷盘（平衡性能与安全）
```

AOF 三个刷盘策略：

| 策略 | 行为 | 数据安全 | 性能 |
|------|------|----------|------|
| `always` | 每条命令立即刷盘 | 最高 | 最低 |
| `everysec` | 每秒批量刷盘 | 丢 1 秒数据 | 中等 |
| `no` | 由操作系统决定 | 不可控 | 最高 |

**推荐生产配置**：RDB + AOF 同时开启。

```bash
# redis.conf 生产环境推荐配置
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

**Docker 部署持久化 Redis Stack**：

```bash
docker run -d \
  --name redis-stack \
  -p 6379:6379 \
  -v ./redis-data:/data \
  -e REDIS_ARGS="--save 900 1 --save 300 10 --appendonly yes --appendfsync everysec" \
  redis/redis-stack-server:latest
```

关键：`-v ./redis-data:/data` 将 RDB 和 AOF 文件持久化到宿主机。Docker 容器重建后，数据依然存在。

**验证持久化**：

```bash
# 1. 索引一些文档（使用 Eino Indexer）
go run main.go index --dir ./docs/

# 2. 重启 Redis
docker restart redis-stack

# 3. 查询索引 —— 依然存在
redis-cli FT._LIST          # 输出: my_kb
redis-cli FT.SEARCH my_kb "*" # 返回之前索引的文档
```

### 5.3 Milvus —— 专业向量数据库

[Milvus](https://milvus.io) 是云原生向量数据库，专为十亿级向量检索设计。**持久化默认开启**，无需额外配置。

```go
// Eino 中使用 Milvus
idx, err := indexer.NewIndexer(ctx, &indexer.Config{
    Store: &indexer.MilvusStore{
        Host:     "localhost",
        Port:     19530,
        Database: "default",
        Collection: "knowledge_base",
        Dim:       1024,
    },
})
```

**Milvus 持久化架构**：

- **元数据** → etcd（分布式键值存储）
- **向量数据** → MinIO / S3（对象存储）
- **日志** → 本地 RocksDB + 异步刷写到对象存储

所有数据都在外部存储中，**Milvus 进程本身可以随意重启**，数据不受影响。

**适用场景**：大规模生产环境、十亿+级别向量、需要分布式检索、需要混合检索（向量 + 标量过滤）。

**Docker Compose 快速启动**：

```yaml
# milvus-standalone docker-compose
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
  minio:
    image: minio/minio:latest
    volumes:
      - ./minio-data:/minio_data      # 持久化关键
  milvus:
    image: milvusdb/milvus:v2.4.0
    depends_on: [etcd, minio]
```

### 5.4 Chroma —— 轻量嵌入式向量库

[Chroma](https://trychroma.com) 是 Python 原生的轻量级向量数据库，**默认将数据持久化到本地磁盘**。Go 生态中可以通过 Chroma 的 HTTP API 或官方 Go SDK 接入。

```go
// Eino 中使用 Chroma
idx, err := indexer.NewIndexer(ctx, &indexer.Config{
    Store: &indexer.ChromaStore{
        Host:  "localhost",
        Port:  8000,
        Collection: "knowledge_base",
        Dim:   768,
    },
})
```

**Docker 启动（挂载持久化目录）**：

```bash
docker run -d \
  --name chroma \
  -p 8000:8000 \
  -v ./chroma-data:/chroma/chroma \
  -e IS_PERSISTENT=TRUE \
  chromadb/chroma
```

`IS_PERSISTENT=TRUE` + 目录挂载 = 数据写入磁盘。Chroma 底层使用 SQLite 存储元数据 + Apache Parquet 存储向量。

**适用场景**：快速原型、中小规模、追求部署简单。Python 生态优先。

### 5.5 PGVector —— PostgreSQL 扩展

如果项目中已经有 PostgreSQL，PGVector 是最自然的 RAG 持久化选择——不需要引入新组件。

```sql
-- 启用扩展
CREATE EXTENSION vector;

-- 创建知识库表（持久化在 PostgreSQL 中）
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(1536),  -- 向量列
    metadata JSONB
);

-- 创建向量索引（IVFFlat）
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);
```

在 Eino 中使用：

```go
idx, err := indexer.NewIndexer(ctx, &indexer.Config{
    Store: &indexer.PGVectorStore{
        Host:     "localhost",
        Port:     5432,
        User:     "postgres",
        Password: "...",
        Database: "rag_db",
        Table:    "documents",
        Dim:      1536,
    },
})
```

**PGVector 的优点**：

- 事务级持久化，支持 `BEGIN/COMMIT/ROLLBACK`
- 向量搜索 + 标准 SQL 过滤（`WHERE metadata->>'date' > '2025-01-01'`）
- 利用现有 PG 备份/恢复/主从复制体系
- 无需额外运维组件

**适用场景**：已有 PostgreSQL 的项目、需要混合检索（向量 + 结构化过滤）、注重运维简单。

### 5.6 本地文件方案

对于极简场景（单机、离线、零依赖），可以使用嵌入式方案：

**方案 A：BoltDB + 暴力搜索**

```go
import "go.etcd.io/bbolt"

// 将所有向量序列化存入 BoltDB
// 每次查询时，暴力计算余弦相似度（适用于 < 10000 向量）
db.Update(func(tx *bolt.Tx) error {
    b := tx.Bucket([]byte("vectors"))
    // key: doc_id, value: 序列化的向量 + 文本内容
    return b.Put([]byte(id), data)
})
```

优点：零外部依赖。缺点：无 ANN 索引，超 1 万条后搜索极慢。

**方案 B：SQLite + sqlite-vec 扩展**

[sqlite-vec](https://github.com/asg017/sqlite-vec) 是 SQLite 的向量搜索扩展，支持 ANN 索引：

```sql
-- 创建向量表
CREATE VIRTUAL TABLE vec_items USING vec0(
    embedding float[768],
    content TEXT
);

-- 插入向量
INSERT INTO vec_items VALUES (?, ?);

-- KNN 搜索
SELECT content, vec_distance_cosine(embedding, ?) AS distance
FROM vec_items
ORDER BY distance
LIMIT 5;
```

优点：SQLite 天然持久化（单文件）、ANN 索引、零服务器。缺点：社区较新，生产验证不如 PGVector 充分。

### 5.7 全方案对比选型表

| 方案 | 持久化方式 | 集群 | ANN 算法 | 部署复杂度 | 适用规模 | Go SDK |
|------|-----------|------|----------|-----------|----------|--------|
| **Redis Stack** | RDB+AOF 配置开启 | 支持 | HNSW | ★☆☆ | 百万级 | ✅ Eino 内置 |
| **Milvus** | 默认（MinIO+etcd） | 原生分布式 | 多种（IVF/HNSW/DiskANN） | ★★★ | 十亿级 | ✅ Eino 内置 |
| **Chroma** | 本地磁盘（需开启） | 单节点 | HNSW | ★☆☆ | 百万级 | ✅ HTTP API |
| **PGVector** | PostgreSQL 事务级 | 利用 PG 集群 | IVFFlat/HNSW | ★★☆ | 亿级 | ✅ Eino 内置 |
| **BoltDB** | 默认文件 | 无 | 无（暴力搜索） | ★☆☆ | 万级 | 自实现 |
| **SQLite+vec** | 默认文件 | 无 | 多种 ANN | ★☆☆ | 百万级 | CGo/FFI |

**选型决策树**：

```
要极简、离线运行？
├─ 是 → 文档 < 1 万条？
│        ├─ 是 → BoltDB（暴力搜索足够了）
│        └─ 否 → SQLite + sqlite-vec
└─ 否 → 已有 PostgreSQL？
         ├─ 是 → PGVector
         └─ 否 → 规模有多大？
                  ├─ < 百万 → Redis Stack（配好持久化）
                  ├─ 百万-亿 → Chroma 或 PGVector
                  └─ > 亿 → Milvus
```

---

## 六、完整实战：本地文档问答系统

### 6.1 需求与架构

实现一个**本地运行的文档问答系统**，满足以下要求：

1. 支持从 Markdown / 文本文件目录索引文档
2. 使用本地 Embedding 模型（零 API 成本）
3. 使用 Redis Stack 作为向量存储
4. Redis 重启后知识库不丢失
5. 命令行交互式问答

```
架构图：

┌──────────┐    ┌──────────────┐    ┌─────────────┐
│  CLI 程序 │───▶│  Ollama 服务  │    │  Redis Stack │
│  (Go)     │    │  bge-m3      │    │  + AOF 持久化 │
│           │    │  qwen2.5     │    │  :6379       │
│  索引/查询 │    │  :11434      │    └─────────────┘
└──────────┘    └──────────────┘
```

- **Embedding 模型**：nomic-embed-text（768 维，CPU 可运行）
- **Chat 模型**：qwen2.5（7B，本地推理）
- **向量数据库**：Redis Stack，开启 AOF + RDB 持久化
- **持久化目录**：`./redis-data/` 挂载到宿主机

> 关于 Ollama 的安装和模型拉取，参见 [Ollama 实战](https://mife-user.github.io/posts/ollama本地模型部署与eino集成/) 一文。本文假设 Ollama 已在 `localhost:11434` 运行，且已拉取 `nomic-embed-text` 和 `qwen2.5` 模型。

### 6.2 环境准备

```bash
# 1. 启动持久化 Redis Stack
docker run -d \
  --name redis-stack \
  -p 6379:6379 \
  -v $(pwd)/redis-data:/data \
  -e REDIS_ARGS="--save 60 1 --appendonly yes --appendfsync everysec" \
  redis/redis-stack-server:latest

# 2. 确认 Ollama 运行中
curl http://localhost:11434/api/tags

# 3. 创建 Go 项目
mkdir doc-qa && cd doc-qa
go mod init doc-qa
go get github.com/cloudwego/eino
go get github.com/redis/go-redis/v9

# 4. 准备测试文档
mkdir docs
echo "# 项目架构

## Redis 持久化配置

redis.conf 中开启:
- save 60 1: 60 秒内至少 1 次修改触发 RDB 快照
- appendonly yes: 开启 AOF
- appendfsync everysec: 每秒刷盘

## API 接口

### GET /api/documents

返回所有已索引的文档列表。

参数：
- page: 页码，默认 1
- size: 每页条数，默认 20

### POST /api/chat

发起对话请求。

参数：
- question: 用户问题
- context: 是否携带上下文，默认 true
" > docs/项目文档.md
```

### 6.3 完整代码实现

```go
package main

import (
    "bufio"
    "context"
    "fmt"
    "log"
    "os"
    "strings"

    "github.com/cloudwego/eino/components/document"
    "github.com/cloudwego/eino/components/embedding"
    "github.com/cloudwego/eino/components/indexer"
    "github.com/cloudwego/eino/components/model"
    "github.com/cloudwego/eino/components/prompt"
    "github.com/cloudwego/eino/components/retriever"
    "github.com/cloudwego/eino/schema"
)

const (
    redisAddr   = "localhost:6379"
    ollamaURL   = "http://localhost:11434"
    embedModel  = "nomic-embed-text" // 768 维
    chatModel   = "qwen2.5:7b"
    vectorDim   = 768
    indexName   = "doc_qa_kb"        // Redis 索引名
    chunkSize   = 300
    chunkOverlap = 30
)

func main() {
    ctx := context.Background()

    if len(os.Args) < 2 {
        fmt.Println("用法: go run . index <docs_dir>   # 索引文档")
        fmt.Println("      go run . search               # 交互式问答")
        os.Exit(1)
    }

    switch os.Args[1] {
    case "index":
        if len(os.Args) < 3 {
            log.Fatal("请指定文档目录: go run . index ./docs/")
        }
        indexDocuments(ctx, os.Args[2])
    case "search":
        interactiveSearch(ctx)
    default:
        log.Fatalf("未知命令: %s", os.Args[1])
    }
}

// ========== 索引阶段 ==========

func indexDocuments(ctx context.Context, dirPath string) {
    // 1. 加载文档
    loader, err := document.NewLoader(ctx, &document.LoaderConfig{
        Source: document.Source{Type: "file", URI: dirPath},
    })
    if err != nil {
        log.Fatalf("创建 Loader 失败: %v", err)
    }
    docs, err := loader.Load(ctx, document.LoaderInput{})
    if err != nil {
        log.Fatalf("加载文档失败: %v", err)
    }
    fmt.Printf("已加载 %d 个文档\n", len(docs))

    // 2. 分割文档
    splitter, err := document.NewTransformer(ctx, &document.TransformerConfig{
        Splitter: &document.RecursiveCharSplitter{
            ChunkSize:    chunkSize,
            ChunkOverlap: chunkOverlap,
        },
    })
    if err != nil {
        log.Fatalf("创建 Splitter 失败: %v", err)
    }
    chunks, err := splitter.Transform(ctx, docs)
    if err != nil {
        log.Fatalf("分割文档失败: %v", err)
    }
    fmt.Printf("已分割为 %d 个 Chunk\n", len(chunks))

    // 3. 向量化所有 Chunk
    emb, err := embedding.NewEmbedder(ctx, &embedding.Config{
        Model:    embedModel,
        BaseURL:  ollamaURL,
        Provider: "ollama",
    })
    if err != nil {
        log.Fatalf("创建 Embedder 失败: %v", err)
    }
    var texts []string
    for _, c := range chunks {
        texts = append(texts, c.Content)
    }
    vectors, err := emb.EmbedStrings(ctx, texts)
    if err != nil {
        log.Fatalf("向量化失败: %v", err)
    }
    fmt.Printf("已完成 %d 个 Chunk 的向量化\n", len(vectors))

    // 4. 存入 Redis（开启 AOF 持久化）
    idx, err := indexer.NewIndexer(ctx, &indexer.Config{
        Store: &indexer.RedisStore{
            Addr:        redisAddr,
            Index:       indexName,
            Dim:         vectorDim,
            DistanceMetric: "COSINE",
        },
    })
    if err != nil {
        log.Fatalf("创建 Indexer 失败: %v", err)
    }
    err = idx.Store(ctx, &indexer.StoreRequest{
        Documents:  chunks,
        Embeddings: vectors,
    })
    if err != nil {
        log.Fatalf("存储失败: %v", err)
    }
    fmt.Println("索引完成！知识库已持久化到 Redis AOF。")
}

// ========== 查询阶段 ==========

func interactiveSearch(ctx context.Context) {
    // 初始化 Embedder（与索引时相同）
    emb, err := embedding.NewEmbedder(ctx, &embedding.Config{
        Model:    embedModel,
        BaseURL:  ollamaURL,
        Provider: "ollama",
    })
    if err != nil {
        log.Fatalf("创建 Embedder 失败: %v", err)
    }

    // 初始化 ChatModel
    cm, err := model.NewChatModel(ctx, &model.Config{
        Model:   chatModel,
        BaseURL: ollamaURL,
    })
    if err != nil {
        log.Fatalf("创建 ChatModel 失败: %v", err)
    }

    // 连接 Redis，检查已有索引
    idx, err := indexer.NewIndexer(ctx, &indexer.Config{
        Store: &indexer.RedisStore{
            Addr:  redisAddr,
            Index: indexName,
            Dim:   vectorDim,
        },
    })
    if err != nil {
        log.Fatalf("连接 Redis 索引失败（是否已执行 index 命令？）: %v", err)
    }

    // 创建检索器
    ret, err := retriever.NewRetriever(ctx, &retriever.Config{
        Store:    idx.GetStore(),
        Embedder: emb,
        TopK:     3,
    })
    if err != nil {
        log.Fatalf("创建 Retriever 失败: %v", err)
    }

    // 构建 Prompt 模板
    tmpl, err := prompt.FromMessages(ctx,
        schema.SystemMessage(`你是一个技术文档助手。请严格根据下面的参考资料回答用户问题。
如果参考资料中没有相关信息，请直接说"文档中未找到相关信息"，不要编造答案。`),
        schema.UserMessage("参考资料：\n{context}\n\n用户问题：{question}\n\n请根据参考资料回答："),
    )
    if err != nil {
        log.Fatalf("创建 Prompt 模板失败: %v", err)
    }

    // 交互式问答循环
    fmt.Println("=== 文档问答系统 ===")
    fmt.Println("输入问题后按回车，输入 exit 退出")
    fmt.Println("===================")

    scanner := bufio.NewScanner(os.Stdin)
    for {
        fmt.Print("\n> ")
        if !scanner.Scan() {
            break
        }
        question := strings.TrimSpace(scanner.Text())
        if question == "" {
            continue
        }
        if question == "exit" || question == "quit" {
            fmt.Println("再见！")
            break
        }

        // 检索相关文档
        retrievedDocs, err := ret.Retrieve(ctx, question)
        if err != nil {
            fmt.Printf("检索失败: %v\n", err)
            continue
        }

        if len(retrievedDocs) == 0 {
            fmt.Println("未找到相关文档")
            continue
        }

        // 拼接上下文
        var contextBuilder strings.Builder
        for i, d := range retrievedDocs {
            contextBuilder.WriteString(fmt.Sprintf("[%d] %s\n", i+1, d.Content))
        }
        contextText := contextBuilder.String()

        // 不打印检索结果，直接生成答案
        messages, err := tmpl.Format(ctx, map[string]any{
            "context":  contextText,
            "question": question,
        })
        if err != nil {
            fmt.Printf("构造 Prompt 失败: %v\n", err)
            continue
        }

        // 调用 LLM
        resp, err := cm.Generate(ctx, messages)
        if err != nil {
            fmt.Printf("生成回答失败: %v\n", err)
            continue
        }

        fmt.Println(resp.Content)
    }
}
```

### 6.4 运行与验证

```bash
# 1. 索引文档
go run . index ./docs/
# 输出：
# 已加载 1 个文档
# 已分割为 5 个 Chunk
# 已完成 5 个 Chunk 的向量化
# 索引完成！知识库已持久化到 Redis AOF。

# 2. 交互式问答
go run . search
# > Redis 持久化怎么配置？
# 根据文档，Redis 持久化配置包含：
# - save 60 1：60秒内至少1次修改触发RDB快照
# - appendonly yes：开启AOF
# - appendfsync everysec：每秒刷盘

# > API 有哪些接口？
# 文档中定义了以下接口：
# - GET /api/documents：返回已索引文档列表，支持分页参数
# - POST /api/chat：发起对话，支持question和context参数

# > 今天天气怎么样？
# 文档中未找到相关信息
```

### 6.5 重启后验证持久化

这是整篇文章最关键的一步——验证 Redis Stack 开启 AOF 后，重启不丢数据：

```bash
# 1. 先确认知识库有数据
docker exec redis-stack redis-cli FT._LIST
# 输出: doc_qa_kb（索引存在）

docker exec redis-stack redis-cli FT.SEARCH doc_qa_kb "*" LIMIT 0 1
# 输出: 文档内容（有数据）

# 2. 重启 Redis
docker restart redis-stack

# 3. 等待 Redis 重新启动（AOF 回放完成）
sleep 3

# 4. 再次查询索引
docker exec redis-stack redis-cli FT._LIST
# 输出: doc_qa_kb（索引依然存在！）

docker exec redis-stack redis-cli FT.SEARCH doc_qa_kb "*" LIMIT 0 2
# 输出: 文档内容（数据完好！）

# 5. 用程序再次查询
go run . search
# > Redis 持久化怎么配置？
# 回答正常，无需重新索引！
```

**验证成功**：Redis 重启后，知识库完整保留。AOF 文件在 `./redis-data/appendonly.aof` 中持久化保存。

如果进一步重建 Docker 容器：

```bash
docker rm -f redis-stack
docker run -d --name redis-stack -p 6379:6379 \
  -v $(pwd)/redis-data:/data \
  -e REDIS_ARGS="--save 60 1 --appendonly yes --appendfsync everysec" \
  redis/redis-stack-server:latest

# 数据依然存在！
docker exec redis-stack redis-cli FT._LIST  # 输出: doc_qa_kb
```

**核心要点**：只要宿主机的 `./redis-data/` 目录没有被删除，数据就永远不会丢失。

---

## 七、总结与展望

本文从 RAG 的概念出发，逐步深入到 Eino 框架的每个组件，最终落地为一个可持久化的本地文档问答系统。核心要点回顾：

1. **RAG = 检索 + 生成**。先找到相关文档，再让 LLM 基于文档回答，解决幻觉和知识截止问题。
2. **文档分割是关键环节**。递归字符分割是性价比最高的默认选择，overlap 参数要合理设置。
3. **Eino 的 RAG 组件体系**完全解耦——Loader、Transformer、Embedder、Indexer、Retriever 各自独立，按需组合，按需替换。
4. **Embedding 模型选择**没有银弹：追求精度选 OpenAI/BGE-M3，追求隐私选本地 Ollama，追求性价比选 nomic-embed-text。
5. **持久化不是可选项而是必选项**。Redis 配好 AOF+RDB 完全能胜任中小规模持久化需求；规模更大则上 PGVector 或 Milvus。

RAG 技术仍在快速演进，值得关注的方向：

- **Agentic RAG**：多步检索、自我修正检索参数、动态选择检索源
- **多模态 RAG**：同时对文本、图片、表格建立索引和检索
- **Graph RAG**：结合知识图谱，在向量检索之上增加实体关系推理
- **HyDE（假设文档嵌入）**：先让 LLM 生成一个假想答案，用假想答案的向量去检索（而不是用问题本身）

Eino 框架的 DeepAgent 模块已经内置了 Agentic RAG 的能力，后续可以继续探索。

---

[返回首页](/)
