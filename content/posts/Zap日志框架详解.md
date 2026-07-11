---
title: 'Zap日志框架详解：高性能结构化日志的配置、接口与实战'
date: 2026-07-10T16:00:00+08:00
draft: false
tags: ["Go", "zap", "日志", "结构化日志", "高性能", "slog"]
---

Zap 是 Uber 开源的高性能结构化日志库。它的核心卖点是：零内存分配（zero-allocation）的日志热路径、纳秒级的字段编码、以及灵活的配置体系。

## 一、为什么要用 Zap

`log` 标准库功能太基础，`log/slog` 到 Go 1.21 才加入。在有 slog 之前，Go 社区有三家主流日志库：

| 库 | 作者 | 特点 |
|----|------|------|
| logrus | sirupsen | 易用，功能全，但性能一般（反射） |
| zerolog | rs | 零分配，速度快，API 是链式调用 |
| zap | Uber | 零分配，速度快，API 是方法调用 |

三者的性能差距（在基准测试中大致是）：zap ≈ zerolog >> logrus。logrus 的反射开销在高 QPS 场景下会成为瓶颈。

Go 1.21 引入的标准库 `log/slog` 在易用性和标准库集成上更好，但 Zap 仍有几个关键优势：

- **更精细的分配控制**：Zap 的 `Field` 类型可以预分配并复用，slog 的 `Attr` 同类。但 Zap 的 `zapcore.Encoder` 接口允许你深度定制序列化格式，slog 做不到。
- **更灵活的采样机制**：Zap 内置了按时间、按数量、按日志级别组合的采样 hook，slog 需要自己实现 Handler。
- **生态成熟度**：大量现有项目深度集成 Zap（Gin、Echo、GORM 等框架都有 zap adapter）。

---

## 二、安装与快速开始

```bash
go get -u go.uber.org/zap
```

30 秒上手：

```go
package main

import "go.uber.org/zap"

func main() {
    // 生产环境用 NewProduction
    logger, _ := zap.NewProduction()
    defer logger.Sync() // 刷新缓冲，确保退出前所有日志写入

    logger.Info("server started",
        zap.String("addr", ":8080"),
        zap.Int("workers", 4),
    )
    // {"level":"info","ts":1752148800.123456,"caller":"main/main.go:10","msg":"server started","addr":":8080","workers":4}
}
```

`logger.Sync()` 很重要。Zap 内部用 `bufio.Writer` 包裹 `os.Stdout`，进程退出时如果没调 `Sync()`，缓冲区的日志会丢失。典型做法是：

```go
func main() {
    logger, _ := zap.NewProduction()
    defer func() {
        if err := logger.Sync(); err != nil {
            // Sync 在 stdout/stderr 上可能返回 "invalid argument"（Linux 的 sync 到非文件描述符的错误），可以安全忽略
            // 但如果是写文件，这个错误必须处理
            fmt.Fprintf(os.Stderr, "sync log: %v\n", err)
        }
    }()
    // 业务逻辑...
}
```

---

## 三、架构设计：Logger、SugaredLogger、Core

Zap 的内部设计分三层：

```text
┌──────────────────────────────────────┐
│             SugaredLogger             │  ← 便利层：接受 interface{}，用反射
│  Infow("msg", "key", val)            │     额外分配 2-3 个小对象
├──────────────────────────────────────┤
│               Logger                  │  ← 高性能层：只接受 zap.Field 类型
│  Info("msg", zap.String("k","v"))     │     零堆分配（字段值会逃逸除外）
├──────────────────────────────────────┤
│                Core                   │  ← 编码层：Encoder + WriteSyncer + Level
│  zapcore.NewCore(enc, ws, level)     │
└──────────────────────────────────────┘
```

### 3.1 Logger vs SugaredLogger

```go
// Logger：强类型，高性能，略啰嗦
logger.Info("user login",
    zap.String("username", "alice"),
    zap.Int("attempt", 3),
    zap.Duration("latency", 50*time.Millisecond),
    zap.Bool("success", true),
)

// SugaredLogger：宽松类型，方便，有反射开销
sugar := logger.Sugar()
sugar.Infow("user login",
    "username", "alice",
    "attempt", 3,
    "latency", 50*time.Millisecond,
    "success", true,
)
```

什么时候该用哪个：

- **热路径**（每个请求都打的日志）：用 `Logger` + 强类型 Field
- **冷路径**（错误日志、初始化日志、调试日志）：用 `SugaredLogger`，省代码
- **不确定**：先用 `SugaredLogger` 写对，profile 后发现是瓶颈再切到 `Logger`

`SugaredLogger` 的转换开销大约是纳秒级，对于每秒百万 QPS 以下的服务基本感觉不到。

### 3.2 Core 的组装

```go
import "go.uber.org/zap/zapcore"

// Core = Encoder + WriteSyncer + LevelEnabler
core := zapcore.NewCore(
    zapcore.NewJSONEncoder(zap.NewProductionEncoderConfig()),  // 编码器
    zapcore.AddSync(os.Stdout),                                 // 写入目标
    zapcore.InfoLevel,                                         // 最低级别
)

logger := zap.New(core)
```

你可以组合多个 Core，让不同的日志级别写到不同的目标：

```go
// 所有日志输出到 stdout
consoleCore := zapcore.NewCore(
    zapcore.NewConsoleEncoder(zap.NewDevelopmentEncoderConfig()),
    zapcore.AddSync(os.Stdout),
    zapcore.DebugLevel,
)

// Error 及以上写入文件
f, _ := os.Create("error.log")
errorCore := zapcore.NewCore(
    zapcore.NewJSONEncoder(zap.NewProductionEncoderConfig()),
    zapcore.AddSync(f),
    zapcore.ErrorLevel, // 只接受 Error 及以上
)

// 组合（Tee 模式）
core := zapcore.NewTee(consoleCore, errorCore)
logger := zap.New(core)
```

`zapcore.NewTee` 把多个 Core 组合成一个——每条日志如果通过某个 Core 的 LevelEnabler 检查，就用该 Core 的 Encoder 编码后写入该 Core 的 WriteSyncer。

---

## 四、Preset 配置：Development vs Production

Zap 提供了两个预设：

```go
// Production 预设
logger, _ := zap.NewProduction()
// - JSON 格式
// - 日志级别: InfoLevel
// - 调用位置: caller 字段
// - 堆栈跟踪: ErrorLevel 及以上
// - 时间格式: Epoch time (浮点秒)
// - 采样: 开启（相同级别+消息在 1 秒内重复 >100 次时丢弃）

// Development 预设
logger, _ := zap.NewDevelopment()
// - Console 格式（人类友好，带颜色）
// - 日志级别: DebugLevel
// - 调用位置: caller 字段
// - 堆栈跟踪: WarnLevel 及以上
// - 时间格式: ISO8601
// - 采样: 关闭
```

两个预设对应的 `EncoderConfig` 源码：

```go
// zap.NewProductionEncoderConfig() 大致等价于：
zapcore.EncoderConfig{
    TimeKey:        "ts",
    LevelKey:       "level",
    NameKey:        "logger",
    CallerKey:      "caller",
    FunctionKey:    zapcore.OmitKey,
    MessageKey:     "msg",
    StacktraceKey:  "stacktrace",
    LineEnding:     zapcore.DefaultLineEnding,
    EncodeLevel:    zapcore.LowercaseLevelEncoder,
    EncodeTime:     zapcore.EpochTimeEncoder,
    EncodeDuration: zapcore.SecondsDurationEncoder,
    EncodeCaller:   zapcore.ShortCallerEncoder,
}

// zap.NewDevelopmentEncoderConfig() 大致等价于：
zapcore.EncoderConfig{
    TimeKey:        "T",
    LevelKey:       "L",
    NameKey:        "N",
    CallerKey:      "C",
    FunctionKey:    zapcore.OmitKey,
    MessageKey:     "M",
    StacktraceKey:  "S",
    LineEnding:     zapcore.DefaultLineEnding,
    EncodeLevel:    zapcore.CapitalColorLevelEncoder, // 带 ANSI 颜色
    EncodeTime:     zapcore.ISO8601TimeEncoder,
    EncodeDuration: zapcore.StringDurationEncoder,
    EncodeCaller:   zapcore.ShortCallerEncoder,
}
```

> ⚠️ `FunctionKey` 设为 `zapcore.OmitKey` 意味着不记录调用函数名。如果设为一个字符串（如 `"func"`），每条日志都会包含函数名，但查找函数名需要走调用栈，有不可忽略的性能开销。生产环境通常不开启。

---

## 五、自定义配置

预设只是起点。生产环境你需要精确控制配置：

```go
func NewLogger(level string, format string, outputPaths []string) (*zap.Logger, error) {
    // 1. 解析日志级别
    var zapLevel zapcore.Level
    if err := zapLevel.UnmarshalText([]byte(level)); err != nil {
        return nil, fmt.Errorf("invalid log level %q: %w", level, err)
    }

    // 2. 编码器配置
    encoderCfg := zapcore.EncoderConfig{
        TimeKey:        "timestamp",
        LevelKey:       "level",
        NameKey:        "logger",
        CallerKey:      "caller",
        FunctionKey:    zapcore.OmitKey,
        MessageKey:     "message",
        StacktraceKey:  "stacktrace",
        LineEnding:     zapcore.DefaultLineEnding,
        EncodeLevel:    zapcore.LowercaseLevelEncoder,
        EncodeTime:     zapcore.RFC3339TimeEncoder,  // 人类可读的 ISO8601
        EncodeDuration: zapcore.MillisDurationEncoder, // 毫秒
        EncodeCaller:   zapcore.ShortCallerEncoder,    // package/file:line
    }

    // 3. 选择编码格式
    var encoder zapcore.Encoder
    switch format {
    case "json":
        encoder = zapcore.NewJSONEncoder(encoderCfg)
    case "console":
        encoder = zapcore.NewConsoleEncoder(encoderCfg)
    default:
        return nil, fmt.Errorf("unknown format %q", format)
    }

    // 4. 组装 WriteSyncer
    var writers []zapcore.WriteSyncer
    for _, path := range outputPaths {
        switch path {
        case "stdout":
            writers = append(writers, zapcore.AddSync(os.Stdout))
        case "stderr":
            writers = append(writers, zapcore.AddSync(os.Stderr))
        default:
            f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
            if err != nil {
                return nil, fmt.Errorf("open log file %q: %w", path, err)
            }
            writers = append(writers, zapcore.AddSync(f))
        }
    }
    ws := zapcore.NewMultiWriteSyncer(writers...)

    // 5. 创建 Logger
    core := zapcore.NewCore(encoder, ws, zapLevel)
    logger := zap.New(core,
        zap.AddCaller(),                          // 添加调用位置
        zap.AddCallerSkip(1),                     // 如果你的日志调用封装了一层
        zap.AddStacktrace(zapcore.ErrorLevel),    // Error 级别自动附调用栈
    )

    return logger, nil
}
```

使用方式：

```go
logger, _ := NewLogger("debug", "json", []string{"stdout", "/var/log/app.log"})
logger.Info("server started", zap.Int("port", 8080))
// stdout 和 /var/log/app.log 都会收到同一行 JSON
```

### 5.1 EncoderConfig 关键字段

| 字段 | 作用 | 设为 OmitKey 的效果 |
|------|------|-------------------|
| `TimeKey` | 时间戳的 key | 不输出时间戳（测试用） |
| `LevelKey` | 级别的 key | 不输出级别 |
| `CallerKey` | 调用位置的 key | 不输出调用位置 |
| `FunctionKey` | 函数名的 key | 不输出函数名 |
| `StacktraceKey` | 堆栈的 key | 不输出堆栈 |

### 5.2 Encoder 类型对比

```go
// JSON Encoder 输出
// {"timestamp":"2026-07-10T15:00:00Z","level":"info","message":"hello","key":"value"}

// Console Encoder 输出
// 2026-07-10T15:00:00.000Z	INFO	hello	{"key": "value"}
```

Console Encoder 的格式是 `时间\t级别\t消息\t{字段JSON}`，字段部分仍然是 JSON。这是为了在终端可读的同时保留结构化数据。如果不用字段，输出就是干净的：

```go
logger.Info("server started")
// 2026-07-10T15:00:00.000Z	INFO	server started
```

### 5.3 时间格式

```go
zapcore.EpochTimeEncoder         // 1752148800.123456
zapcore.EpochMillisTimeEncoder   // 1752148800123
zapcore.EpochNanosTimeEncoder    // 1752148800123456789
zapcore.ISO8601TimeEncoder       // 2026-07-10T15:00:00.000Z
zapcore.RFC3339TimeEncoder       // 2026-07-10T15:00:00Z
zapcore.RFC3339NanoTimeEncoder   // 2026-07-10T15:00:00.000000000Z

// 自定义
EncodeTime: func(t time.Time, enc zapcore.PrimitiveArrayEncoder) {
    enc.AppendString(t.Format("2006-01-02 15:04:05.000"))
}
```

> ⚠️ 如果日志会被 Loki 或 Elasticsearch 索引，用 `RFC3339NanoTimeEncoder`——这些系统默认能解析 ISO8601/RFC3339，不需要额外配置时间格式。

### 5.4 调用者位置

```go
zapcore.ShortCallerEncoder // service/main.go:42
zapcore.FullCallerEncoder // /home/user/project/service/main.go:42

// 自定义：只输出 package/file:line
EncodeCaller: func(caller zapcore.EntryCaller, enc zapcore.PrimitiveArrayEncoder) {
    _, file := filepath.Split(caller.File)
    enc.AppendString(fmt.Sprintf("%s:%d", file, caller.Line))
}
```

---

## 六、Field 类型速查

Zap 为每个 Go 基本类型提供了专门的 Field 构造函数，避免 `interface{}` 装箱带来的堆分配：

```go
// 基本类型
zap.String("key", "value")
zap.Int("key", 42)
zap.Int64("key", int64(42))
zap.Float64("key", 3.14)
zap.Bool("key", true)

// 错误（注意：不是 Errorf）
zap.Error(err)

// 时间
zap.Time("key", time.Now())
zap.Duration("key", time.Second*5)

// 复合类型
zap.Strings("tags", []string{"go", "web"})
zap.Ints("ids", []int{1, 2, 3})

// 嵌套对象（序列化为 JSON 子对象）
zap.Object("user", &User{Name: "alice", Age: 30})          // 需要实现 zapcore.ObjectMarshaler
zap.Any("metadata", map[string]interface{}{"k": "v"})      // 反射，有分配开销

// 二进制数据（base64 编码）
zap.Binary("payload", []byte{0x00, 0xFF})

// 命名空间：给后续字段包一层嵌套对象
zap.Namespace("server")  // 后续字段全部归入 "server" 子对象
```

### 6.1 实现 ObjectMarshaler

```go
type User struct {
    Name string
    Age  int
}

func (u *User) MarshalLogObject(enc zapcore.ObjectEncoder) error {
    enc.AddString("name", u.Name)
    enc.AddInt("age", u.Age)
    return nil
}

logger.Info("user created", zap.Object("user", &User{"alice", 30}))
// {"level":"info","msg":"user created","user":{"name":"alice","age":30}}
```

### 6.2 实现 ArrayMarshaler

```go
type Users []User

func (users Users) MarshalLogArray(enc zapcore.ArrayEncoder) error {
    for _, u := range users {
        if err := enc.AppendObject(&u); err != nil {
            return err
        }
    }
    return nil
}

logger.Info("batch result", zap.Array("users", Users{{"a", 1}, {"b", 2}}))
```

### 6.3 避免 Any 的堆分配

`zap.Any` 在内部对值做 `interface{}` 装箱，导致堆分配。高频日志路径上应该避免：

```go
// 不好：每个请求都分配
logger.Info("request", zap.Any("headers", req.Header)) // map 装箱到 interface{}

// 好：提前提取需要的字段
logger.Info("request",
    zap.String("method", req.Method),
    zap.String("path", req.URL.Path),
    zap.String("user_agent", req.UserAgent()),
    zap.Int64("content_length", req.ContentLength),
)
```

---

## 七、日志级别

Zap 定义了 6 个级别（从低到高）：

```go
const (
    DebugLevel  Level = iota - 1 // -1
    InfoLevel                     // 0
    WarnLevel                     // 1
    ErrorLevel                    // 2
    DPanicLevel                   // 3 (Development 模式 panic，Production 模式 Fatal)
    PanicLevel                    // 4
    FatalLevel                    // 5
)
```

```go
logger.Debug("verbose detail")    // 调试信息
logger.Info("server started")     // 正常运行时信息
logger.Warn("retry exhausted")    // 潜在问题
logger.Error("db connection lost")// 错误但服务继续运行
// logger.Panic("unrecoverable")  // panic 后 recover
// logger.Fatal("cannot start")   // os.Exit(1)，defer 不会执行
```

多一条关于 `Fatal` 的行为说明：

```go
logger.Fatal("cannot open config file")
// 内部调用 os.Exit(1)
// ⚠️ defer 不会执行！已缓冲的日志也可能丢失！
// 如果一定要在 main 中 Fatal，确保在此之前调了 Sync()
```

> ⚠️ `Fatal` 不会执行 `defer`，也不会 flush 缓冲区。所以如果你把日志写入了文件，`Fatal` 执行时可能导致最后几行日志丢失。通常 `Fatal` 应该只在 `main()` 函数中使用，避免在库代码或请求处理中使用。库代码应该 return error 让调用者决定是否退出。

---

## 八、Logger 复用与 Context 集成

### 8.1 预填充字段

```go
// 创建带固定字段的子 Logger（0 分配，字段被复制到 Core 中）
requestLogger := logger.With(
    zap.String("service", "user-api"),
    zap.String("env", "production"),
)
requestLogger.Info("handling request") // 自动带 service 和 env 字段
```

`With` 方法返回一个新的 `Logger`，它的 `Core` 会预填充这些字段。这条日志的每个后续调用都不需要重新序列化 `service` 和 `env`。

### 8.2 从 context 提取 trace 信息

```go
// 在中间件中创建带 trace_id 的 logger
func LoggingMiddleware(logger *zap.Logger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            traceID := r.Header.Get("X-Trace-Id")
            if traceID == "" {
                traceID = uuid.New().String()
            }
            // 为这个请求创建专用 Logger
            reqLogger := logger.With(
                zap.String("trace_id", traceID),
                zap.String("method", r.Method),
                zap.String("path", r.URL.Path),
            )
            // 注入到 context
            ctx := context.WithValue(r.Context(), loggerKey, reqLogger)
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}

type contextKey struct{}
var loggerKey = contextKey{}

// Handler 中取出 Logger
func LoggerFromContext(ctx context.Context) *zap.Logger {
    if logger, ok := ctx.Value(loggerKey).(*zap.Logger); ok {
        return logger
    }
    return zap.L() // fallback 到全局 logger
}
```

### 8.3 全局 Logger

```go
// 替换全局 Logger（被 L() 和 S() 返回）
zap.ReplaceGlobals(logger)

// 之后任何地方可以用
zap.L().Info("global logger message")
zap.S().Infow("global sugared message", "key", "val")
```

`zap.L()` 返回 `*zap.Logger`，`zap.S()` 返回 `*zap.SugaredLogger`。`ReplaceGlobals` 不是并发安全的，应该在 `main()` 的初始化阶段调用，不要在运行时切换。

---

## 九、高级特性

### 9.1 Hook — 在日志写入后执行回调

```go
logger := zap.New(core,
    zap.Hooks(func(entry zapcore.Entry) error {
        if entry.Level >= zapcore.ErrorLevel {
            // 发送告警到监控系统
            go sendAlert(entry)
        }
        return nil
    }),
)
```

Hook 在日志编码并写入 WriteSyncer 之后被调用。Hook 返回 error 不会阻止日志写入，但会累加到内部的 error count 中（可以用 `logger.Core().Sync()` 的返回值间接看到）。

### 9.2 Sampling — 日志采样

生产环境下，如果某个错误在循环中被疯狂打印（比如数据库连接失败的重试循环），日志量可能瞬间把磁盘打满。Zap 内置的采样器能限制日志频率：

```go
// 每秒前 100 条相同级别和消息的日志正常输出，
// 之后相同级别+消息的日志每 100 条输出一条，并附带丢弃的计数。
sampledCore := zapcore.NewSamplerWithOptions(core, time.Second, 100, 100)

logger := zap.New(sampledCore)

// 循环中不断输出同样内容的错误：
for i := 0; i < 10000; i++ {
    logger.Error("db connection failed")
}
// 实际输出：
// ...前100条正常...
// {"level":"error","msg":"db connection failed"} (第200条)
// {"level":"error","msg":"db connection failed","_sampled":"9900"} (结束时汇报丢弃数)
```

`NewSamplerWithOptions(core, tick, first, thereafter)` 的参数含义：
- `tick`：采样窗口，每个窗口重置计数
- `first`：窗口内前 N 条日志不受限制
- `thereafter`：之后每 N 条输出 1 条

也可以为不同级别设置不同采样策略：

```go
sampledCore := zapcore.NewSamplerWithOptions(core, time.Second, 100, 100)
// 自定义更精细的控制
sampledCore = zapcore.NewSamplerWithOptions(core, time.Second, 100, 100,
    zapcore.WithSamplerHook(func(entry zapcore.Entry, dec zapcore.SamplingDecision) {
        // entry: 日志条目
        // dec: SamplingDecision 表示这条日志被保留还是丢弃
    }),
)
```

### 9.3 动态修改日志级别

```go
// 创建一个可动态调整级别的 Core
level := zap.NewAtomicLevelAt(zapcore.InfoLevel)

core := zapcore.NewCore(
    zapcore.NewJSONEncoder(encoderCfg),
    zapcore.AddSync(os.Stdout),
    level,
)
logger := zap.New(core)

// 运行时通过 HTTP endpoint 或者 SIGHUP 信号动态调整
func debugHandler(w http.ResponseWriter, r *http.Request) {
    level.SetLevel(zapcore.DebugLevel)
    w.Write([]byte("log level set to debug"))
}
```

这对于线上排错非常有用：平时用 `InfoLevel` 减少日志量，出问题时不重启服务就能切到 `DebugLevel`，观察一段时间后再切回来。

### 9.4 写入文件时自动轮转

Zap 本身不提供日志轮转（rotation）。需要配合 `lumberjack`：

```go
import "gopkg.in/natefinch/lumberjack.v2"

writer := &lumberjack.Logger{
    Filename:   "/var/log/app.log",
    MaxSize:    100,  // MB，单个文件最大 100MB 后轮转
    MaxBackups: 10,   // 保留 10 个旧文件
    MaxAge:     30,   // 保留 30 天
    Compress:   true, // 压缩旧文件
}

core := zapcore.NewCore(
    zapcore.NewJSONEncoder(encoderCfg),
    zapcore.AddSync(writer),
    zapcore.InfoLevel,
)
logger := zap.New(core)
```

> ⚠️ `lumberjack` 的 `Write` 方法不是线程安全的吗？它是的，`lumberjack.Logger` 内部有互斥锁保护。但要注意如果有多个 `zap.Logger` 实例写入同一个 `lumberjack.Logger`，轮转行为是共享的。

### 9.5 自定义 Encoder — 接入非标准格式

除了 JSON 和 Console，你可以实现 `zapcore.Encoder` 接口输出任意格式。比如输出给 Logstash 的格式或公司内部格式：

```go
type Encoder interface {
    AddArray(key string, marshaler ArrayMarshaler) error
    AddObject(key string, marshaler ObjectMarshaler) error
    AddBinary(key string, value []byte)
    AddByteString(key string, value []byte)
    AddBool(key string, value bool)
    AddComplex128(key string, value complex128)
    AddComplex64(key string, value complex64)
    AddDuration(key string, value time.Duration)
    AddFloat64(key string, value float64)
    AddFloat32(key string, value float32)
    AddInt(key string, value int)
    AddInt64(key string, value int64)
    AddInt32(key string, value int32)
    AddInt16(key string, value int16)
    AddInt8(key string, value int8)
    AddString(key, value string)
    AddTime(key string, value time.Time)
    AddUint(key string, value uint)
    AddUint64(key string, value uint64)
    AddUint32(key string, value uint32)
    AddUint16(key string, value uint16)
    AddUint8(key string, value uint8)
    AddUintptr(key string, value uintptr)
    AddReflected(key string, value interface{}) error
    OpenNamespace(key string)
    Clone() Encoder
    EncodeEntry(Entry, []Field) (*buffer.Buffer, error)
}
```

实际自定义 Encoder 时，通常组合 `zapcore.EncoderConfig` + 自己的 `EncodeEntry`，而不是从零实现 25 个方法：

```go
type KVEncoder struct {
    zapcore.Encoder // 嵌入默认实现，只重写 EncodeEntry
}

func (e *KVEncoder) EncodeEntry(entry zapcore.Entry, fields []zapcore.Field) (*buffer.Buffer, error) {
    buf := &buffer.Buffer{}
    buf.AppendString(fmt.Sprintf("%s [%s] %s", entry.Time.Format(time.RFC3339), entry.Level.CapitalString(), entry.Message))
    for _, f := range fields {
        buf.AppendString(fmt.Sprintf(" %s=%v", f.Key, f.Interface))
    }
    buf.AppendString("\n")
    return buf, nil
}
```

---

## 十、与 slog 的互操作

Go 1.21 `log/slog` 和 Zap 可以桥接。`zap/exp/zapslog` 提供了 slog Handler 实现：

```go
import "go.uber.org/zap/exp/zapslog"

// 将 Zap Logger 包装为 slog Logger
handler := zapslog.NewHandler(zapLogger.Core(), nil)
slogLogger := slog.New(handler)

// 现在可以用标准库的 slog API 写日志，底层是 Zap 的高性能实现
slogLogger.Info("hello", "key", "value")
```

Zap Logger → slog Handler → 标准库 API。这让你可以在新代码用 slog 的标准接口，同时保持底层 Zap 的性能和配置能力。

---

## 十一、性能优化清单

1. **热路径用 `Logger` 而非 `SugaredLogger`**：省去 `interface{}` 装箱和反射
2. **复用 `zap.Field` 切片**：如果日志的 key 都相同，可以预分配 `[]zap.Field` 然后每次只改 value
3. **用 `logger.With()` 预设固定字段**：避免每次调用都重新序列化 service、env 等不变字段
4. **关闭 caller 和 function**：`zap.AddCaller()` 需要 `runtime.Caller(2)`，有几十纳秒开销
5. **开启采样**：生产环境必须开采样，防止异常循环写爆磁盘
6. **用 `zapcore.BufferedWriteSyncer`**：在 Core 层再加一层缓冲，减少 `Write` 系统调用
7. **用 `zap.Error(err)` 而不是 `zap.String("error", err.Error())`**：前者能处理 nil error（输出空字符串），后者在 err 为 nil 时 panic

> ⚠️ 第 7 条特别容易踩坑。`zap.String("error", err.Error())` 在 `err == nil` 时会 panic。`zap.Error(err)` 正确处理了 nil case，输出空字符串。这是 Zap 源码中专门处理的：

```go
func (f Field) Error(err error) Field {
    return Field{Key: f.Key, Type: zapcore.ErrorType, Interface: err}
}
// 编码时:
func (enc *jsonEncoder) AddError(err error) {
    if err == nil {
        enc.AppendString("") // nil error → 空字符串，不会 panic
        return
    }
    enc.AppendString(err.Error())
}
```

---

## 十二、完整的生产配置模板

```go
package main

import (
    "fmt"
    "os"
    "time"

    "go.uber.org/zap"
    "go.uber.org/zap/zapcore"
    "gopkg.in/natefinch/lumberjack.v2"
)

type LogConfig struct {
    Level      string `yaml:"level"`       // debug, info, warn, error
    Format     string `yaml:"format"`      // json, console
    Filename   string `yaml:"filename"`    // 日志文件路径，为空则只输出到 stdout
    MaxSize    int    `yaml:"max_size"`    // MB
    MaxBackups int    `yaml:"max_backups"` // 保留文件数
    MaxAge     int    `yaml:"max_age"`     // 保留天数
    Compress   bool   `yaml:"compress"`    // 是否压缩
}

func NewZapLogger(cfg LogConfig) (*zap.Logger, error) {
    level := zap.NewAtomicLevelAt(zapcore.InfoLevel)
    if err := level.UnmarshalText([]byte(cfg.Level)); err != nil {
        return nil, fmt.Errorf("parse log level %q: %w", cfg.Level, err)
    }

    encoderCfg := zapcore.EncoderConfig{
        TimeKey:        "ts",
        LevelKey:       "level",
        NameKey:        "logger",
        CallerKey:      "caller",
        FunctionKey:    zapcore.OmitKey,
        MessageKey:     "msg",
        StacktraceKey:  "stacktrace",
        LineEnding:     zapcore.DefaultLineEnding,
        EncodeLevel:    zapcore.LowercaseLevelEncoder,
        EncodeTime:     zapcore.RFC3339NanoTimeEncoder,
        EncodeDuration: zapcore.MillisDurationEncoder,
        EncodeCaller:   zapcore.ShortCallerEncoder,
    }

    var encoder zapcore.Encoder
    if cfg.Format == "console" {
        encoder = zapcore.NewConsoleEncoder(encoderCfg)
    } else {
        encoder = zapcore.NewJSONEncoder(encoderCfg)
    }

    var core zapcore.Core
    if cfg.Filename != "" {
        lumberjackLogger := &lumberjack.Logger{
            Filename:   cfg.Filename,
            MaxSize:    cfg.MaxSize,
            MaxBackups: cfg.MaxBackups,
            MaxAge:     cfg.MaxAge,
            Compress:   cfg.Compress,
        }
        fileWS := zapcore.AddSync(lumberjackLogger)
        stdoutWS := zapcore.AddSync(os.Stdout)
        // Tee: 同时写文件和 stdout
        core = zapcore.NewTee(
            zapcore.NewCore(encoder, fileWS, level),
            zapcore.NewCore(zapcore.NewConsoleEncoder(encoderCfg), stdoutWS, level),
        )
    } else {
        core = zapcore.NewCore(encoder, zapcore.AddSync(os.Stdout), level)
    }

    logger := zap.New(core,
        zap.AddCaller(),
        zap.AddStacktrace(zapcore.ErrorLevel),
    )

    return logger, nil
}
```

使用：

```go
logger, err := NewZapLogger(LogConfig{
    Level:      "info",
    Format:     "json",
    Filename:   "/var/log/app.log",
    MaxSize:    100,
    MaxBackups: 10,
    MaxAge:     30,
    Compress:   true,
})
defer logger.Sync()

zap.ReplaceGlobals(logger) // 设置全局 logger
```

---

## 十三、总结

Zap 的核心价值在于三条设计决策：

1. **类型化 Field 替代 `map[string]interface{}`**——避免日志字段的堆分配
2. **Encoder 和 Core 分离**——编码逻辑和写入逻辑独立，可组合
3. **`With()` 方法预设字段**——静态字段只序列化一次，后续调用只需追加动态字段

日常使用时的建议路径：用预设（`NewProduction`/`NewDevelopment`）→ 按需自定义 `EncoderConfig` → 需要轮转时接入 `lumberjack` → 需要 trace 集成的用 `With()` 预填充 traceID → 高 QPS 服务加采样。

不要过早优化。如果你的服务 QPS 不到一万，`SugaredLogger` 的反射开销完全感知不到。等 profile 告诉你日志占了 >5% CPU 时再来做 Logger 到强类型 Field 的切换。
