---
title: 云网盘服务 — 从架构设计到工程落地
date: 2026-03-11T09:43:00+08:00
draft: false
tags: ["Go", "Gin", "网盘", "Redis", "DDD", "项目实战"]
---

[项目源码](https://github.com/mife-user/Cloud_Drive)

## 前言

Cloud_Drive 是一个全栈云网盘服务，后端基于 Go + Gin 构建，前端使用 Vue3 + Element Plus，支持 Docker Compose 一键部署。项目虽然规模不大，但在架构分层、缓存策略、文件处理等方面做了比较完整的工程实践，适合作为 Go Web 后端方向的面试展示项目。

**技术栈一览：**

| 层级 | 技术选型 |
|------|------|
| Web 框架 | Gin v1.11 |
| ORM | GORM v1.31 + MySQL 8.0 |
| 缓存 | Redis 7.x (go-redis/v8) |
| 认证 | JWT (golang-jwt/v5) |
| 密码加密 | bcrypt |
| 配置管理 | Viper (多环境 + 环境变量覆盖) |
| 日志 | Zap + Lumberjack (日志轮转) |
| 定时任务 | robfig/cron v3 |
| 限流 | golang.org/x/time/rate |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Axios |
| 部署 | Docker + Docker Compose |

---

## 一、项目架构 — 领域驱动设计（DDD）分层

项目采用经典的 DDD 分层架构，从上到下各层职责清晰，依赖方向严格向内：

```
cmd/main/          → 程序入口，启动引导
cmd/bootstrap/     → 启动编排：加载配置 → 初始化日志 → 初始化数据库 →
                      初始化Redis → 运行迁移 → 注册路由 → 启动定时任务
                      
internal/api/      → 接口层（HTTP）
  ├── routes/      → 路由注册，组装依赖
  ├── handlers/    → 请求处理，参数校验，调用 Service
  ├── middlewares/  → 认证、CORS、文件类型校验
  └── dtos/        → 请求/响应 DTO，隔离外部协议与内部模型

internal/service/  → 业务逻辑层，编排 Domain + Repo
internal/repo/     → 数据访问层，封装 GORM + Redis 缓存
internal/domain/   → 领域核心：实体定义 + 接口契约（Repo / Servicer）
internal/model/    → 数据库模型（GORM Model）

pkg/               → 公共基础设施（auth, cache, cron, db, logger, pool, save...）
configs/           → YAML 配置文件（config.yaml + config.dev.yaml + config.prod.yaml）
migrations/        → 数据库 AutoMigrate
web/               → Vue3 前端（SFC + Vite 构建）
```

### 关键设计决策

**1. 接口契约集中定义（bridge.go）**

在 `internal/domain/bridge.go` 中统一定义 `UserRepo`、`FileRepo`、`UserServicer`、`FileServicer` 四个接口。这样做的好处是：
- Handler 不依赖具体实现，只依赖接口，方便单元测试 Mock
- Service 和 Repo 的实现可以独立替换
- 接口定义与领域模型放在一起，符合 DDD 的"依赖倒置"原则

```go
// domain/bridge.go
type FileRepo interface {
    UploadFile(ctx context.Context, files []*File, nowSize int64) error
    DeleteFile(ctx context.Context, userID uint, fileID uint) error
    ViewFile(ctx context.Context, fileID uint, userID uint) (*File, error)
    // ...
}

type FileServicer interface {
    UploadFile(ctx context.Context, files []*File, nowSize int64) error
    // ...
}
```

**2. 依赖注入手动完成**

在 `routes/router.go` 的 `NewRouter` 方法中，按照 "Repo → Service → Handler" 的顺序逐层组装依赖，没有引入第三方 DI 容器，保持简单可控：

```go
func (r *Router) NewRouter(db *gorm.DB, rd *redis.Client, config *conf.Config) bool {
    userRepo := repo.NewUserRepo(db, rd)
    fileRepo := repo.NewFileRepo(db, rd)
    userServicer := service.NewUserServicer(userRepo, config)
    fileServicer := service.NewFileServicer(fileRepo, config)
    r.fileHandler = handlers.NewFileHandler(fileServicer, config)
    r.userHandler = handlers.NewUserHandler(userServicer, config)
    return true
}
```

**3. 优雅启动与关闭**

`main.go` 中通过 signal 监听实现优雅关闭，确保收到 SIGINT/SIGTERM 后 5 秒内完成资源释放：

```go
func main() {
    app, _ := bootstrap.NewApplication()
    go func() { app.Run() }()
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    app.Shutdown(ctx)
}
```

---

## 二、功能模块与技术实现

### 2.1 用户系统

| 功能 | 技术细节 |
|------|----------|
| 注册 | bcrypt 密码哈希，用户名唯一性校验（先查 Redis 缓存，再查 DB） |
| 登录 | JWT 签发（HS256，24h 过期），Claims 包含 UserID / Name / Role |
| 鉴权 | Gin 中间件解析 `Authorization: Bearer <token>`，将用户信息注入 Context |
| 头像 | multipart/form-data 上传，本地存储，路径记录到 UserHeader 表 |
| 信息修改 | 支持修改用户名、密码，旧用户名校验 |

**JWT 中间件流程：**

```
请求 → 提取 Authorization Header → 验证 Bearer 前缀
→ jwt.ParseWithClaims() → 验证签名和过期时间
→ 将 user_id / role / user_name 写入 gin.Context
→ c.Next()
```

### 2.2 文件系统

#### 普通上传

适用于小文件（< 5MB），通过 `multipart/form-data` 一次性提交。流程：

```
客户端 POST /api/file/upload (multipart/form-data)
→ TypeCheck 中间件校验文件扩展名
→ AuthMiddleware 提取用户信息
→ handler: 计算文件大小 → checkUserSize(空间配额检查)
→ service: 调用 save.SaveFiles 将文件写入 ./storage/{userID}/{fileName}
→ repo: 写 MySQL 记录 + 淘汰 Redis 文件列表缓存
```

#### 分片上传（大文件）

对于大文件，采用**前端分片 + 后端合并**的方案：

```
分片上传流程（3 步）:

Step 1 — POST /api/file/chunk/upload
  { MD5, ChunkIndex, TotalChunks, Data(Base64) }
  → Base64 解码 → save.SaveChunk → ./storage/chunks/{md5}/{n}.part
  → Redis 记录分片进度: HSET chunk:meta:{md5} chunks {totalChunks}

Step 2 — GET /api/file/chunk/progress/:md5
  → save.GetChunkFiles → 扫描磁盘 {n}.part 文件
  → Redis HGETALL chunk:meta:{md5} 获取预期的 totalChunks
  → 返回 { uploaded: [1,2,3,...], total: 10 }
  → 前端据此实现断点续传，只上传缺失的分片

Step 3 — POST /api/file/chunk/merge
  { MD5, FileName, TotalChunks }
  → save.MergeChunks 按 1..N 顺序合并分片
  → 写入 ./storage/{userID}/{fileName}
  → save.CleanChunks 清理临时分片
  → 写 MySQL 文件记录
```

这个设计的关键点：
- **MD5 作为分片会话ID**：同一个文件的多个分片通过 MD5 关联
- **断点续传**：通过 progress 接口查询已上传分片，只上传缺失的部分
- **Base64 编码**：前端将分片数据编码为 Base64 JSON 传输，简化编码处理

#### 软删除与回收站

```
软删除: DELETE /api/file/delete/:file_id
  → GORM Soft Delete (设置 deleted_at 时间戳)
  → 文件仍在数据库和磁盘中

查看回收站: GET /api/file/view/deleted
  → 查询 deleted_at IS NOT NULL 的记录

永久删除: DELETE /api/file/delete/:file_id/forever
  → GORM Unscoped().Delete (物理删除)
  → 同时删除磁盘文件

定时清理: cron 每天凌晨1点
  → 清理 deleted_at 超过 N 天的文件（默认1天）
```

#### 文件分享

分享机制采用 **ShareID + AccessKey 双 token** 设计：

```
创建分享: POST /api/file/share
  { FileID, ExpiresAt }
  → 生成随机 ShareID + AccessKey（双双 8 位随机字符串）
  → 写入 file_shares 表
  → 返回 { share_id, access_key }

访问分享: GET /api/file/share/:share_id?key=xxx
  → 无需登录（跳过 AuthMiddleware）
  → 校验 share_id 和 access_key
  → 校验是否过期（ExpiresAt）
  → 返回文件详情
```

ShareID 可公开传播，AccessKey 作为"密码"保护分享链接。

#### 收藏与权限

- 收藏：`file_favorites` 表记录 user_id + file_id，支持添加/取消/查看
- 权限：文件支持 public/private 两种权限，public 文件可被其他用户查看

### 2.3 会员体系

在 `model/user.go` 中，用户有 `Role`（NOVIP/VIP）和 `Size`（空间配额）、`NowSize`（已用空间）：

```go
type User struct {
    gorm.Model
    UserName string
    PassWord string
    Role     string `gorm:"default:NOVIP"`  // NOVIP 默认 1GB, VIP 可配置更大
    Size     int64   // 空间配额（字节）
    NowSize  int64   // 已用空间（字节）
}
```

上传文件时通过 `CheckUserSize` 判断 `NowSize + FileSize > Size` 则拒绝。

---

## 三、Redis 缓存策略 — 三重防护

这是项目中最能体现技术深度的部分。针对高并发场景下 Redis 缓存的三个经典问题，都做了完整实现。

### 3.1 缓存穿透（空对象缓存）

**问题**：恶意请求查询不存在的 key，绕过缓存直接打到数据库。

**方案**：对不存在的数据也缓存一个标记值，带较短 TTL（5±1 分钟随机）：

```go
// cache/cache_penetration.go
const NullValueMarker = "__NULL_VALUE__"

func CacheNullValue(ctx context.Context, rdb *redis.Client, key string) error {
    ttl := NullCacheConfig.RandomTTL()  // 5分钟 ± 1分钟
    return rdb.Set(ctx, key, NullValueMarker, ttl).Err()
}
```

**应用场景**：登录时缓存不存在的用户名，注册时先检查空值缓存。

### 3.2 缓存雪崩（随机过期时间）

**问题**：大量缓存在同一时间过期，瞬间请求全部打到数据库。

**方案**：给每个 key 的 TTL 加上一个随机偏移量（加密安全随机数），让过期时间分散开：

```go
// cache/cache_strategy.go
func (c *CacheConfig) RandomTTL() time.Duration {
    max := big.NewInt(int64(c.RandomRange * 2))
    n, _ := cryptoRand.Int(cryptoRand.Reader, max)
    offset := time.Duration(n.Int64()) - c.RandomRange
    return c.BaseTTL + offset  // 例如 1h ± 10min
}

var UserCacheConfig     = NewCacheConfig(1*time.Hour, 10*time.Minute)   // 用户缓存 1h±10m
var FileCacheConfig     = NewCacheConfig(3*time.Hour, 30*time.Minute)   // 文件缓存 3h±30m
var FavoriteCacheConfig = NewCacheConfig(30*time.Minute, 5*time.Minute) // 收藏缓存 30m±5m
var ShareCacheConfig    = NewCacheConfig(15*time.Minute, 3*time.Minute) // 分享缓存 15m±3m
```

不同业务的数据热度不同，分别设置不同的 BaseTTL 和随机范围。

### 3.3 缓存击穿（Singleflight）

**问题**：热点 key 过期瞬间，大量并发请求同时去数据库加载同一个数据。

**方案**：使用 `golang.org/x/sync/singleflight`，对同一个 key 的并发加载请求，只允许一个真正去查数据库，其他请求等待结果复用：

```go
// repo/file_type.go
type fileRepo struct {
    db    *gorm.DB
    rd    *redis.Client
    rds   *singleflight.Group  // singleflight 分组
    locks sync.Map             // 按 ID 粒度的互斥锁
}
```

`rds` 用于缓存穿透控制——同一 key 的缓存加载只执行一次。`locks` 提供按 ID 级别的互斥锁，防止并发修改冲突。

---

## 四、基础设施组件

### 4.1 配置管理（Viper）

- 主配置文件 `configs/config.yaml` + 环境覆盖文件 `configs/config.{env}.yaml`
- 支持环境变量覆盖（`CLOUDPAN_ENV`, `CLOUDPAN_MYSQL_DSN`, `CLOUDPAN_REDIS_HOST`, `CLOUDPAN_JWT_SECRET`）
- 启动时校验必填配置项

### 4.2 日志系统（Zap + Lumberjack）

- 根据不同环境自动选择格式：dev → 控制台彩色输出，prod → JSON 格式
- 日志轮转：单文件最大 10MB，保留 5 个备份，最长保留 30 天
- 结构化字段辅助函数（`logger.S()`, `logger.U()`, `logger.C()`）

### 4.3 数据库初始化（带重试）

连接 MySQL 时有 5 次重试机制，每次间隔 8 秒，适配 Docker Compose 中 MySQL 容器启动延迟的问题：

```go
func Init() error {
    for i := 0; i < 5; i++ {
        conn, err := gorm.Open(mysql.Open(g.Mysql.Dsn), &gorm.Config{})
        if err != nil {
            time.Sleep(8 * time.Second)
            continue
        }
        sqlDB, _ := conn.DB()
        sqlDB.SetMaxIdleConns(g.Mysql.MaxIdle)
        sqlDB.SetMaxOpenConns(g.Mysql.MaxOpen)
        database = conn
        return nil
    }
    return fmt.Errorf("数据库连接失败")
}
```

### 4.4 定时任务（Cron）

| 任务 | 频率 | 功能 |
|------|------|------|
| 清理已删除文件 | 每天凌晨 1:00 | 物理删除 deleted_at 超过 N 天的文件记录 |
| 清理过期分片 | 每小时 | 遍历 `./storage/chunks/`，删除 Redis 中已无元数据的过期分片目录 |

### 4.5 协程池（自定义）

`pkg/pool` 实现了一个简洁的 goroutine pool，用于控制并发任务数量：

```go
type Pool struct {
    Size  int
    Tasks chan func()
}
```

在上传文件批量缓存时使用（协程池大小 = 4），避免瞬时创建过多 goroutine。

### 4.6 Context 感知的任务执行器

`pkg/task/init.go` 中的 `task.Do()` 函数，在执行 repo 操作时同时监听 context 取消信号，确保请求超时或被取消时能及时退出。

### 4.7 文件保存与限速

- `pkg/save/file.go`：负责将上传文件写入磁盘，处理路径冲突（重名文件追加时间戳后缀）
- `pkg/save/limit.go`：基于 `golang.org/x/time/rate` 令牌桶实现读取限速，可以限制不同会员等级的上传/下载带宽

### 4.8 统一错误码

`pkg/errorer/errorer.go` 定义了项目所有错误常量，分用户错误、文件错误、分享错误、收藏错误等类，返回中文错误信息，前端可直接展示。

---

## 五、项目亮点总结

1. **完整的分层架构**：DDD 四层（接口层 → 服务层 → 仓库层 → 领域层），职责清晰，依赖方向符合倒置原则
2. **缓存三防护**：穿透（空对象缓存）、雪崩（随机 TTL）、击穿（singleflight），是目前面试中最常问的缓存问题
3. **分片上传 + 断点续传**：MD5 会话关联 + Redis 进度追踪 + 磁盘分片存储，实现成熟的大文件传输方案
4. **双重分享 Token 设计**：ShareID（定位）+ AccessKey（鉴权），兼顾易传播与安全性
5. **手动依赖注入**：不引入 DI 框架，依赖关系一目了然，符合 Go 社区的简洁理念
6. **优雅关闭**：signal 监听 + context 超时控制，确保服务安全退出
7. **Docker Compose 全栈部署**：一键启动 MySQL + Redis + 后端 + 前端（Nginx），生产可用
8. **数据库重试机制**：适配容器编排中服务的启动顺序问题

---

## 六、待完善方向

- [ ] 文件搜索引擎（可引入 Elasticsearch 或 bleve）
- [ ] 敏感内容检测（图片/文本审核）
- [ ] 文件标签系统（多标签关联 + 按标签检索）
- [ ] 单元测试覆盖
- [ ] API 限流中间件（基于令牌桶或滑动窗口）
- [ ] 文件版本管理
- [ ] WebSocket 实时上传进度推送
