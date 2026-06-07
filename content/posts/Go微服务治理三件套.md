---
title: 'Go微服务治理三件套：日志、链路、指标'
date: 2026-06-07T22:53:20+08:00
draft: false
tags: ["Go", "微服务", "可观察性", "OpenTelemetry", "Prometheus", "slog", "zap", "日志", "链路追踪", "指标"]
---

## 前言

当你把一个单体应用拆成 5 个、10 个甚至更多的微服务后，一个用户请求可能跨越多个服务。这时你会遇到三个经典问题：

- **出错了，但日志散落在 N 个服务里，怎么快速定位？** → 你需要**集中式日志**
- **一个请求经过了哪些服务？哪个环节慢了？** → 你需要**分布式链路追踪**
- **服务整体 QPS 多少？P99 延迟多少？错误率多少？** → 你需要**指标监控**

这三者合称**可观察性三件套**（Logging、Tracing、Metrics），是微服务治理的基石。本文将带你用 Go 实战这三个方向，选择的框架如下：

| 领域 | 框架 | 理由 |
|------|------|------|
| 日志 | `log/slog` + `zap` | slog 是 Go 标准库零依赖方案；zap 是高性能生产方案 |
| 链路追踪 | OpenTelemetry | CNCF 标准，厂商中立，生态最广 |
| 指标 | Prometheus client | 最成熟，与 Grafana 无缝集成 |

读完本文你将能够：手写一个带完整可观察性的 Go 微服务，并用 Docker 一键部署全套可观察性基础设施。

---

## 一、原理讲解：三件套各自解决什么问题？

在写代码之前，先理解三件套的本质原理。这就像学车之前先知道方向盘、刹车和油门的原理一样重要。

### 1.1 日志的原理：从文本流到结构化检索

**传统日志的本质**是一个按时间顺序排列的文本流：

```text
10:00:00 server started on :8080
10:00:05 user mife login success
10:00:06 user mife query orders, count=5
10:00:10 ERROR: db connection timeout, host=db-1:5432
```

问题是：当你有 10 个服务 × 3 个实例 = 30 个日志流时，你不可能逐个 `tail -f`。所以日志需要：

**第一步：结构化。** 把日志从"人读的句子"变成"机器可解析的键值对"。

```text
传统:   "user mife login success at 10:00:05"
结构化: {"time":"10:00:05","level":"INFO","user":"mife","action":"login","result":"success"}
```

**第二步：聚合。** 所有服务的日志发送到同一个地方（Loki / Elasticsearch），按标签索引。

```text
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Service A│  │ Service B│  │ Service C│   每个服务 stdout/stderr
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │
     └──────────────┼──────────────┘
                    │ 日志采集器 (Promtail / Filebeat)
                    ▼
           ┌────────────────┐
           │  Loki / ELK     │   集中存储 + 索引
           │  {service="A",  │
           │   level="ERROR"}│
           └────────────────┘
```

**第三步：关联。** 用 `trace_id` 把同一个请求的日志串联起来。

```text
[order-svc]   trace_id=abc123 INFO  "creating order"
[inventory-svc] trace_id=abc123 ERROR "stock insufficient"  ← 同一条 trace_id
[order-svc]   trace_id=abc123 ERROR "order failed"
```

> **核心原理**：日志是**离散事件**的记录。每条日志是独立的，靠时间戳和 trace_id 关联。它的优势是**详细**（你能记录任意内容），劣势是**离散**（缺少调用关系图）。

### 1.2 链路追踪的原理：从分散调用到调用链树

**核心问题**：一个请求进来，A 调 B，B 调 C 和 D，C 调 E。如何知道这个完整调用链？

**解决方案**：在整个调用链中传递一个全局唯一的 **Trace ID**，每个调用环节记录为一个 **Span**，Span 之间用 **Parent Span ID** 建立父子关系。

```text
                    请求入口 (Trace ID = abc123)
                              │
               ┌──────────────┴──────────────┐
               │        Span A (Root)         │
               │  SpanID: aaa                 │
               │  Parent: (none)              │
               │  耗时: 500ms                  │
               └──────────────┬──────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                                       │
   ┌──────┴──────┐                         ┌──────┴──────┐
   │  Span B      │                         │  Span C      │
   │  SpanID: bbb │                         │  SpanID: ccc │
   │  Parent: aaa │                         │  Parent: aaa │
   │  耗时: 200ms │                         │  耗时: 250ms │
   └──────┬──────┘                         └──────────────┘
          │
   ┌──────┴──────┐
   │  Span D      │
   │  SpanID: ddd │
   │  Parent: bbb │
   │  耗时: 150ms │
   └─────────────┘
```

**Trace Context 传播机制（W3C 标准）**：

服务间调用时，Trace 信息通过 HTTP Header 传递：

```text
客户端发起请求时自动注入:
  traceparent: 00-abc123def456-aaa111bbb222-01
               │  │             │            │
               │  │             │            └─ 采样标志 (01=采样)
               │  │             └─ Parent Span ID
               │  └─ Trace ID (16 字节 hex)
               └─ 版本号

服务端收到请求时自动提取:
  1. 从 Header 解析 Trace ID → 知道属于哪个 Trace
  2. 用 Parent Span ID → 知道自己在调用链中的位置
  3. 创建自己的 Span ID → 下游调用时作为新的 Parent 传递
```

**采样是怎么工作的**：

并不是所有请求都需要追踪。采样的决策在 Trace 根部（请求入口）做出，然后通过 `traceparent` flag 一路传递：

```text
请求进来 → 采样决策（保留 10%）
           │
           ├─ 采样 → 创建 Trace，trace flag=01 → 全链路追踪
           └─ 不采样 → 创建 Trace，trace flag=00 → 所有服务跳过 Span 创建
```

这就是 `ParentBased` 采样器的原理：子 Span 的采样决策**继承自父 Span**，保证同一个 Trace 要么全追踪、要么全不追踪。不会出现"追踪到一半断了"的情况。

> **核心原理**：链路追踪解决的是**因果关系**。通过 Trace ID + Parent Span ID，把分散在各服务的调用还原成一棵调用树。它的优势是**全局视角**（一眼看出瓶颈在哪），劣势是**采样不完全**（不是所有请求都追踪）。

### 1.3 指标的原理：从单点数值到时间序列聚合

**核心问题**：日志能看到"一个请求 500ms 返回了"，但看不到"过去 5 分钟，99% 的请求在多少 ms 内返回"。

**Prometheus 的工作原理（拉模型）**：

```text
┌──────────────────────────────────────────────────────────┐
│                      Prometheus Server                     │
│                                                          │
│  ┌──────────────┐    每隔 15s 抓取     ┌────────────────┐ │
│  │ Service      │ ◄────────────────── │ Go 微服务 :8080 │ │
│  │ Discovery    │                     │ /metrics        │ │
│  │ (k8s/consul) │                     └────────────────┘ │
│  └──────┬───────┘                                        │
│         │ 发现目标                                        │
│  ┌──────┴───────┐                                        │
│  │ Scrape       │ ────► 写入 ────► ┌──────────────────┐ │
│  │ Manager      │                   │ TSDB (时间序列DB) │ │
│  └──────────────┘                   │ 按 label 索引     │ │
│                                     └──────────────────┘ │
│                                                          │
│  ┌──────────────┐     查询      ┌──────────────────────┐ │
│  │ Grafana      │ ◄──────────── │ PromQL Engine        │ │
│  │ Dashboard    │              │ (histogram_quantile)  │ │
│  └──────────────┘              └──────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**Histogram 分位数原理**：

这是最容易被误解的概念。当你调用 `.Observe(0.35)` 时，发生了：

```text
假设 Bucket = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0]

请求延迟 0.35s 到来:
  le=0.01  bucket: 不加（0.35 > 0.01）
  le=0.05  bucket: 不加（0.35 > 0.05）
  le=0.1   bucket: 不加（0.35 > 0.1）
  le=0.25  bucket: 不加（0.35 > 0.25）
  le=0.5   bucket: +1  （0.35 ≤ 0.5） ← 落入这个 bucket
  le=1.0   bucket: +1  （0.35 ≤ 1.0） ← 所有更大的 bucket 也 +1
  +Inf     bucket: +1  （所有值都 ≤ +Inf）

所以 bucket 是累积的。经过 1000 个请求后:
  le=0.01:  10 个请求 ≤ 10ms
  le=0.05:  50 个请求 ≤ 50ms
  le=0.1:  200 个请求 ≤ 100ms
  le=0.25: 600 个请求 ≤ 250ms
  le=0.5:  950 个请求 ≤ 500ms
  le=1.0:  990 个请求 ≤ 1000ms

PromQL histogram_quantile(0.99, ...) 从这些累积值中线性插值:
  → P99 ≈ 950ms（第 990 个请求落在 0.5~1.0s 区间）
```

> **核心原理**：指标解决的是**统计聚合**。它不做单个请求的记录，而是把大量数据点预先聚合为 Counter（累加）、Histogram（分桶计数）、Gauge（瞬时值）。优势是**查询极快**（预聚合），劣势是**丢失细节**（你不能用指标查某个具体请求的信息）。

### 1.4 三件套协作全景图

```text
一个请求进来 ──────────────────────────────────────────────►

  指标 (Metrics)                    链路 (Tracing)
  ┌──────────────────┐              ┌──────────────────────┐
  │ Counter: +1       │              │ Trace ID: abc123     │
  │ Histogram: 记录    │◄── trace_id ─│ Span A (入口)        │
  │ 延迟到bucket       │   关联       │ Span B (调用户服务)   │
  │ Gauge: 活跃连接+1  │              │ Span C (查数据库)     │
  └──────────────────┘              └──────────────────────┘
          │                                   │
          │ 聚合查询                          │ 单次查询
          ▼                                   ▼
   "过去 5 分钟 P99 是多少？"         "abc123 这个请求为什么慢？"
   回答快（预聚合）                   回答详细（完整调用树）

                         日志 (Logging)
                    ┌──────────────────────┐
                    │ trace_id=abc123       │
                    │ "querying user table" │
                    │ "found 1 row, 5ms"    │
                    │ "ERROR: timeout"      │ ◄── 错误的详细上下文
                    └──────────────────────┘
                              │
                              │ 自由文本查询
                              ▼
                    "abc123 的错误具体是什么？"
                    回答最详细（开发者写的完整上下文）
```

**三者关系一句话**：指标告诉你"出事了"，链路告诉你"哪里出的事"，日志告诉你"具体出了什么事"。

---

## 二、第一件：日志（Logging）

### 1.1 为什么结构化日志很重要？

传统日志是这样的：

```text
2026-06-07 10:30:15 User mife login success
```

机器很难解析。结构化日志是这样的：

```json
{"time":"2026-06-07T10:30:15Z","level":"INFO","msg":"user login","user":"mife","action":"login","status":"success"}
```

机器可以按字段检索、聚合、告警。**结构化日志是现代微服务的标配。**

### 1.2 方案一：slog — Go 标准库方案

Go 1.21 引入了 `log/slog`，是官方出品的结构化日志库，零依赖。

#### 快速开始

```go
package main

import (
	"log/slog"
	"os"
)

func main() {
	// 创建 JSON 格式的 logger，输出到 stdout
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

	// 基础日志
	logger.Info("server started", "port", 8080)
	// 输出: {"time":"2026-06-07T10:00:00Z","level":"INFO","msg":"server started","port":8080}

	// 带错误级别的日志
	logger.Warn("disk usage high", "usage_percent", 85.5)

	// 结构化错误日志
	logger.Error("db connection failed",
		"host", "localhost:5432",
		"error", "connection refused",
		"retry_count", 3,
	)
}
```

#### 使用 context 传递公共字段

在实际微服务中，很多字段是共用的（如 `service_name`、`trace_id`），可以用 `With` 创建子 logger：

```go
func main() {
	baseLogger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

	// 预填充公共字段
	serviceLogger := baseLogger.With(
		"service", "user-service",
		"version", "v1.2.3",
		"env", "production",
	)

	// 后续日志自动带上公共字段
	serviceLogger.Info("listening", "addr", ":8080")
	// {"time":"...","level":"INFO","msg":"listening","service":"user-service","version":"v1.2.3","env":"production","addr":":8080"}
}
```

#### 与 context 绑定 — 提取 trace_id

链路追踪的 `trace_id` 需要贯穿整个请求生命周期：

```go
// 自定义 slog key，用于从 context 取值
type contextKey string

const traceIDKey contextKey = "trace_id"

// 中间件：从 HTTP header 提取 trace_id，注入 context
func TraceMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		traceID := r.Header.Get("X-Trace-ID")
		if traceID == "" {
			traceID = generateTraceID()
		}
		ctx := context.WithValue(r.Context(), traceIDKey, traceID)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// Handler 中使用 slog + context
func UserHandler(logger *slog.Logger) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		traceID, _ := r.Context().Value(traceIDKey).(string)
		// 为本次请求创建带 trace_id 的子 logger
		reqLogger := logger.With("trace_id", traceID)

		reqLogger.Info("handling request", "method", r.Method, "path", r.URL.Path)

		user, err := fetchUser(r.Context(), 123)
		if err != nil {
			reqLogger.Error("fetch user failed", "user_id", 123, "error", err)
			http.Error(w, "internal error", 500)
			return
		}
		reqLogger.Info("user fetched", "user_id", user.ID, "name", user.Name)
	}
}
```

#### slog 最佳实践

```go
// ✅ 好：结构化字段
logger.Info("order created", "order_id", orderID, "amount", amount)

// ❌ 坏：字符串拼接
logger.Info(fmt.Sprintf("order %s created with amount %.2f", orderID, amount))

// ✅ 好：自定义日志级别判断
if slog.Default().Enabled(context.Background(), slog.LevelDebug) {
	logger.Debug("expensive debug info", "data", heavyComputation())
}

// ✅ 好：按 scope 分组
dbLogger := logger.With("scope", "database")
dbLogger.Info("query executed", "sql", query, "duration_ms", elapsed)
```

### 1.3 方案二：zap — 高性能生产方案

zap 是 Uber 出品的日志库，特点是**极高性能**和**强类型字段**。

#### 快速开始

```go
package main

import (
	"go.uber.org/zap"
)

func main() {
	// 生产环境用 NewProduction（JSON 格式，Info 级别）
	logger, _ := zap.NewProduction()
	defer logger.Sync() // 刷新缓冲区

	// 开发环境用 NewDevelopment（控制台格式，Debug 级别）
	// logger, _ := zap.NewDevelopment()

	logger.Info("server started",
		zap.Int("port", 8080),
		zap.String("env", "production"),
	)

	logger.Error("db connection failed",
		zap.String("host", "localhost:5432"),
		zap.Error(errors.New("connection refused")),
		zap.Int("retry_count", 3),
	)
}
```

#### Sugar logger — 更接近 slog 的体验

zap 提供两种 API：强类型的 `Logger` 和更宽松的 `SugaredLogger`：

```go
logger, _ := zap.NewProduction()
sugar := logger.Sugar()
defer sugar.Sync()

// Sugar 支持 Printf 风格（稍慢但方便）
sugar.Infof("user %s logged in from %s", userName, ipAddr)

// 也支持键值对
sugar.Infow("user login",
	"user", userName,
	"ip", ipAddr,
	"status", "success",
)
```

> **选择建议**：对性能敏感的热路径用 `Logger`（强类型），一般业务逻辑用 `SugaredLogger`。

#### 自定义配置

```go
func NewLogger() *zap.Logger {
	config := zap.Config{
		Level:            zap.NewAtomicLevelAt(zap.InfoLevel),
		Encoding:         "json",           // 或 "console"
		OutputPaths:      []string{"stdout"},
		ErrorOutputPaths: []string{"stderr"},
		EncoderConfig: zap.NewProductionEncoderConfig(),
	}
	// 自定义时间格式
	config.EncoderConfig.TimeKey = "timestamp"
	config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

	// 自定义日志级别名称
	config.EncoderConfig.EncodeLevel = zapcore.CapitalLevelEncoder

	logger, _ := config.Build()
	return logger
}
```

#### 与 HTTP 中间件集成

```go
func ZapMiddleware(logger *zap.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()

			// 为每个请求创建子 logger，自动带 trace_id
			traceID := r.Header.Get("X-Trace-ID")
			reqLogger := logger.With(
				zap.String("trace_id", traceID),
				zap.String("method", r.Method),
				zap.String("path", r.URL.Path),
			)

			// 注入到 context
			ctx := context.WithValue(r.Context(), loggerKey, reqLogger)
			r = r.WithContext(ctx)

			// 包装 ResponseWriter 以捕获状态码
			wrapped := &responseWriter{ResponseWriter: w, statusCode: 200}
			next.ServeHTTP(wrapped, r)

			// 记录请求完成
			reqLogger.Info("request completed",
				zap.Int("status", wrapped.statusCode),
				zap.Duration("duration", time.Since(start)),
			)
		})
	}
}
```

### 1.4 slog vs zap：怎么选？

| 维度 | slog | zap |
|------|------|-----|
| 依赖 | 零依赖（标准库） | 需要引入 `go.uber.org/zap` |
| 性能 | 良好，足够大多数场景 | 极致，零分配设计 |
| API 风格 | 键值对 `"key", val` | 强类型 `zap.String("key", val)` |
| 学习曲线 | 低，Go 开发者自带 | 中等，需要了解 zapcore |
| 适用场景 | 中小项目、工具、CLI | 高吞吐微服务、对性能有极致要求 |

我的建议：**先用 slog，性能不够再换 zap**。不过实际生产环境中 zap 仍然更常见。

---

## 三、第二件：链路追踪（Distributed Tracing）

### 2.1 为什么需要链路追踪？

假设一个 `/api/order` 请求经过 4 个服务：

```text
API Gateway → 订单服务 → 库存服务 → 支付服务
                ↓
            用户服务

你看到的日志：
[order-svc]  10:00:01.100 INFO  creating order
[inventory-svc] 10:00:01.350 ERROR stock insufficient  ← 这里失败了
[order-svc]  10:00:01.500 ERROR order failed

问题是：这三个日志来自不同服务，怎么知道它们是同一个请求？哪个环节花了 250ms？
```

链路追踪解决的就是这个问题：**用一个全局唯一的 Trace ID 串联同一个请求在所有服务中的调用**。

### 2.2 OpenTelemetry 核心概念

```text
┌─────────────────────────────────────────────────────┐
│                   一次请求 (Trace)                    │
│  Trace ID: abc123                                    │
│                                                     │
│  ┌─────────────────────────────────────┐            │
│  │       Span 1: 订单服务.createOrder   │            │
│  │       Span ID: span-001             │            │
│  │       开始: 10:00:01.000             │            │
│  │       结束: 10:00:01.500             │            │
│  │       耗时: 500ms                    │            │
│  │                                     │            │
│  │  ┌─────────────────────────────┐    │            │
│  │  │ Span 2: 库存服务.checkStock │    │            │
│  │  │ Parent: span-001            │    │            │
│  │  │ 耗时: 250ms                 │    │            │
│  │  └─────────────────────────────┘    │            │
│  │                                     │            │
│  │  ┌─────────────────────────────┐    │            │
│  │  │ Span 3: 支付服务.pay       │    │            │
│  │  │ Parent: span-001            │    │            │
│  │  │ 耗时: 150ms                 │    │            │
│  │  └─────────────────────────────┘    │            │
│  └─────────────────────────────────────┘            │
└─────────────────────────────────────────────────────┘
```

- **Trace**：一次完整的请求链路，由全局唯一的 `Trace ID` 标识
- **Span**：链路中的一个操作单元（一次 RPC 调用、一次 DB 查询、一个函数执行），有 `Span ID` 和 `Parent Span ID` 组成父子关系
- **Span Context**：Span 的上下文信息（Trace ID、Span ID 等），通过 HTTP Header 或 gRPC Metadata 在服务间传递

### 2.3 安装 OpenTelemetry

```bash
go get go.opentelemetry.io/otel
go get go.opentelemetry.io/otel/sdk/trace
go get go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc
go get go.opentelemetry.io/otel/exporters/stdout/stdouttrace
go get go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp
```

### 2.4 初始化 Tracer Provider

```go
package telemetry

import (
	"context"
	"fmt"
	"os"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/exporters/stdout/stdouttrace"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

// InitTracer 初始化 OpenTelemetry Tracer
// endpoint: OTLP collector 地址，留空则输出到 stdout（开发环境）
func InitTracer(ctx context.Context, serviceName, endpoint string) (*sdktrace.TracerProvider, error) {
	var exporter sdktrace.SpanExporter
	var err error

	if endpoint == "" {
		// 开发环境：输出到控制台
		exporter, err = stdouttrace.New(stdouttrace.WithPrettyPrint())
	} else {
		// 生产环境：通过 gRPC 发送到 OTLP Collector（如 Jaeger、Tempo）
		exporter, err = otlptracegrpc.New(ctx,
			otlptracegrpc.WithEndpoint(endpoint),
			otlptracegrpc.WithInsecure(), // 生产环境建议使用 TLS
		)
	}
	if err != nil {
		return nil, fmt.Errorf("create exporter: %w", err)
	}

	// 创建 Resource，描述这个服务
	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName(serviceName),
			semconv.ServiceVersion("v1.0.0"),
			semconv.DeploymentEnvironment(getEnv("ENV", "development")),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("create resource: %w", err)
	}

	// 创建 TracerProvider
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		// 采样策略：AlwaysSample（开发）/ TraceIDRatioBased（生产）
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)

	// 设为全局
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},  // W3C Trace Context 标准
		propagation.Baggage{},       // 传递自定义键值对
	))

	return tp, nil
}

func getEnv(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}
```

### 2.5 自动注入 HTTP 中间件

`otelhttp` 可以自动为 HTTP 服务创建 Span，无需手动埋点：

```go
package main

import (
	"net/http"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

func main() {
	// ... 初始化 tracer ...

	mux := http.NewServeMux()

	// 业务 handler
	mux.HandleFunc("GET /api/users/{id}", GetUserHandler)
	mux.HandleFunc("POST /api/orders", CreateOrderHandler)

	// 包装：otelhttp 自动为每个请求创建 Span、提取/传递 Trace Context
	handler := otelhttp.NewHandler(mux, "user-service",
		otelhttp.WithMessageEvents(otelhttp.ReadEvents, otelhttp.WriteEvents),
	)

	http.ListenAndServe(":8080", handler)
}
```

### 2.6 手动创建 Span

自动埋点之外，关键业务逻辑需要手动创建 Span：

```go
import (
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
)

func CreateOrderHandler(w http.ResponseWriter, r *http.Request) {
	// 从请求 context 获取当前 Span
	ctx := r.Context()
	tracer := otel.Tracer("order-service")

	// 创建子 Span
	ctx, span := tracer.Start(ctx, "CreateOrder")
	defer span.End()

	// 添加属性
	orderID := "ord_12345"
	span.SetAttributes(
		attribute.String("order.id", orderID),
		attribute.Float64("order.amount", 99.99),
		attribute.String("order.currency", "CNY"),
	)

	// 调用库存服务
	if err := checkInventory(ctx, orderID); err != nil {
		// 标记 Span 为错误
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		http.Error(w, "inventory check failed", 500)
		return
	}

	// 调用支付服务
	if err := processPayment(ctx, orderID); err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		http.Error(w, "payment failed", 500)
		return
	}

	span.SetStatus(codes.Ok, "order created")
	w.WriteHeader(201)
}

func checkInventory(ctx context.Context, orderID string) error {
	tracer := otel.Tracer("order-service")
	ctx, span := tracer.Start(ctx, "checkInventory")
	defer span.End()

	span.SetAttributes(attribute.String("order.id", orderID))

	// 模拟检查库存
	time.Sleep(50 * time.Millisecond)

	span.SetAttributes(attribute.Bool("inventory.sufficient", true))
	return nil
}

func processPayment(ctx context.Context, orderID string) error {
	tracer := otel.Tracer("order-service")
	ctx, span := tracer.Start(ctx, "processPayment")
	defer span.End()

	// 模拟支付
	time.Sleep(100 * time.Millisecond)

	span.AddEvent("payment processed", attribute.String("order.id", orderID))
	return nil
}
```

### 2.7 发起 HTTP 请求时传递 Trace Context

服务间 HTTP 调用需要传递 Trace Context，同样用 `otelhttp`：

```go
func callUserService(ctx context.Context, userID string) (*User, error) {
	// otelhttp 自动注入 Trace Context 到 HTTP Header
	client := &http.Client{
		Transport: otelhttp.NewTransport(http.DefaultTransport),
	}

	req, _ := http.NewRequestWithContext(ctx, "GET",
		"http://user-service:8081/api/users/"+userID, nil)

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var user User
	json.NewDecoder(resp.Body).Decode(&user)
	return &user, nil
}
```

> 在 HTTP Header 中你能看到：`traceparent: 00-{trace_id}-{span_id}-01` 这就是 W3C Trace Context 标准格式。

### 2.8 事件与 Error 的使用场景

```go
// ✅ 用 AddEvent 记录关键节点
span.AddEvent("cache.miss", attribute.String("key", cacheKey))
span.AddEvent("db.query.start")
span.AddEvent("db.query.end", attribute.Int64("rows", 42))

// ✅ 用 RecordError 记录错误
if err != nil {
	span.RecordError(err)
	span.SetStatus(codes.Error, "db query failed")
}

// ✅ 对比：标记返回成功
span.SetStatus(codes.Ok, "completed")
```

---

## 四、第三件：指标（Metrics）

### 3.1 为什么需要指标？

日志告诉你"发生了什么"，链路告诉你"怎么发生的"，指标告诉你"发生了多少、多快、多频繁"。

```text
指标能回答的问题：
- QPS（每秒请求数）是多少？
- P50/P95/P99 延迟是多少？
- 错误率是多少？
- 数据库连接池是否耗尽？
- 内存和 Goroutine 数量是否正常？
```

### 3.2 安装 Prometheus client

```bash
go get github.com/prometheus/client_golang/prometheus
go get github.com/prometheus/client_golang/prometheus/promhttp
```

### 3.3 四种核心指标类型

```text
┌──────────────┬──────────────────────────────────────────┐
│ Counter      │ 只增不减的计数器                          │
│              │ 例：请求总数、错误总数                      │
├──────────────┼──────────────────────────────────────────┤
│ Gauge        │ 可增可减的瞬时值                          │
│              │ 例：当前连接数、内存使用量、CPU 温度        │
├──────────────┼──────────────────────────────────────────┤
│ Histogram    │ 将数据分桶统计，计算分位数                  │
│              │ 例：请求延迟（0-10ms, 10-50ms, 50-100ms...）│
├──────────────┼──────────────────────────────────────────┤
│ Summary      │ 客户端计算分位数（P50/P99）                │
│              │ 例：请求延迟分位数（不推荐，用 Histogram）  │
└──────────────┴──────────────────────────────────────────┘
```

> **Histogram vs Summary**：始终优先用 Histogram。Summary 的分位数在客户端计算，多个实例无法聚合；Histogram 在 Prometheus 服务端用 `histogram_quantile()` 计算，可以跨实例聚合。

### 3.4 定义和注册指标

```go
package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// Counter: HTTP 请求总数
	HttpRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"method", "endpoint", "status"}, // 标签维度
	)

	// Histogram: HTTP 请求延迟
	HttpRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP request latency in seconds",
			Buckets: prometheus.DefBuckets, // .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10
		},
		[]string{"method", "endpoint"},
	)

	// Gauge: 当前活跃连接数
	ActiveConnections = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "active_connections",
			Help: "Current number of active connections",
		},
	)

	// Counter: 业务指标
	OrdersCreatedTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "orders_created_total",
			Help: "Total number of orders created",
		},
		[]string{"status"}, // success / failed
	)
)
```

> `promauto` 自动将指标注册到默认 Registry。你也可以手动注册以获得更多控制。

### 3.5 暴露 /metrics 端点

```go
package main

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"your-project/metrics"
)

func main() {
	mux := http.NewServeMux()

	// 暴露 /metrics 端点（Prometheus 定时抓取）
	mux.Handle("/metrics", promhttp.Handler())

	// 业务端点
	mux.HandleFunc("/api/orders", CreateOrderHandler)

	http.ListenAndServe(":8080", mux)
}
```

启动后访问 `http://localhost:8080/metrics` 可以看到类似：

```text
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/users",status="200"} 1423
http_requests_total{method="POST",endpoint="/api/orders",status="201"} 567
# HELP http_request_duration_seconds HTTP request latency in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.005"} 200
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.01"} 500
...
```

### 3.6 在代码中埋点

```go
func CreateOrderHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()

	// ... 业务逻辑 ...
	success := true
	if success {
		w.WriteHeader(201)
	} else {
		w.WriteHeader(500)
	}

	duration := time.Since(start).Seconds()

	// 记录请求计数
	metrics.HttpRequestsTotal.WithLabelValues(
		r.Method,
		"/api/orders",
		fmt.Sprint(w.(*responseWriter).statusCode),
	).Inc()

	// 记录延迟
	metrics.HttpRequestDuration.WithLabelValues(
		r.Method,
		"/api/orders",
	).Observe(duration)

	// 记录业务指标
	metrics.OrdersCreatedTotal.WithLabelValues("success").Inc()
}
```

### 3.7 自定义 Bucket 很重要

默认 Bucket 适合 Web 请求，但对内部 RPC 调用可能不合适：

```go
// 微服务间 RPC 调用一般期望 < 100ms
var RpcDuration = promauto.NewHistogramVec(
	prometheus.HistogramOpts{
		Name: "rpc_call_duration_seconds",
		Help: "RPC call latency in seconds",
		Buckets: []float64{
			0.001, 0.005, // 1ms, 5ms
			0.01, 0.025,  // 10ms, 25ms
			0.05, 0.1,    // 50ms, 100ms
			0.25, 0.5,    // 250ms, 500ms
			1.0, 2.5,     // 1s, 2.5s (超时)
		},
	},
	[]string{"service", "method"},
)

// 数据库查询通常 < 50ms
var DbQueryDuration = promauto.NewHistogramVec(
	prometheus.HistogramOpts{
		Name: "db_query_duration_seconds",
		Help: "Database query latency in seconds",
		Buckets: []float64{
			0.0005, 0.001, 0.005, // 0.5ms, 1ms, 5ms
			0.01, 0.025, 0.05,    // 10ms, 25ms, 50ms
			0.1, 0.25, 0.5, 1.0,  // 慢查询区域
		},
	},
	[]string{"query_type", "table"},
)
```

> **Bucket 选择的黄金法则**：覆盖你关心的延迟范围。少了分不准，多了浪费内存。一般 10-15 个 Bucket 足够了。

---

## 五、三件套整合实战

### 5.1 整体架构

```text
┌──────────────────────────────────────────────────────────────────┐
│                        Go 微服务进程                              │
│                                                                  │
│   ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐ │
│   │   slog / zap │    │  OpenTelemetry   │    │  Prometheus   │ │
│   │   (日志)      │    │  (链路追踪)       │    │  (指标)        │ │
│   └──────┬───────┘    └────────┬─────────┘    └───────┬───────┘ │
│          │                     │                      │         │
│          │ stdout / stderr     │ OTLP (gRPC/HTTP)     │ /metrics│
│          │                     │                      │         │
└──────────┼─────────────────────┼──────────────────────┼─────────┘
           │                     │                      │
           ▼                     ▼                      ▼
    ┌──────────────┐    ┌──────────────┐      ┌──────────────┐
    │ Loki / ELK   │    │ Jaeger/Tempo │      │  Prometheus  │
    │ (日志存储)    │    │ (链路存储)    │      │  (指标存储)   │
    └──────┬───────┘    └──────┬───────┘      └──────┬───────┘
           │                   │                     │
           └───────────────────┼─────────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   Grafana    │
                        │  (统一可视化)  │
                        └──────────────┘
```

### 5.2 基础 HTTP 服务骨架

下面是整合了三件套的完整服务骨架代码。你可以直接在这个基础上开发业务逻辑。

```go
package main

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// ==================== 指标定义 ====================

var (
	httpRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"method", "endpoint", "status"},
	)

	httpRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP request latency in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"method", "endpoint"},
	)

	businessOperationTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "business_operation_total",
			Help: "Total number of business operations",
		},
		[]string{"operation", "status"},
	)
)

// ==================== 中间件：日志 + 指标 + 链路 ====================

func ObservabilityMiddleware(logger *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()

			// 1. 链路追踪：从 context 提取 Span，添加属性
			span := otel.Tracer("http").StartSpan(r.Context(), r.Method+" "+r.URL.Path)
			defer span.End()

			// 2. 日志：为本次请求创建子 logger
			traceID := span.SpanContext().TraceID().String()
			reqLogger := logger.With(
				"trace_id", traceID,
				"method", r.Method,
				"path", r.URL.Path,
			)

			// 注入到 context
			ctx := context.WithValue(r.Context(), "logger", reqLogger)
			r = r.WithContext(ctx)

			// 3. 包装 ResponseWriter，捕获状态码
			wrapped := &responseWriter{ResponseWriter: w, statusCode: 200}
			next.ServeHTTP(wrapped, r)

			// 4. 记录请求完成
			duration := time.Since(start)
			statusStr := fmt.Sprintf("%d", wrapped.statusCode)

			reqLogger.Info("request completed",
				"status", wrapped.statusCode,
				"duration_ms", duration.Milliseconds(),
			)

			span.SetAttributes(
				attribute.Int("http.status_code", wrapped.statusCode),
				attribute.String("http.method", r.Method),
				attribute.String("http.path", r.URL.Path),
			)

			// 5. 指标
			httpRequestsTotal.WithLabelValues(r.Method, r.URL.Path, statusStr).Inc()
			httpRequestDuration.WithLabelValues(r.Method, r.URL.Path).Observe(duration.Seconds())
		})
	}
}

type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

// ==================== 业务 Handler ====================

func GetUserHandler(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	logger := ctx.Value("logger").(*slog.Logger)
	tracer := otel.Tracer("user-service")

	// 手动创建 Span
	_, span := tracer.Start(ctx, "GetUserHandler")
	defer span.End()

	userID := r.PathValue("id")
	logger.Info("fetching user", "user_id", userID)

	// 模拟数据库查询
	time.Sleep(30 * time.Millisecond)

	// 记录业务指标
	businessOperationTotal.WithLabelValues("get_user", "success").Inc()

	span.SetStatus(codes.Ok, "user fetched")
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"id":"` + userID + `","name":"mife","email":"mife@example.com"}`))
}

func CreateOrderHandler(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	logger := ctx.Value("logger").(*slog.Logger)
	tracer := otel.Tracer("order-service")

	ctx, span := tracer.Start(ctx, "CreateOrderHandler")
	defer span.End()

	orderID := fmt.Sprintf("ord_%d", time.Now().Unix())
	logger.Info("creating order", "order_id", orderID)

	// 模拟检查库存
	if err := checkStock(ctx, orderID); err != nil {
		logger.Error("stock check failed", "order_id", orderID, "error", err)
		businessOperationTotal.WithLabelValues("create_order", "failed").Inc()
		span.RecordError(err)
		span.SetStatus(codes.Error, "insufficient stock")
		http.Error(w, `{"error":"insufficient stock"}`, 500)
		return
	}

	businessOperationTotal.WithLabelValues("create_order", "success").Inc()
	span.SetStatus(codes.Ok, "order created")
	w.WriteHeader(201)
	w.Write([]byte(`{"order_id":"` + orderID + `","status":"created"}`))
}

func checkStock(ctx context.Context, orderID string) error {
	tracer := otel.Tracer("order-service")
	_, span := tracer.Start(ctx, "checkStock")
	defer span.End()

	time.Sleep(20 * time.Millisecond)
	return nil
}

// ==================== main ====================

func main() {
	// 日志
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	// 链路追踪 — 这里用控制台输出，生产环境改成 Jaeger/Tempo 地址
	tp, err := initTracer("demo-service", "")
	if err != nil {
		logger.Error("init tracer failed", "error", err)
		os.Exit(1)
	}
	defer tp.Shutdown(context.Background())

	// 路由
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/users/{id}", GetUserHandler)
	mux.HandleFunc("POST /api/orders", CreateOrderHandler)
	mux.Handle("/metrics", promhttp.Handler()) // Prometheus 抓取端点

	// 链路追踪自动埋点
	otelHandler := otelhttp.NewHandler(mux, "demo-service")

	// 日志+指标中间件
	handler := ObservabilityMiddleware(logger)(otelHandler)

	server := &http.Server{
		Addr:    ":8080",
		Handler: handler,
	}

	// 优雅关闭
	go func() {
		logger.Info("server starting", "addr", ":8080")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("server error", "error", err)
			os.Exit(1)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("server shutting down")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	server.Shutdown(ctx)
}
```

### 5.3 完整的 Tracer 初始化（initTracer）

```go
package main

import (
	"context"
	"fmt"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/stdout/stdouttrace"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

func initTracer(serviceName, otlpEndpoint string) (*sdktrace.TracerProvider, error) {
	// 导出器：开发用 stdout，生产用 OTLP
	exporter, err := stdouttrace.New(stdouttrace.WithPrettyPrint())
	if err != nil {
		return nil, fmt.Errorf("create stdout exporter: %w", err)
	}

	res, err := resource.New(context.Background(),
		resource.WithAttributes(
			semconv.ServiceName(serviceName),
			semconv.ServiceVersion("v1.0.0"),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("create resource: %w", err)
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)

	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	return tp, nil
}
```

### 5.4 使用 zap 替换 slog 的版本

如果你选择 zap，只需替换日志部分：

```go
func ObservabilityMiddlewareWithZap(logger *zap.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()

			span := otel.Tracer("http").StartSpan(r.Context(), r.Method+" "+r.URL.Path)
			defer span.End()

			traceID := span.SpanContext().TraceID().String()
			reqLogger := logger.With(
				zap.String("trace_id", traceID),
				zap.String("method", r.Method),
				zap.String("path", r.URL.Path),
			)

			ctx := context.WithValue(r.Context(), "logger", reqLogger)
			r = r.WithContext(ctx)

			wrapped := &responseWriter{ResponseWriter: w, statusCode: 200}
			next.ServeHTTP(wrapped, r)

			duration := time.Since(start)

			reqLogger.Info("request completed",
				zap.Int("status", wrapped.statusCode),
				zap.Duration("duration", duration),
			)

			span.SetAttributes(
				attribute.Int("http.status_code", wrapped.statusCode),
			)

			httpRequestsTotal.WithLabelValues(r.Method, r.URL.Path, fmt.Sprint(wrapped.statusCode)).Inc()
			httpRequestDuration.WithLabelValues(r.Method, r.URL.Path).Observe(duration.Seconds())
		})
	}
}
```

### 5.5 运行和验证

```bash
# 启动服务
go run main.go

# 另一个终端：发几个请求
curl http://localhost:8080/api/users/123
curl -X POST http://localhost:8080/api/orders
curl http://localhost:8080/metrics
```

控制台输出示例（slog JSON + OTel stdout）：

```json
{"time":"2026-06-07T10:30:15Z","level":"INFO","msg":"server starting","addr":":8080"}
{"time":"2026-06-07T10:30:20Z","level":"INFO","msg":"fetching user","trace_id":"a1b2c3...","user_id":"123","method":"GET","path":"/api/users/123"}
{
    "Name": "GET /api/users/{id}",
    "SpanContext": {
        "TraceID": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        "SpanID": "1a2b3c4d5e6f7a8b"
    },
    "Parent": {"TraceID": "...", "SpanID": "..."},
    "SpanKind": 2,
    "StartTime": "2026-06-07T10:30:20.123Z",
    "EndTime": "2026-06-07T10:30:20.153Z",
    "Attributes": [
        {"Key": "http.status_code", "Value": {"Type": "INT64", "Value": 200}}
    ],
    "Status": {"Code": "Ok"}
}
```

`/metrics` 端点输出：

```text
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/api/users/{id}",method="GET",status="200"} 1
http_requests_total{endpoint="/api/orders",method="POST",status="201"} 1
# HELP http_request_duration_seconds HTTP request latency in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/api/users/{id}",method="GET",le="0.005"} 0
http_request_duration_seconds_bucket{endpoint="/api/users/{id}",method="GET",le="0.01"} 0
http_request_duration_seconds_bucket{endpoint="/api/users/{id}",method="GET",le="0.025"} 0
http_request_duration_seconds_bucket{endpoint="/api/users/{id}",method="GET",le="0.05"} 1
...
```

---

## 六、Grafana 可视化配置

### 6.1 核心 Grafana 面板

有了三件套数据后，在 Grafana 中你可以创建以下面板：

**指标面板 — PromQL 示例：**

```promql
# QPS（每秒请求数）
rate(http_requests_total[1m])

# P99 延迟（使用 Histogram）
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[1m]))

# 错误率
sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))

# 服务可用性（SLI）
(sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100
```

**日志面板 — LogQL 示例（配合 Loki）：**

```logql
{service="order-service"} |= "error"
{service="order-service"} | json | trace_id="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
```

> 这里的 `trace_id` 正是你在代码的 `logger.With("trace_id", traceID)` 中注入的字段。在日志中找到错误后，可以用 `trace_id` 跳到 Jaeger/Tempo 查看完整链路。

### 6.2 推荐的 Grafana Dashboard 布局

```text
┌─────────────────────────────────────────────────────┐
│  Row 1: 概览                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │  QPS      │ │  P99 延迟 │ │  错误率   │ │  可用性  │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
├─────────────────────────────────────────────────────┤
│  Row 2: 延迟详情                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │         延迟热力图 (Heatmap)                    │    │
│  └──────────────────────────────────────────────┘    │
│  ┌──────────────────┐ ┌──────────────────────┐       │
│  │  P50/P90/P99 折线 │ │  各端点延迟对比       │       │
│  └──────────────────┘ └──────────────────────┘       │
├─────────────────────────────────────────────────────┤
│  Row 3: 日志                                          │
│  ┌──────────────────────────────────────────────┐    │
│  │         日志面板（Loki，可点击 trace_id 跳转）  │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## 七、Docker Compose 一键部署

前面写了那么多代码，但如果没有后端存储，日志写到 stdout 就丢了，链路追踪也只在控制台打印。这一节用 Docker Compose 把全套基础设施跑起来。

### 7.1 整体部署架构

```text
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network: observability            │
│                                                             │
│  ┌──────────────┐                                           │
│  │ Go 微服务      │  本机开发时直接 go run，部署时也打包进 compose│
│  │ :8080         │                                           │
│  │ /metrics      │── Prometheus 抓取 ────────────────────┐   │
│  │ OTLP gRPC ────┼──► otel-collector:4317 ──► Jaeger    │   │
│  │ stdout log ───┼──► Promtail(loki:9080) ──► Loki      │   │
│  └──────────────┘                                         │   │
│                                                           │   │
│  ┌──────────────────┐  ┌──────────────────┐               │   │
│  │ Otel Collector   │  │ Jaeger           │               │   │
│  │ :4317 (OTLP)     │  │ :16686 (UI)      │               │   │
│  │ :8888 (metrics)  │  │ :14250 (OTLP)    │               │   │
│  └──────────────────┘  └──────────────────┘               │   │
│                                                           │   │
│  ┌──────────────────┐  ┌──────────────────┐               │   │
│  │ Prometheus       │  │ Loki             │               │   │
│  │ :9090 (UI)       │  │ :3100 (API)      │               │   │
│  └──────────────────┘  └──────────────────┘               │   │
│                                                           │   │
│  ┌──────────────────┐  ┌──────────────────┐               │   │
│  │ Promtail         │  │ Grafana          │               │   │
│  │ :9080 (API)      │  │ :3000 (UI)       │               │   │
│  └──────────────────┘  └──────────────────┘               │   │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 docker-compose.yml

在项目根目录创建 `docker-compose.observability.yml`：

```yaml
version: "3.8"

services:
  # ==================== 链路追踪：OpenTelemetry Collector ====================
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.120.0
    container_name: otel-collector
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC（Go 服务发送 Trace 的入口）
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Collector 自身的 metrics
    depends_on:
      - jaeger
    networks:
      - observability

  # ==================== 链路追踪存储：Jaeger ====================
  jaeger:
    image: jaegertracing/all-in-one:1.66
    container_name: jaeger
    environment:
      - COLLECTOR_OTLP_ENABLED=true   # 开启 OTLP 接收（兼容 OpenTelemetry）
      - SPAN_STORAGE_TYPE=badger       # 本地存储（生产环境改用 ES/Cassandra）
      - BADGER_EPHEMERAL=false
      - BADGER_DIRECTORY_VALUE=/badger/data
      - BADGER_DIRECTORY_KEY=/badger/key
    volumes:
      - jaeger_data:/badger
    ports:
      - "16686:16686"  # Jaeger UI: http://localhost:16686
      - "14250:14250"  # OTLP gRPC（Otel Collector → Jaeger）
    networks:
      - observability

  # ==================== 指标存储：Prometheus ====================
  prometheus:
    image: prom/prometheus:v3.2
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=15d"     # 数据保留 15 天
      - "--web.enable-admin-api"
    ports:
      - "9090:9090"   # Prometheus UI: http://localhost:9090
    networks:
      - observability

  # ==================== 日志聚合：Loki ====================
  loki:
    image: grafana/loki:3.4
    container_name: loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"   # Loki API
    volumes:
      - loki_data:/loki
    networks:
      - observability

  # ==================== 日志采集：Promtail ====================
  promtail:
    image: grafana/promtail:3.4
    container_name: promtail
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml
      # 挂载 Docker 日志目录，采集容器 stdout
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki
    networks:
      - observability

  # ==================== 统一可视化：Grafana ====================
  grafana:
    image: grafana/grafana:11.6
    container_name: grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin    # 生产环境务必修改
      - GF_INSTALL_PLUGINS=                  # 不自动装插件，加快启动
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"   # Grafana UI: http://localhost:3000
    depends_on:
      - prometheus
      - loki
    networks:
      - observability

volumes:
  jaeger_data:
  prometheus_data:
  loki_data:
  grafana_data:

networks:
  observability:
    driver: bridge
```

### 7.3 OpenTelemetry Collector 配置

创建 `otel-collector-config.yaml`：

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317   # 接收 Go 服务发来的 Trace
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  # 生产环境可选：基于概率的尾部采样
  # tail_sampling:
  #   policies:
  #     - name: error-policy
  #       type: status_code
  #       status_code: { status_codes: [ERROR] }
  #     - name: probabilistic
  #       type: probabilistic
  #       probabilistic: { sampling_percentage: 10 }

exporters:
  # 导出到 Jaeger
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

  # 调试用：打印到 Collector 控制台（开发调试用）
  debug:
    verbosity: basic

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/jaeger, debug]
```

> **关键流程**：Go 服务 → OTLP gRPC `:4317` → Otel Collector（批处理） → Jaeger `:4317`。Collector 在中间做缓冲和路由，避免 Go 服务直接连 Jaeger 造成耦合。

### 7.4 Prometheus 配置

创建 `prometheus.yml`：

```yaml
global:
  scrape_interval: 15s       # 抓取间隔
  evaluation_interval: 15s   # 告警规则评估间隔

scrape_configs:
  # 抓取 Go 微服务的 /metrics
  - job_name: "go-microservice"
    static_configs:
      # host.docker.internal 是 Docker Desktop 访问宿主机的特殊地址
      # Linux 下需改为 172.17.0.1 或 host 网络模式
      - targets: ["host.docker.internal:8080"]
        labels:
          service: "demo-service"
          env: "development"

  # 抓取 Otel Collector 自身的指标
  - job_name: "otel-collector"
    static_configs:
      - targets: ["otel-collector:8888"]
```

### 7.5 Promtail 配置

创建 `promtail-config.yml`：

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # 采集 Docker 容器的 stdout 日志
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      # 用容器名作为 service 标签
      - source_labels: ["__meta_docker_container_name"]
        regex: "/(.*)"
        target_label: "container"
      # 只采集特定容器（可选，不设则采集全部）
      # - source_labels: ["__meta_docker_container_name"]
      #   regex: "/go-.*"
      #   action: keep
    pipeline_stages:
      # 如果日志是 JSON（slog/zap JSON 输出），自动解析字段
      - json:
          expressions:
            time: time
            level: level
            msg: msg
            trace_id: trace_id
      # 用解析出的时间作为日志时间戳
      - timestamp:
          source: time
          format: RFC3339
      # 用 level 字段派生 Loki 标签（可用于 LogQL 过滤）
      - labels:
          level: ""
          trace_id: ""
```

### 7.6 启动与验证

```bash
# 1. 启动所有基础设施
docker compose -f docker-compose.observability.yml up -d

# 2. 检查所有服务状态
docker compose -f docker-compose.observability.yml ps

# 3. 确保 Go 微服务已经启动（监听 :8080），然后发请求
curl http://localhost:8080/api/users/123
curl -X POST http://localhost:8080/api/orders
curl http://localhost:8080/api/orders
curl -X POST http://localhost:8080/api/orders
```

访问各组件 UI：

| 组件 | 地址 | 用途 |
|------|------|------|
| **Jaeger** | http://localhost:16686 | 搜索 Trace，查看调用链火焰图 |
| **Prometheus** | http://localhost:9090 | 查询指标，执行 PromQL |
| **Grafana** | http://localhost:3000 | 统一 Dashboard（登录 admin/admin） |
| **Loki** | http://localhost:3100/ready | 通过 Grafana 内 Data Source 访问 |

### 7.7 Jaeger 中查看链路

1. 打开 http://localhost:16686
2. Service 下拉选择 `demo-service`
3. 点击 **Find Traces**
4. 点击任意一条 Trace，你会看到类似：

```text
┌────────────────────────────────────────────────────────────┐
│ Trace: a1b2c3d4e5f6...  │  Duration: 62ms  │  Spans: 4    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  demo-service (50ms)                                       │
│  ├── GET /api/users/{id} (48ms)  ◄── otelhttp 自动创建      │
│  │   └── GetUserHandler (30ms)    ◄── 手动 Span             │
│  └── POST /api/orders (10ms)                               │
│      └── CreateOrderHandler (8ms)                           │
│          └── checkStock (5ms)                               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

每个 Span 可展开查看属性（`http.status_code`、`order.id` 等）和耗时。

### 7.8 Grafana 配置数据源与 Dashboard

**第一步：添加数据源**

Grafana 启动后，进入 **Connections → Data sources**：

- **Prometheus**：URL 填 `http://prometheus:9090`，点 Save & test
- **Loki**：URL 填 `http://loki:3100`，点 Save & test
- **Jaeger**：URL 填 `http://jaeger:16686`，点 Save & test

**第二步：在 Explore 中验证数据**

- 切换到 **Prometheus** 数据源，输入 `rate(http_requests_total[1m])`，应该能看到曲线
- 切换到 **Loki** 数据源，输入 `{container=~".*demo.*"} |= "error"`，应该能看到日志
- 切换到 **Jaeger** 数据源，搜索 Service `demo-service`，应该能看到 Trace

**第三步：创建统一 Dashboard**

关键技巧 — **让日志可以跳转到链路**：在 Loki 日志面板中，配置 `trace_id` 字段为 Data Link，点击后自动跳转 Jaeger 搜索对应 Trace。

在 Grafana 的 Loki Panel 中配置：

```text
Data link:
  URL: http://localhost:16686/trace/${__value.raw}
  （如果使用 Tempo 则: /explore?orgId=1&left={"queries":[{"refId":"A","query":"${__value.raw}"}]}）
```

这样流程就通了：**看到告警 → 打开 Grafana 看指标 → 发现有错误 → 切到日志面板搜 ERROR → 点击 trace_id 跳转到 Jaeger → 看完整调用链定位根因**。

---

## 八、生产环境注意事项

### 8.1 采样策略

全量采样在 QPS 很高时会消耗大量资源。生产环境应该做采样：

```go
// 按比例采样：保留 10% 的 Trace
sdktrace.WithSampler(sdktrace.TraceIDRatioBased(0.1))

// 父 Span 决定子 Span 采样（推荐）：保证同一 Trace 的 Span 全部或全不采样
sdktrace.WithSampler(sdktrace.ParentBased(
    sdktrace.TraceIDRatioBased(0.1),
))
```

### 8.2 日志级别控制

```go
// 通过环境变量控制日志级别
func getLogLevel() slog.Level {
	switch os.Getenv("LOG_LEVEL") {
	case "DEBUG":
		return slog.LevelDebug
	case "WARN":
		return slog.LevelWarn
	case "ERROR":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}
```

### 8.3 避免指标基数爆炸

```go
// ❌ 危险：用 userId 作为标签，用户多了指标数爆炸
counter.WithLabelValues(method, endpoint, userId).Inc()

// ✅ 正确：标签值集合应有限且可预测
counter.WithLabelValues(method, endpoint, statusCode).Inc()
```

> **规则**：标签的基数（不同取值的组合数）应该有限。HTTP 方法 × 端点 × 状态码 是有限的；用户 ID、订单 ID 是无限的，绝对不能作为标签。

### 8.4 优雅关闭

确保进程退出前刷新日志缓冲和导出未发送的 Span：

```go
func shutdown(logger *zap.Logger, tp *sdktrace.TracerProvider) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	logger.Info("flushing traces...")
	if err := tp.Shutdown(ctx); err != nil {
		logger.Error("trace shutdown failed", zap.Error(err))
	}

	logger.Info("flushing logs...")
	logger.Sync() // zap 需要手动 Sync
}
```

---

## 九、总结

本文覆盖了 Go 微服务治理三件套的完整实现：

| 组件 | 库 | 核心操作 |
|------|-----|----------|
| 日志 | `slog` / `zap` | 结构化输出 + trace_id 关联 + 中间件注入 |
| 链路 | OpenTelemetry | 自动 HTTP 埋点 + 手动 Span + W3C 传播 |
| 指标 | Prometheus client | Counter / Histogram / Gauge + `/metrics` 端点 |

**三件套串联的关键是 `trace_id`**：日志中带上，链路中贯穿，指标中关联 —— 三者打通后，你可以在 Grafana 中从告警→指标→日志→链路一路点下去，秒级定位问题。

最后记住三个原则：

1. **日志要结构化**：JSON 输出，key=value，别用字符串拼接
2. **指标标签要有限**：只用于聚合维度，别把用户 ID 当标签
3. **链路要适度**：http/db 调用自动埋，关键业务逻辑手动埋，别每行代码都包 Span

---

> 本文基于以下库版本编写：Go 1.24、OpenTelemetry Go SDK v1.x、prometheus/client_golang v1.x、zap v1.x。如有问题或建议，欢迎联系[邮箱](mailto:15723556393@163.com)。
