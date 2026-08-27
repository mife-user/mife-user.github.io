---
title: PlumeBot — 有记忆、有人格的 QQ 赛博群友
date: 2026-08-24T12:00:00+08:00
draft: false
tags: ["Go", "AI", "Eino", "Agent", "QQ机器人", "OneBot", "SQLite", "DDD"]
---

[项目源码](https://github.com/plumebot/plumeBot)

## 前言

PlumeBot 是一个基于 OneBot v11 协议的 QQ 机器人，对接 NapCat 完成QQ 登录，Go 语言实现，单二进制部署。它不是传统的命令机器人，而是一个**有记忆、有人格、懂分寸的群成员**：像人一样记住群里发生过什么，不会刷屏、不会半夜吵人，被 @ 时上下文永远完整。

**技术栈一览：**

| 层级 | 技术选型 |
|------|----------|
| OneBot 连接层 | ZeroBot v1.8 |
| AI Agent 引擎 | CloudWeGo Eino v0.8 (ADK ChatModelAgent) |
| 存储 | SQLite (modernc.org/sqlite，纯 Go 无 cgo) |
| 配置管理 | Viper (嵌入默认模板 + 敏感字段环境变量覆盖) |
| 日志 | Zap + Lumberjack (日志轮转) |
| 插件 | HashiCorp go-plugin (net/rpc 变体，免 protoc) |
| 限流 | golang.org/x/time/rate |
| 敏感词 | 自研 Aho-Corasick 自动机 |

除 NapCat 外没有任何外部服务依赖——没有 Redis、没有消息队列、没有向量数据库，SQLite 一个文件扛下全部持久化。

---

## 一、项目架构 — DDD 分层与依赖方向

```
cmd/bot/main.go    → 唯一入口，手动依赖注入组装全部模块

internal/
  domain/          → 领域层：纯接口 + 实体 + 哨兵错误，禁止 import 任何第三方库
    entity/        →   Message / Event / Profile / Session 等公共实体
    agent.go       →   Agent 接口（infra/ai 实现）
    memory.go      →   Memory 接口（service/memory 实现）
    storage.go     →   Storage 接口（infra/sqlite 实现）
    control.go     →   Control 接口（service/control 实现）
    sender.go      →   Sender 接口（infra/onebot 实现，per-event 注入 ctx）

  service/         → 业务编排层，只依赖 domain 接口
    event/         →   消息中间件链：日志 → 限流 → 敏感词 → 持久化 → 分流
    memory/        →   上下文窗口 + 摘要压缩 + Prompt 组装
    control/       →   触发判断 + 状态规则（精力/冷却/时段）
    plugin/        →   插件发现/加载/命令路由
    agent/         →   薄透传 GenerateReply → domain.Agent

  handler/         → 事件处理入口（薄胶水，无业务逻辑）
  infra/           → 基础设施，实现 domain 接口
    onebot/        →   ZeroBot 封装 + Sender + GroupManager
    ai/            →   eino Agent + Summarizer + MediaDescriber + tools/
    sqlite/        →   SQLite 存储实现 + 版本化迁移

plugin-sdk/        → 独立 SDK module：第三方插件只依赖它即可编写
pkg/               → config / logger / ahocorasick / base64util
```

依赖方向严格单向：

```
cmd ──→ handler ──→ service ──→ domain（接口）
                      │
                      └──→ infra（编译时注入）

infra ──→ domain（实现接口）
domain 零依赖
```

这套分层带来的实际收益在两处体现得最明显：一是 `infra/ai` 内部从 Instruction 注入人格改为 service 层组装注入 system 消息时，上层代码一行未动；二是插件方案从 Go `.so` 库切换到 go-plugin 子进程时，`domain.Plugin` 接口签名不变，service 层零改动。

### 关键约束

- **domain 层不 import 任何第三方库**——接口定义处看不到 eino、ZeroBot、SQLite 的影子；
- **service 层不 import infra 包**——编排逻辑只面向接口，可独立单测；
- **SQL 语句强制外提**——DML 以包级 `const` 存放在 `queries.go`，DDL 走 `migrations/*.sql` 经 `//go:embed` 加载；
- **哨兵错误集中定义**在 `internal/domain/errors.go`，参数化错误实现 `Unwrap()` 指向哨兵，上层用 `errors.Is` 判断，不耦合数据库驱动。

---

## 二、消息处理管线

每条消息进入后的完整路径：

```
消息进入
  ├── [1. 日志]         所有消息先落日志，包括后续被拦截的
  ├── [2. 限流]          令牌桶按群/用户限流，超限固定文案回复
  ├── [3. 敏感词过滤]    Aho-Corasick 匹配，命中拦截并回复
  ├── [4. 持久化]        写入内存窗口 + SQLite messages 表
  │
  ├── 是命令 (/开头)？  → 插件分发 → 校验指令集 → 回复 + 动作
  │
  └── 是普通消息？
        ├── 触发判断未命中 → 忽略（但已在窗口里旁听）
        └── 命中 → 拼 prompt → Agent 推理 → 发送 → 记忆更新
```

### 2.1 中间件链的实现

ZeroBot 本身没有中间件机制（只有 Rule/Matcher），所以业务管线放进了 service 层自己编织：

```go
// service/event/event.go
mws := []Middleware{
    logMiddleware,
    rateLimitMiddleware(newRateLimiter(mwCfg.RateLimit)),
    sensitiveWordMiddleware(newSensitiveWordFilter(mwCfg.SensitiveWords)),
}
s.msgChain = chain(mws, s.tail)
```

每个中间件签名统一为 `func(ctx, msg, next) error`，命中即返回哨兵错误短路整条链；`tail` 是末端处理：持久化 → 压缩触发 → 命令分支 → 回复闭环。

### 2.2 敏感词过滤：手写 Aho-Corasick 自动机

敏感词可能有几百上千个词条，逐词 `strings.Contains` 是 O(词数 × 文本长度)。Aho-Corasick 自动机把多模式匹配降到 **O(文本长度)**——构建 trie 后 BFS 计算 fail 指针（当前路径的最长真后缀节点），匹配失败沿 fail 指针回退而不是回到开头：

```go
// pkg/ahocorasick/ahocorasick.go
type node struct {
    children map[byte]*node // 子节点（按字节索引，UTF-8 安全）
    fail     *node          // 失配指针
    word     string         // 非空 = 词条终点（保留原始大小写）
}
```

构建一次后自动机只读，多个 goroutine 并发调用 `Find` 无需加锁。空词表 = 不过滤，配置驱动。

> ⚠️ 匹配按小写化字节进行（大小写不敏感），但返回的命中词保留配置中的原始大小写——日志里看到的是配置原样，不是匹配文本片段。

### 2.3 回复闭环：发送成功才算说话

普通消息命中触发后走 `respond`，这条链上有一个关键时序约定——**OnReplied 记账必须在发送成功之后**：

```go
// 发送（Sender 从 ctx 取）。发送失败 = bot 未说话。
if err := sender.Send(ctx, agentReply(msg, reply)); err != nil {
    return nil // 不记账、不追加窗口
}

// 发送成功才：窗口追加 bot 回复 + OnReplied 记账（消耗精力/记冷却）
botMsg := s.botReplyMessage(msg, reply)
s.memory.PersistMessageToSession(ctx, msg.SessionKey(), botMsg)
s.control.OnReplied(ctx, msg)
```

如果把记账挂在触发判断环节，同一条消息可能因为重试或并发被重复扣精力；挂在推理环节则 Agent 推理失败也会白白消耗精力值。只有「消息真的发出去了」才消耗状态，任何一步失败保守沉默——bot 故障时的表现是安静，而不是刷屏报错。

另一个边角：私聊场景下 bot 回复的作者是 botID，按其自身 `SessionKey()` 会派生出 `private:`+botID 这个孤立会话，回复永远进不了用户的对话窗。所以 bot 回复必须经 `PersistMessageToSession` 显式并入触发消息（用户）的会话。

---

## 三、三级记忆系统

这是整个项目的核心设计。像人一样分三层记事：

### 3.1 短期：内存 ring buffer 窗口

```go
const (
    WindowCap       = 100 // 窗口上限：达到后淘汰最旧并触发压缩信号
    CompressionKeep = 20  // 一级压缩后保留轮数
)
```

纯内存实现，初始 20 轮按需增长到 100 上限，满后淘汰最旧并返回压缩触发信号。全量数据已经落 SQLite，窗口淘汰不丢记忆。会话键贯穿始终：**群聊 = GroupID，私聊 = `"private:"`+UserID**，避免空 GroupID 的私聊互相串窗。

锁粒度是 per-session：`sync.Map` 注册表 + 每会话一把 `sync.Mutex`，不同群/私聊的窗口操作互不阻塞，跨会话天然并行。

### 3.2 中期：两级压缩摘要流水线

窗口满 100 条时，取最早 80 条交给 LLM 压缩成一条结构化摘要（保留最新 20 条继续容纳新消息）：

```go
const systemSummaryPrompt = `你是 QQ 群聊记录的摘要助手。你的任务是把一段群聊记录压缩成结构化摘要，
保留话题脉络、关键事件与重要信息，丢弃闲聊与寒暄噪音。

输出严格为单个 JSON 对象：
{"summary":"不超过 150 字的中文摘要","keywords":["3 到 5 个话题关键词"],"decisions":["关键决定"]}`
```

摘要累积超过上限（5 条）时执行**二级融合**——多条旧摘要再交给 LLM 融合成一条综合摘要；融合失败则 FIFO 淘汰最旧兜底，保证流程不卡死。

存储分两层：

- **热链存内存**：当前参与对话的最新摘要，直接拼入 prompt；
- **归档落 SQLite**（`conversation_summary` 表）：被融合覆盖/被淘汰的摘要落库，重启后按会话回灌最新若干条作为热链底——bot 重启后依然记得长程历史。

```go
// ensureLoaded 惰性回灌：会话首次触达时加载归档作热链底，
// seq 续号到已归档最大值+1 —— 跨重启单调递增不重复
func (s *SummaryStore) ensureLoaded(ctx context.Context, chatID string) {
    if _, ok := s.chains[chatID]; ok {
        return
    }
    sums, _ := s.store.ListSummaries(ctx, chatID, summaryReloadLimit)
    maxSeq := int64(0)
    for _, sum := range sums {
        if sum.Seq > maxSeq {
            maxSeq = sum.Seq
        }
    }
    s.chains[chatID] = sums
    s.nextSeq[chatID] = maxSeq + 1
}
```

压缩是异步的：`Trigger` 用会话级防重入 map + 失败冷却（60 秒）防止 LLM 故障时每条消息都触发重试风暴。LLM 压缩失败时不裁剪窗口，数据不丢，冷却后下次重试。

### 3.3 长期：Agent 经 tool calling 自主读写

长期记忆分两类，都是 Agent 在对话中**自主决定何时写**：

| 表 | 内容 | 写入工具 |
|----|------|---------|
| member_facts | 成员事实（爱好/习惯/个人信息），group_id 空=私聊、非空=群聊 | store_fact / forget_fact |
| group_jargon | 群黑话词典，带 pending → confirmed 审核状态机 | learn_jargon |

工具定义用 eino 的 struct 转 schema 能力，参数描述即文档：

```go
type storeFactArgs struct {
    UserID string `json:"user_id" jsonschema:"description=目标用户QQ号；缺省为当前说话人"`
    Fact   string `json:"fact" jsonschema:"required,description=要记住的事实，一句完整的陈述"`
}

return toolutils.NewTool(&schema.ToolInfo{
    Name: "store_fact",
    Desc: "记住一条关于某位群成员的长期事实……重复的相同事实会被自动去重；"
        + "若已有旧事实需要更正，请先用 forget_fact 删除旧事实再调用本工具。",
    ParamsOneOf: params,
}, m.storeFact)
```

三条设计原则值得展开：

**读在组装、写在 tool。** 事实和黑话的读取发生在 prompt 组装时现查注入，不做查询型 tool——数据量小，直接注入比指望模型「记得去查」可靠得多。

**无界写入、有界注入。** 写入侧不做数量限制（小行 + 索引，与 messages 全量落库同性质）；真正有界的是注入 prompt 的量——每成员各 N 条事实、黑话 N 条，上限由组装消费方配置。

**会话身份走 ctx。** 工具是无状态共享单例，「这条记忆属于哪个群的哪个用户」通过 `entity.Session` 注入 ctx，贯穿 eino 传到工具的 `InvokableRun`：

```go
// respond 里注入会话身份
sctx := entity.WithSession(ctx, entity.Session{GroupID: msg.GroupID, UserID: msg.UserID})
reply, err := s.agent.GenerateReply(sctx, msgs)

// 工具内读取——未注入时报错而非写入错误归属
session, ok := entity.SessionFrom(ctx)
if !ok {
    return "", errors.New("缺少会话上下文（group_id/user_id），无法写入记忆")
}
```

黑话学习带审核状态机是个容易忽略的点：模型学到的黑话先落 pending 状态，人工确认后才进入 confirmed 并参与 prompt 注入——防止 Agent 把误读的词污染整个群的话术体系。

---

## 四、Prompt 五段组装

每轮对话的 prompt 都现查现拼，五段顺序固定：

```
┌──────────────────────┐
│ ① 系统人格            │  persona 模板 system_prompt（每次现查 DB）
├──────────────────────┐
│ ② 会话画像            │  群画像 + confirmed 黑话 + 窗口内成员事实
├──────────────────────┐
│ ③ 历史摘要            │  热链全量拼接（旧→新）
├──────────────────────┐
│ ④ 当前窗口            │  最近 N 轮原始消息（时间序）
├──────────────────────┐
│ ⑤ 当前消息            │  正在处理的这条
└──────────────────────┘
```

对应的核心函数：

```go
func (s *MemoryService) buildSystemText(ctx context.Context, msg entity.Message,
    win []entity.Message, botID string) string {
    blocks := []string{
        s.personaText(ctx),                              // ①
        s.buildProfileText(ctx, msg, win, botID),        // ②
        s.buildSummaryText(ctx, msg.SessionKey()),       // ③
    }
    return strings.Join(blocks, "\n\n") + "\n\n" + replyInstruction
}
```

几个渲染细节：

**群聊消息带发送者前缀**，让 agent 区分不同说话人：

```go
func speakerText(m entity.Message) string {
    if m.MessageType != "group" || m.UserID == "" {
        return m.ForLLM()
    }
    return "[" + m.UserID + "]: " + m.ForLLM()
}
```

格式 `[QQ号]: 内容` 与压缩输入完全对齐——压缩时看到的和对话时看到的是同一视图，摘要里的指代不会错位。私聊对方唯一且画像块已标注用户 ID，不加前缀避免噪音。

**bot 自己的历史消息映射为 assistant 角色**（其余为 user），模型才能把「我之前说过的话」当成自己说的，而不是旁观另一人的发言。

**空 MessageID 去重**。OneBot 偶发 `message_id=0`，转 ID 为空串。当前消息持久化后必然出现在窗口末尾，此时不能按 ID 去重（会误删所有空 ID 消息），只能对末尾一条做「同发送者同时刻」匹配去重：

```go
if msg.MessageID == "" && i == len(win)-1 && m.UserID == msg.UserID && m.Timestamp == msg.Timestamp {
    continue // 仅对末尾按位置去重，避免误删早期同秒消息
}
```

---

## 五、触发控制 — 像人一样有分寸

不会刷屏、不会半夜吵人，靠的是两层机制。

### 5.1 mention / auto 双模式

| 模式 | 行为 |
|------|------|
| mention | 仅被 @ 或私聊时回复；所有消息仍流入窗口，被 @ 时上下文完整 |
| auto | @ 和私聊一定回复；普通消息由状态规则判断是否加入 |

每个群可在 `group_config` 表独立配置模式。归一化时**未知/空一律兜底 mention**（fail-closed）——配置错了最多是变安静，不会变成失控刷屏：

```go
func normalizeMode(mode string) string {
    if mode == ModeAuto {
        return ModeAuto
    }
    return ModeMention // 空/未知 → mention
}
```

关键边界：**触发模式只控制「是否回复」，不影响「是否收消息」**。被规则拦下的消息 ≠ 丢弃——它已经走完了日志→限流→敏感词→持久化链，仍在窗口里持续旁听。所以哪怕 bot 半天没说话，被 @ 时它依然知道「刚刚大家在聊什么」。

### 5.2 五条状态规则（纯规则层，不调 LLM）

auto 模式下的普通消息按这个顺序评估：

```go
func (s *ControlService) shouldReplyAuto(ctx context.Context, msg entity.Message, p ruleConfig) (entity.Decision, error) {
    // 1. 短消息忽略：<N 字不触发（中文按字计）
    if utf8.RuneCountInString(msg.PlainText()) < p.shortMessageChars {
        return entity.Decision{Reason: entity.DecisionReasonShortMessage}, nil
    }
    // 2. 时段控制：深夜/凌晨静默（支持跨午夜区间）
    if inQuietHours(p, s.now()) {
        return entity.Decision{Reason: entity.DecisionReasonQuietHours}, nil
    }
    // 3. 精力值：惰性恢复后判断是否低于阈值
    st, err := s.loadState(ctx, msg.SessionKey())
    s.recoverEnergy(&st, p, s.now())
    if st.Energy < p.energyThreshold {
        return entity.Decision{Reason: entity.DecisionReasonLowEnergy}, nil
    }
    // 4. 冷却 / 强制休息
    if now < st.RestUntil || now < st.LastReplyAt+p.cooldownSeconds {
        return entity.Decision{Reason: entity.DecisionReasonCooldown}, nil
    }
    return entity.Decision{Reply: true, Reason: entity.DecisionReasonAutoPass}, nil
}
```

前两条不读数据库（短路省查询）；被 @ 或私聊 = 强制回复，绕过全部规则且 0 查询。

**精力值的惰性恢复**是不跑定时器的经典做法——读时按整分钟增益补算，子分钟余数留待下次累计防漂移：

```go
func (s *ControlService) recoverEnergy(st *groupState, p ruleConfig, now time.Time) {
    elapsedMin := (now.Unix() - st.EnergyUpdatedAt) / 60
    if elapsedMin <= 0 {
        return
    }
    gain := int(elapsedMin) * p.energyRecover
    if st.Energy+gain >= p.energyMax {
        st.Energy = p.energyMax
        st.EnergyUpdatedAt = now.Unix() // 满格归位，避免下次重复计算
        return
    }
    st.Energy += gain
    st.EnergyUpdatedAt += elapsedMin * 60 // 只前进整分钟
}
```

**连续回复上限**的处理有个对称性细节：连续计数达到上限进入强制休息后，休息期内不递增计数（防 @ 风暴反复延长休息）；距上次回复 ≥ 冷却窗口则计数重置为 1——与 ShouldReply 里「过了冷却就放行」的条件严格对称，否则会出现「判定能回但记账判连续」的边界分裂。

运行态存 `bot_state` 表（JSON 字段，每会话一行），同一会话的读-改-写以 per-session 锁串行化，防并发触发丢更新或绕过冷却。

> ⚠️ 已知边界：纯图片消息 `PlainText()` 为空，auto 模式会被短消息规则短路而永不触发——多模态启用后需要豁免非 text 段（roadmap B-039）。

---

## 六、人格系统 — 改库即时生效

人格不是写在配置文件里的一行 system prompt，而是 SQLite `persona` 表中的一条模板：

```sql
persona (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  agent         TEXT NOT NULL DEFAULT '',  -- 绑定的 agent 名，UNIQUE
  name          TEXT NOT NULL DEFAULT '',  -- 展示名
  system_prompt TEXT NOT NULL DEFAULT ''   -- 完整人设文本
);
```

第一版把人格经 eino 的 `Instruction` 注入 infra 层，很快发现问题：**改人格要重启**。修订后的方案是组装层现查——`BuildMessages` 每次组装都查一遍 persona 表，改表即时生效，无需重启：

```go
func (s *MemoryService) personaText(ctx context.Context) string {
    p, err := s.store.GetPersonaByAgent(ctx, s.agentName)
    if err == nil && strings.TrimSpace(p.SystemPrompt) != "" {
        return p.SystemPrompt
    }
    // 兜底链：defaultPersona(main 传入) → config.DefaultSystemPrompt
    ...
}
```

兜底链完整：DB 模板 → 配置项 → 内置默认人设，任何一环缺失都不会让 bot 失去人格。启动时默认 agent 若无模板则 seed 一条（固化当时生效的人设），并在日志中明确提示「人格来自 DB persona 表」——避免用户改了 `config.yaml` 里的 system_prompt 后困惑为什么不生效（config 值只是首次 seed 和兜底用的）。

「人格选择 agent」的绑定方向也值得注意：配置里只有 `agent.name`，不引用 persona id——模板行通过 `agent` 字段反向绑定，未来多 agent 各挂各的人格，互不干扰。

---

## 七、多模态感知 — 图片惰性描述

群里发的图不会以原图形式进 prompt（成本不可控），而是走**惰性描述**：配置了 vision_model 时，组装阶段把最近 N 轮 + 当前消息里的图片交给视觉模型生成文字描述，预算控制（每轮描述轮数 + 每消息张数上限）防止一张斗图刷爆 token。

描述结果有两处去向：

1. **写回 SQLite**（`UpdateMessageParts`）——下次组装直接跳过已描述的图，同图永不重复调模型；
2. **回填内存窗口**——压缩摘要也能包含图片内容。

这里有一个教科书级的并发问题。窗口为了并发安全做了深拷贝读取（见下一节），组装拿到的是副本——在副本上写的描述如何回到窗口内部？答案是显式回填接口：

```go
// BackfillParts 在窗口锁内把最新 Parts 写回内部消息（深拷贝入参，杜绝逃逸数组竞态）
func (w *Window) BackfillParts(_ context.Context, sessionID, messageID string, parts []entity.ContentPart) {
    sw.mu.Lock()
    defer sw.mu.Unlock()
    for i := range sw.data {
        if sw.data[i].MessageID == messageID {
            sw.data[i].Parts = append([]entity.ContentPart(nil), parts...)
            return
        }
    }
}
```

回填失败静默跳过（消息已被压缩移除属正常情况）——描述已持久化，下次组装重试即可。这类「最佳努力」优化用可选接口 + 类型断言接入，不污染 domain 核心接口。

图片本身经 base64 入链时有内容级 md5 去重缓存（`data/image_cache/`），URL 存路径闭合「base64 不入库」原则——SQLite 里不存大对象。

---

## 八、AI 群管理 — 护栏先行

Agent 可以调用四个工具自主管群：`group_mute / group_unmute / group_kick / group_set_card`。高危能力开放给 LLM，护栏设计比功能本身重要。

### 8.1 三道护栏集中在唯一执行入口

```go
func (m *botGroupManager) Execute(ctx context.Context, action entity.GroupAction) error {
    // 护栏 0：群聊守卫——私聊事件直接拒绝
    // 护栏 1：per-group 开关 group_mgmt_enabled（默认开，0 = 显式关闭）
    // 护栏 2：触发者与 bot 都须为群主/管理员（fail-closed）
    if !memberInfoIsAdmin(m.ctx.GetGroupMemberInfo(groupID, triggerer, true)) {
        return errors.New("仅群主/管理员可触发群管理动作")
    }
    if !memberInfoIsAdmin(m.ctx.GetGroupMemberInfo(groupID, m.botID, true)) {
        return errors.New("bot 非本群主/管理员，无法执行")
    }
    // 护栏 3：动作映射（mute 时长钳制 30 天）+ API 响应检查
    rsp := m.ctx.CallAction(actionName, params)
    if rsp.Status != "ok" || rsp.RetCode != 0 {
        return fmt.Errorf("动作 %s 执行失败: retcode=%d", actionName, rsp.RetCode)
    }
    return nil
}
```

三个设计决策：

**fail-closed 校验。** `get_group_member_info` 查询失败、响应缺 role 字段，一律按非管理员拒绝。权限校验的正确失败方向是「拒绝」，不是「放行」。

**不用封装方法，直接 CallAction。** ZeroBot 的 `SetGroupBan` 等封装方法返回 void，吞掉了 API 响应——禁言失败无从得知，高危能力静默失败不可接受。必须走 `ctx.CallAction` 检查 `APIResponse.Status/RetCode`。

**mute 时长钳制**到 QQ 平台上限 30 天，超限时钳而不是拒——模型给出的时长数字本就不必精确，钳制比报错重试体验好。

### 8.2 工具层零校验

护栏不在工具实现里重复——工具只做「群聊守卫 → 取执行器 → 构造动作」，全部校验收敛在 `GroupManager.Execute`。这样插件系统的群管理动作（见下一节）与 AI 工具走**同一条执行路径**，护栏天然共享，不存在「插件绕过校验」的第二入口。

工具的 Desc 也承担安全职责——把触发边界写清楚，让模型自己学会克制：

```go
Desc: "将某位群成员移出本群。踢人属最高危动作，仅当成员严重违规（广告、人身攻击）时调用；" +
    "本群未显式关闭群管理开关且你和 bot 都是群主/管理员，任一不满足调用失败。仅群聊可用。",
```

---

## 九、插件系统 — 子进程隔离 + 零权限协议

### 9.1 为什么放弃 Go .so

Go 官方 `plugin` 包（`-buildmode=plugin`）看起来是最顺路的选择，实际全是坑：

- **仅支持 Linux/FreeBSD/macOS**——Windows 开发机直接不可用，且禁交叉编译；
- **无卸载 API**——只能热添加不能替换，算不上真热重载;
- **同进程运行**——插件 panic 拖垮整个 bot；
- **强版本耦合**——插件需与主程序完全同 Go 版本编译。

最终定案：**HashiCorp go-plugin 子进程 stdio 通信**（net/rpc 变体，免 protoc）。插件崩溃不影响主程序、真热重载（重启子进程）、跨平台编译无障碍。

### 9.2 指令集协议：插件零权限，宿主唯一执行者

插件碰不到 OneBot API，只声明意图：

```go
// 请求（宿主 → 插件）
PluginRequest{Command, Args, Session{GroupID, UserID, MessageID}}

// 结果（插件 → 宿主）：结构化声明想要什么，执行权在宿主
PluginResult{
    Reply: &Reply{                    // 单条回复：多段混排
        Quote: true,                  //   引用触发消息
        At:    "sender",              //   @"sender" / "" / 具体 user_id
        Segments: []Segment{          //   text / image / face
            {Kind: SegmentKindText, Text: "echo: " + strings.Join(req.Args, " ")},
            {Kind: SegmentKindImage, Image: &ImageRef{...}},
        },
    },
    Actions: []GroupAction{           // 群管理动作（与 AI 工具同一套护栏）
        {Op: GroupOpMute, Target: req.Session.UserID, Duration: 60},
    },
}
```

宿主先校验（枚举合法性/必填字段），校验通过后：回复经 ctx 内 Sender 发送，动作经 `GroupManager.Execute` 执行——先发回复后执行动作，用户立刻能看到反馈。

### 9.3 独立 SDK module

协议类型与 go-plugin 接线抽成了仓库内的独立 module `plugin-sdk/`（entity wire 类型 + Serve/NewClient 接线）。第三方插件只 import SDK 即可编写，完全不接触宿主 internal 包。一个最小插件：

```go
package main

import (
    "context"
    "github.com/plumebot/plumebot-sdk/plugin"
)

type hello struct{}

func (h *hello) Execute(_ context.Context, req plugin.PluginRequest) (plugin.PluginResult, error) {
    return plugin.PluginResult{Reply: &plugin.Reply{
        Segments: []plugin.Segment{{Kind: plugin.SegmentKindText, Text: "hello!"}},
    }}, nil
}

func main() { plugin.Serve(&hello{}) }
```

编译成 exe 放入 `plugins/<name>/` 并配一份 `plugin.json`（name/path/commands）即被发现加载。单个插件加载失败仅告警跳过，坏插件不会阻断 bot 启动。

gob 序列化对类型名敏感——宿主 internal/entity 的协议类型用**类型别名**指向 SDK 类型（`type X = sdkentity.X`），保证两侧 gob 注册的类型路径一致，这是子进程 RPC 不出诡异解码错误的隐藏前提。

---

## 十、并发设计 — 几个值得抄的细节

### 10.1 per-session 锁，跨会话天然并行

窗口、触发状态两处的并发控制用同一模式：`sync.Map` 注册表 + 每会话一把 `sync.Mutex`。

```go
func (w *Window) AppendToSession(_ context.Context, sessionID string, msg entity.Message) (bool, error) {
    raw, _ := w.sessions.LoadOrStore(sessionID, &sessionWindow{}) // 原子 get-or-create
    sw := raw.(*sessionWindow)
    sw.mu.Lock()
    defer sw.mu.Unlock()
    ...
}
```

不同群的消息处理完全并行，单会话内串行保序。注册表用 `LoadOrStore` 保证并发首条消息不会创建两个窗口实例。

> ⚠️ 这几个按会话键的 map（窗口/限流器/画像缓存/摘要链）目前只增不删，长期运行的内存治理（LRU/TTL 淘汰）列在 roadmap 待办里——单机自用规模无碍，公开部署前需要处理。

### 10.2 深拷贝快照 + 锁内回填

组装 prompt 和压缩摘要都要读窗口，如果拿着窗口的内部切片去做 LLM 调用，要么全程持锁（阻塞该会话的新消息写入），要么遭遇切片逃逸后被并发修改。解法是把「读快照」和「写回」拆成两个原语：

```go
// 读：锁内深拷贝（Message 与 Parts 均复制），调用方任意读写都不影响窗口内部
func (w *Window) GetWindow(...) ([]entity.Message, error) {
    out := make([]entity.Message, len(buf))
    copy(out, buf)
    for i := range out {
        parts := make([]entity.ContentPart, len(buf[i].Parts))
        copy(parts, buf[i].Parts)
        out[i].Parts = parts
    }
    return out, nil
}
```

组装/压缩各持独立快照，LLM 调用期间零持锁；产生的图片描述经 `BackfillParts` 在窗口锁内一次性写回。**持锁绝不含 IO** 是铁律。

### 10.3 版本化数据库迁移

早期 migrate() 是全量重跑 001 建表脚本，`CREATE TABLE IF NOT EXISTS` 对已存在的表不加新列——某次给 `group_config` 加 10 列时原地改了 001，旧库升级静默失效，运行时报「no such column」。修复后改为版本记录式：

- 建 `schema_migrations` 表（version PK + applied_at）；
- 每个迁移文件在**单事务内**执行并记录版本；
- 任一语句失败整体回滚、不记版本——下次启动重试，杜绝「ALTER 成功但未记录 → 重启 duplicate column」；
- 新增列一律新建 `00N_*.sql`（SQLite 没有 `ADD COLUMN IF NOT EXISTS`，幂等性靠版本记录保证）。

---

## 十一、项目亮点总结

1. **三级记忆系统**：ring buffer 窗口（短期）→ 两级 LLM 压缩摘要 + 热链/归档分离（中期）→ member_facts/group_jargon 经 tool calling 自主读写（长期），重启自动回灌
2. **Prompt 五段组装**：人格 → 会话画像 → 历史摘要 → 窗口 → 当前消息，每轮现查现拼；群聊带 `[QQ号]:` 发送者前缀且与压缩输入格式对齐
3. **人格即数据**：persona 表模板 + 组装层现查，改库即时生效无需重启，三层兜底链
4. **触发控制双层设计**：mention/auto 双模式 + 五条纯规则层状态（精力惰性恢复/冷却/连续上限/深夜静默/短消息），拦截 ≠ 丢弃，旁听不断
5. **AI 群管理护栏先行**：三道护栏集中在唯一执行入口，fail-closed 权限校验，CallAction 检查 API 响应拒绝静默失败
6. **插件零权限协议**：go-plugin 子进程隔离 + 指令集协议（只声明意图，宿主执行），独立 SDK module 第三方可自由编写，群管理动作与 AI 工具共用护栏链
7. **自研 Aho-Corasick**：O(文本长度) 多模式匹配，构建后只读可并发
8. **并发工程细节**：per-session 锁粒度、GetWindow 深拷贝 + BackfillParts 锁内回填、持锁绝不含 IO、版本化迁移单事务执行
9. **纯 Go 无 cgo**：modernc.org/sqlite 驱动，交叉编译无障碍，单二进制部署

## 后续方向

- [ ] P6-003 稳定性验证：长时间运行内存/goroutine 泄漏检查，无界 map 统一 LRU/TTL 治理
- [ ] 引用回复解析（reply 段）：从窗口/SQLite 找回被引用原文并入上下文
- [ ] 重启断档补全：经 NapCat `get_group_msg_history` 按 seq 拉取离线期间的群消息
- [ ] 阶段 3 原生多模态：image part 直接喂视觉模型（`native_multimodal` 开关已占位）
- [ ] 插件热重载与崩溃自动重启（go-plugin 原生支持，mtime 轮询检测变更）
