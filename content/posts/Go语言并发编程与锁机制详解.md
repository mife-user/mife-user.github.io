---
title: 'Go语言并发编程与锁机制详解：从新手到能写并发安全的代码'
date: 2026-06-15T15:00:00+08:00
draft: false
tags: ["Go", "并发", "goroutine", "channel", "mutex", "锁", "sync", "atomic", "面试"]
---

## 前言：银行柜台的启示

你走进一家银行，发现这家银行有一个奇怪的规则：**只有 1 个柜台，但可以有无数个排队的人**。

- 每个排队的人就是一个 **goroutine**
- 柜台服务员就是 **操作系统线程**（通常只有几个）
- 排队的人之间可以传纸条交流——这就是 **channel**
- 如果两个人同时要修改同一张表格，就需要 **锁**

这就是 Go 并发编程的全部核心概念。听起来很简单对吧？但要把它们用好，你需要理解背后的细节。

> 本文假定你是一个 Go 新手，对并发只有模糊的概念。我会用大量生活比喻和可运行的代码示例，带你从零掌握 Go 的并发编程和各类锁的使用。每个概念都会配一个"新手常犯的错误"和"正确写法"对照。

读完本文你将能够：

- 用 `go` 关键字启动 goroutine，并理解它和线程的区别
- 用 `channel` 在 goroutine 之间安全地传递数据
- 用 `select` 同时监听多个 channel
- 区分并正确使用 `sync.Mutex`、`sync.RWMutex`、`sync.WaitGroup`、`sync.Once`、`sync.Cond`
- 用 `atomic` 包进行无锁的原子操作
- 识别并发编程中的常见陷阱并避开它们
- 掌握几种最实用的并发模式

---

## 一、goroutine：Go 的并发心脏

### 1.1 什么是 goroutine？

**一句话：goroutine 是 Go 的"轻量级线程"，由 Go 运行时管理，而不是操作系统。**

类比：

| 概念 | 比喻 | 创建成本 | 切换成本 |
|------|------|----------|----------|
| 操作系统线程 | 雇一个全职员工 | ~1MB 内存 | ~1-10 微秒 |
| goroutine | 给自己贴一张便利贴 | ~2KB 栈空间 | ~几十纳秒 |

正因为 goroutine 这么"轻"，你可以在 Go 里同时运行**上百万个** goroutine，而线程最多几千个就撑不住了。

### 1.2 启动一个 goroutine

启动 goroutine 只需要在函数调用前加 `go` 关键字：

```go
package main

import (
    "fmt"
    "time"
)

func sayHello() {
    fmt.Println("Hello from goroutine!")
}

func main() {
    go sayHello() // 启动一个 goroutine，不会阻塞 main
    fmt.Println("Hello from main!")

    time.Sleep(time.Second) // 等一秒，让 goroutine 有机会执行完
}
```

输出可能是：

```
Hello from main!
Hello from goroutine!
```

也可能是：

```
Hello from goroutine!
Hello from main!
```

顺序是不确定的——这就是并发的特点。

### 1.3 新手常犯的错误 #1：main 函数退出太快

```go
// ❌ 错误写法：goroutine 还没来得及执行，main 就结束了
func main() {
    go func() {
        fmt.Println("我不会被打印出来")
    }()
    // main 函数结束 = 整个程序退出，所有 goroutine 被强制终止
}
```

```go
// ✅ 正确写法：用 sync.WaitGroup 等待 goroutine 完成
func main() {
    var wg sync.WaitGroup
    wg.Add(1) // 告诉 WaitGroup："我要等 1 个 goroutine"

    go func() {
        defer wg.Done() // goroutine 结束时通知 WaitGroup
        fmt.Println("我肯定会被打印出来！")
    }()

    wg.Wait() // 阻塞，直到所有 goroutine 都调用了 Done()
}
```

### 1.4 新手常犯的错误 #2：闭包捕获循环变量

这是 Go 新手最容易掉进去的坑：

```go
// ❌ 错误写法：所有 goroutine 都打印 "3 3 3"
func main() {
    for i := 0; i < 3; i++ {
        go func() {
            fmt.Println(i) // i 是循环变量的引用，goroutine 执行时循环早已结束
        }()
    }
    time.Sleep(time.Second)
}
```

为什么？因为 `i` 是同一个变量，3 个 goroutine 启动时循环已经跑完了，`i` 变成了 3。正确的写法有两种：

```go
// ✅ 正确写法 1：通过参数传递（推荐，最清晰）
for i := 0; i < 3; i++ {
    go func(n int) {
        fmt.Println(n) // n 是 goroutine 自己的局部变量
    }(i)
}

// ✅ 正确写法 2：在循环体内创建局部变量（Go 1.22+ 也可以用 for i := range 3）
for i := 0; i < 3; i++ {
    i := i // 创建新的局部变量，遮蔽外层的 i
    go func() {
        fmt.Println(i)
    }()
}
```

### 1.5 goroutine 到底有多轻量？一个实验

```go
package main

import (
    "fmt"
    "runtime"
    "time"
)

func main() {
    // 打印当前的 goroutine 数量
    fmt.Println("启动前 goroutine 数:", runtime.NumGoroutine())

    // 启动 10 万个 goroutine
    for i := 0; i < 100000; i++ {
        go func() {
            time.Sleep(time.Hour) // 让每个 goroutine 都活着，方便观察
        }()
    }

    fmt.Println("启动后 goroutine 数:", runtime.NumGoroutine())
    // 在我的电脑上输出：启动后 goroutine 数: 100002
    // 内存占用大约只多了 200MB 左右——10 万个 goroutine！
}
```

关键数据对比：

| 指标 | 线程 | goroutine |
|------|------|-----------|
| 初始栈大小 | 1MB（固定） | 2KB（可动态增长） |
| 10 万个的内存 | ~100GB（不可能） | ~200MB |
| 创建速度 | 慢（系统调用） | 快（用户态） |
| 切换上下文 | 内核态 | 用户态 |

---

## 二、channel：goroutine 之间的"传纸条"

### 2.1 为什么需要 channel？

Go 社区有一句名言：

> **Don't communicate by sharing memory; share memory by communicating.**
> 不要通过共享内存来通信，而要通过通信来共享内存。

翻译成人话：多个 goroutine 需要交换数据时，**不要**让它们直接操作同一块内存（容易出 bug），**要**让它们通过 channel 传递数据（Go 帮你保证安全）。

channel 就像一个**管道**：一头往里塞数据，另一头往外取数据。管道的类型决定了能传输什么类型的数据。

### 2.2 创建和基本使用

```go
// 创建一个能传 int 的 channel（无缓冲）
ch := make(chan int)

// 创建一个能传 string 的 channel（无缓冲）
chStr := make(chan string)

// 创建一个有缓冲的 channel，缓冲区大小为 3
chBuffered := make(chan int, 3)
```

发送和接收：

```go
ch := make(chan int)

// 在一个 goroutine 中发送
go func() {
    ch <- 42 // 把 42 塞进管道
}()

// 在另一个 goroutine 中接收
value := <-ch // 从管道取出数据
fmt.Println(value) // 42
```

### 2.3 无缓冲 vs 有缓冲 channel

这是理解 channel 最重要的一对概念。我用餐厅传菜来比喻：

**无缓冲 channel（同步 channel）**：`make(chan int)`

就像两个厨师手递手传菜——送菜的人必须等接菜的人**伸手来接**，两个动作同时发生。

```go
ch := make(chan int)

go func() {
    fmt.Println("准备发送...")
    ch <- 42                        // 阻塞！直到有人接收
    fmt.Println("发送成功！")        // 有人在接收后才会打印
}()

time.Sleep(time.Second)
fmt.Println("准备接收...")
value := <-ch                       // 此时发送方的阻塞解除
fmt.Println("接收到:", value)
```

输出：
```
准备发送...
准备接收...
发送成功！
接收到: 42
```

**有缓冲 channel（异步 channel）**：`make(chan int, 3)`

就像在中间放了一个**托盘架**——送菜的人把菜放架子上就能走（只要架子还有空位），接菜的人从架子上取。

```go
ch := make(chan int, 2) // 能放 2 个的托盘架

ch <- 1 // 不阻塞，放架子上
ch <- 2 // 不阻塞，架子还有空位
// ch <- 3 // 阻塞！架子满了，必须等有人取走一个

fmt.Println(<-ch) // 1
fmt.Println(<-ch) // 2
```

用表格总结：

| 特性 | 无缓冲 `make(chan T)` | 有缓冲 `make(chan T, n)` |
|------|----------------------|--------------------------|
| 发送行为 | 必须有人同时在接收才不阻塞 | 缓冲区没满就不阻塞 |
| 接收行为 | 必须有人同时在发送才不阻塞 | 缓冲区没空就不阻塞 |
| 用途 | 同步两个 goroutine | 削峰填谷、解耦生产消费 |
| 类比 | 手递手传菜 | 托盘架传菜 |

### 2.4 关闭 channel

当你不再往 channel 发数据时，应该关闭它：

```go
ch := make(chan int, 3)
ch <- 1
ch <- 2
ch <- 3
close(ch) // 关闭 channel

// 关闭后还能接收剩余数据
fmt.Println(<-ch) // 1
fmt.Println(<-ch) // 2
fmt.Println(<-ch) // 3

// 数据取完后，再接收会得到零值
value, ok := <-ch
fmt.Println(value, ok) // 0 false（ok=false 表示 channel 已关闭且无数据）
```

**新手必记的三条规则：**

1. **往已关闭的 channel 发数据 → panic**
2. **重复关闭 channel → panic**
3. **从已关闭的 channel 接收 → 数据取完后返回零值，不会 panic**

```go
// ❌ 往已关闭的 channel 发数据
ch := make(chan int)
close(ch)
ch <- 1 // panic: send on closed channel

// ❌ 重复关闭
close(ch)
close(ch) // panic: close of closed channel

// ✅ 从已关闭的 channel 接收是安全的
ch := make(chan int, 1)
ch <- 42
close(ch)
fmt.Println(<-ch) // 42
fmt.Println(<-ch) // 0（零值），不会 panic
```

### 2.5 用 range 遍历 channel

```go
ch := make(chan int, 5)

go func() {
    for i := 0; i < 5; i++ {
        ch <- i
    }
    close(ch) // ⚠️ 必须关闭！否则 range 会永远阻塞
}()

// range 会一直读取，直到 channel 关闭
for value := range ch {
    fmt.Println(value)
}
// 输出：0 1 2 3 4（顺序不一定）
```

### 2.6 单向 channel：限制方向，防止误用

单向 channel 通常用在函数参数中，明确该函数"只能发"或"只能收"：

```go
// 这个函数只能往 channel 发数据
func producer(ch chan<- int) {
    for i := 0; i < 5; i++ {
        ch <- i
    }
    close(ch)
}

// 这个函数只能从 channel 收数据
func consumer(ch <-chan int) {
    for value := range ch {
        fmt.Println(value)
    }
}

func main() {
    ch := make(chan int, 5)
    go producer(ch) // 自动把 chan int 转成 chan<- int
    consumer(ch)    // 自动把 chan int 转成 <-chan int
}
```

记法：箭头指向 `chan` 就是"往里塞"，箭头从 `chan` 出来就是"往外取"。
- `chan<-`  = 只能发送（send-only）
- `<-chan`  = 只能接收（receive-only）

### 2.7 新手常犯的错误 #3：channel 死锁

```go
// ❌ 死锁：无缓冲 channel，发送和接收在同一个 goroutine
func main() {
    ch := make(chan int)
    ch <- 1  // 阻塞！没有人接收
    <-ch     // 永远执行不到这里
    // fatal error: all goroutines are asleep - deadlock!
}
```

```go
// ✅ 正确：发送和接收在不同的 goroutine
func main() {
    ch := make(chan int)
    go func() {
        ch <- 1
    }()
    fmt.Println(<-ch) // 1
}
```

---

## 三、select：同时监听多个 channel

### 3.1 基本语法

`select` 就像在多个 channel 上"同时等待"，哪个 channel 先有数据就处理哪个：

```go
select {
case value := <-ch1:
    fmt.Println("从 ch1 收到:", value)
case value := <-ch2:
    fmt.Println("从 ch2 收到:", value)
case ch3 <- 42:
    fmt.Println("向 ch3 发送成功")
default:
    fmt.Println("没有任何 channel 就绪")
}
```

关键规则：
- 如果有多个 case 同时就绪，**随机选一个**执行（防止某个 case 饿死）
- 如果没有 case 就绪且有 `default`，执行 `default`
- 如果没有 case 就绪且没有 `default`，**阻塞等待**

### 3.2 超时控制

```go
func fetchData() string {
    time.Sleep(2 * time.Second)
    return "数据来了"
}

func main() {
    ch := make(chan string)

    go func() {
        ch <- fetchData()
    }()

    select {
    case result := <-ch:
        fmt.Println("成功获取:", result)
    case <-time.After(1 * time.Second):
        fmt.Println("超时了！等太久不等了")
    }
}
// 输出：超时了！等太久不等了
```

`time.After(d)` 返回一个 channel，在 `d` 时间后会往这个 channel 发一个值。把它放在 select 里，就实现了超时控制。

### 3.3 优雅退出：用 channel 发"停止信号"

```go
func worker(stop <-chan struct{}) {
    for {
        select {
        case <-stop:
            fmt.Println("收到停止信号，收工！")
            return
        default:
            fmt.Println("工作中...")
            time.Sleep(500 * time.Millisecond)
        }
    }
}

func main() {
    stop := make(chan struct{}) // struct{} 不占内存，专门用于发信号
    go worker(stop)

    time.Sleep(2 * time.Second)
    close(stop) // 关闭 channel 后，所有接收者都会立即收到零值
    time.Sleep(time.Second)
}
```

### 3.4 新手常犯的错误 #4：select 和已关闭的 channel

```go
// ❌ 危险：从已关闭的 channel 接收会不断返回零值
ch := make(chan int)
close(ch)

for {
    select {
    case v := <-ch:
        fmt.Println(v) // 疯狂打印 0 0 0 0 0 ...
    }
}
```

```go
// ✅ 正确：用 ok 判断 channel 是否关闭
for {
    select {
    case v, ok := <-ch:
        if !ok {
            fmt.Println("channel 已关闭，退出")
            return
        }
        fmt.Println(v)
    }
}
```

**实用技巧**：把已关闭的 channel 设成 `nil`，select 就会跳过它：

```go
var ch chan int = make(chan int)

// ... 某处 close(ch)

// 关闭后置 nil
ch = nil
// select 中 nil channel 的 case 永远不会被选中，完美!
```

---

## 四、sync.Mutex：互斥锁——"我正在用，你等会儿"

### 4.1 为什么需要锁？

先看一个没有锁的灾难现场：

```go
// ❌ 竞态条件：counter 最终不一定是 100000
func main() {
    var counter int
    var wg sync.WaitGroup

    for i := 0; i < 100000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            counter++ // 这不是原子操作！
        }()
    }

    wg.Wait()
    fmt.Println("counter =", counter) // 可能是 98762、99234... 每次都不一样
}
```

为什么 `counter++` 不是原子的？

```
counter++ 在 CPU 层面其实是三步：
1. LOAD:   从内存读取 counter 的值到寄存器
2. ADD:    寄存器里的值 +1
3. STORE:  把新值写回内存

如果两个 goroutine 同时执行：

时间线：
goroutine A: LOAD counter (读到 42)    → ADD (43)    → STORE (43)
goroutine B:     LOAD counter (读到 42) → ADD (43) → STORE (43)

结果：加了两次，counter 只增加了 1！其中一个 +1 被"吞掉"了。
```

这就是**竞态条件（Race Condition）**。

### 4.2 用 Mutex 保护共享变量

Mutex（互斥锁）就像一个**厕所的门**——一次只能进去一个人，进去的人锁门，外面的人排队等。

```go
// ✅ 用 Mutex 保护 counter
func main() {
    var counter int
    var mu sync.Mutex
    var wg sync.WaitGroup

    for i := 0; i < 100000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            mu.Lock()   // 锁门
            counter++   // 安全地 +1
            mu.Unlock() // 开门
        }()
    }

    wg.Wait()
    fmt.Println("counter =", counter) // 稳稳的 100000
}
```

### 4.3 Mutex 的核心方法

```go
var mu sync.Mutex

mu.Lock()    // 加锁。如果锁已被别人持有，阻塞等待
// ... 临界区代码 ...
mu.Unlock()  // 解锁。必须在 Lock 之后调用，否则 panic

// ⚠️ 试试用 defer 防止忘记解锁（强烈推荐）
mu.Lock()
defer mu.Unlock()
// ... 临界区代码 ...（即使 panic 也会解锁）
```

### 4.4 新手常犯的错误 #5：Lock 之后忘记 Unlock

```go
// ❌ 错误：如果中间 return 了，Unlock 永远执行不到
func update(data map[string]int, key string) {
    mu.Lock()
    if data[key] > 100 {
        return // 💀 锁没释放！之后所有人都卡死
    }
    data[key]++
    mu.Unlock()
}
```

```go
// ✅ 正确：defer 大法
func update(data map[string]int, key string) {
    mu.Lock()
    defer mu.Unlock() // 无论如何都会解锁
    if data[key] > 100 {
        return // defer 确保 Unlock 一定会执行
    }
    data[key]++
}
```

### 4.5 新手常犯的错误 #6：复制含有 Mutex 的结构体

```go
// ❌ 错误：Mutex 被复制，两把"不同"的锁
type Counter struct {
    mu    sync.Mutex
    value int
}

func (c Counter) Increment() { // 值接收者！c 是副本
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++ // 修改的是副本的 value，原值不变
}
```

```go
// ✅ 正确：用指针接收者
func (c *Counter) Increment() { // 指针接收者
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++
}
```

### 4.6 用 `go run -race` 检测竞态条件

Go 自带竞态检测器，太好用了：

```bash
go run -race main.go
```

如果有竞态条件，它会精确告诉你哪个 goroutine 在读写哪块内存：

```
WARNING: DATA RACE
Read at 0x00c000012345 by goroutine 7:
  main.main.func1()
      main.go:15 +0x3c

Previous write at 0x00c000012345 by goroutine 6:
  main.main.func1()
      main.go:15 +0x52
```

养成习惯：**写并发代码时，永远用 `-race` 跑一遍。**

---

## 五、sync.RWMutex：读写锁——"你可以一起看，但我要独自写"

### 5.1 为什么需要读写锁？

Mutex 的问题：哪怕 100 个 goroutine 都只是**读**数据（互不影响），也得排队——因为 Mutex 不区分读和写。

RWMutex 更聪明：**允许多个读者同时持有读锁，但写者独占地持有写锁。**

|  | 读锁 | 写锁 |
|------|------|------|
| 读锁 | ✅ 可以共存 | ❌ 互斥 |
| 写锁 | ❌ 互斥 | ❌ 互斥 |

形象比喻：
- **读锁** = 图书馆的书，多人可以同时看同一本
- **写锁** = 图书馆管理员在修订这本书，修订期间所有人不能看

### 5.2 基本用法

```go
var (
    cache   = make(map[string]string)
    rwMu    sync.RWMutex
)

// 读操作：用读锁
func get(key string) string {
    rwMu.RLock()         // 加读锁（其他人也能同时加读锁）
    defer rwMu.RUnlock() // 解读锁
    return cache[key]
}

// 写操作：用写锁
func set(key, value string) {
    rwMu.Lock()         // 加写锁（独占，所有读锁和写锁都得等）
    defer rwMu.Unlock() // 解写锁
    cache[key] = value
}
```

### 5.3 什么时候用 RWMutex 而不是 Mutex？

**大量读、少量写**的场景。比如：
- 配置管理：配置偶尔更新，大部分时间都在读
- 缓存系统：缓存偶尔刷新，大部分时间都在查
- 路由表：路由偶尔变更，大部分时间在查表

简单测试一下性能差异：

```go
func BenchmarkMutex(b *testing.B) {
    var mu sync.Mutex
    var value int

    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            mu.Lock()
            _ = value // 读
            mu.Unlock()
        }
    })
}

func BenchmarkRWMutex(b *testing.B) {
    var rwMu sync.RWMutex
    var value int

    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            rwMu.RLock()
            _ = value // 读
            rwMu.RUnlock()
        }
    })
}
// RWMutex 在读密集场景下快几倍到几十倍
```

### 5.4 新手常犯的错误 #7：拿着读锁去加写锁

```go
// ❌ 死锁！
func upgrade() {
    rwMu.RLock()
    // ... 读到一些数据后，想升级成写锁 ...
    rwMu.Lock() // 💀 死锁！读锁没释放，写锁永远等不到
    // ...
    rwMu.Unlock()
    rwMu.RUnlock()
}
```

```go
// ✅ 正确：先释放读锁，再加写锁
func upgrade() {
    rwMu.RLock()
    data := cache["key"] // 读出数据
    rwMu.RUnlock()       // 释放读锁

    rwMu.Lock()          // 加写锁
    cache["key"] = data + " updated"
    rwMu.Unlock()
}
```

---

## 六、sync.WaitGroup：等人齐了再出发

### 6.1 基本概念

WaitGroup 就像一个**导游举的小旗子**——"大家别走散，人齐了再出发！"

核心三个方法：

| 方法 | 含义 | 比喻 |
|------|------|------|
| `wg.Add(n)` | 我要等 n 个 goroutine | 导游数人数："一共 5 个人" |
| `wg.Done()` | 我这干完了 | 游客说："我到齐了！" |
| `wg.Wait()` | 阻塞，等所有人都 Done | 导游等着，人齐了才走 |

### 6.2 基本用法

```go
func main() {
    var wg sync.WaitGroup

    for i := 0; i < 5; i++ {
        wg.Add(1) // 每启动一个 goroutine，计数 +1
        go func(id int) {
            defer wg.Done() // goroutine 结束时计数 -1
            fmt.Printf("工人 %d 完成工作\n", id)
        }(i)
    }

    wg.Wait() // 阻塞，直到计数为 0
    fmt.Println("所有工人完成！")
}
```

### 6.3 新手常犯的错误 #8：Add 的位置不对

```go
// ❌ 错误：Add 放在 goroutine 里面
// wg.Wait() 可能在 Add(1) 执行前就已经返回了！
for i := 0; i < 5; i++ {
    go func(id int) {
        wg.Add(1)       // 太晚了！main goroutine 可能已经 Wait 完毕
        defer wg.Done()
    }(i)
}
wg.Wait()
```

```go
// ✅ 正确：Add 在启动 goroutine 之前
for i := 0; i < 5; i++ {
    wg.Add(1)          // 先登记
    go func(id int) {
        defer wg.Done() // 再干活
    }(i)
}
wg.Wait()
```

> 记住：**`Add` 必须在 `Wait` 所在的 goroutine 中、在启动子 goroutine 之前调用。** 或者说：把 `Add` 放在离 `go` 关键字尽可能近的地方。

### 6.4 实战：并发下载多个 URL

```go
func downloadAll(urls []string) {
    var wg sync.WaitGroup

    for _, url := range urls {
        wg.Add(1)
        go func(u string) {
            defer wg.Done()
            resp, err := http.Get(u)
            if err != nil {
                fmt.Printf("下载 %s 失败: %v\n", u, err)
                return
            }
            defer resp.Body.Close()
            fmt.Printf("下载 %s 成功，状态码: %d\n", u, resp.StatusCode)
        }(url) // ⚠️ 把 url 作为参数传入，避免闭包陷阱
    }

    wg.Wait()
    fmt.Println("全部下载完成！")
}
```

---

## 七、sync.Once：这辈子只做一次

### 7.1 为什么需要 Once？

很多操作只需要做一次——初始化配置、建立数据库连接、加载配置文件。如果每个 goroutine 都做一遍，不仅浪费，还可能出错。

`sync.Once` 保证：**无论多少个 goroutine 同时调用，它包裹的函数只执行一次。**

### 7.2 基本用法

```go
var (
    config map[string]string
    once   sync.Once
)

func getConfig() map[string]string {
    once.Do(func() {
        // 这段代码只会执行一次，无论多少 goroutine 同时调用
        fmt.Println("加载配置文件...")
        config = map[string]string{
            "host": "localhost",
            "port": "8080",
        }
    })
    return config
}

func main() {
    var wg sync.WaitGroup

    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            cfg := getConfig()
            fmt.Println(cfg["host"]) // 所有 goroutine 拿到的是同一份配置
        }()
    }

    wg.Wait()
    // "加载配置文件..." 只打印一次！
}
```

### 7.3 Once 的实现原理（简化版）

```go
// sync.Once 的核心逻辑（简化版）
type Once struct {
    done uint32  // 原子标志位
    m    Mutex
}

func (o *Once) Do(f func()) {
    if atomic.LoadUint32(&o.done) == 0 { // 快速路径：已经执行过就直接返回
        o.doSlow(f)
    }
}

func (o *Once) DoSlow(f func()) {
    o.m.Lock()
    defer o.m.Unlock()
    if o.done == 0 {    // 双重检查
        defer atomic.StoreUint32(&o.done, 1)
        f()              // 执行函数
    }
}
```

这个实现很精妙：
1. **快速路径**：大多数调用只做一次原子读，不加锁
2. **双重检查**：加锁后再检查一次，防止多 goroutine 同时进入慢路径
3. **先设标志再执行**：`defer` 保证即使 `f()` panic，`done` 也会被设为 1

### 7.4 新手常犯的错误 #9：Once 中的函数 panic

```go
var once sync.Once

// ❌ 注意：如果 Do 里的函数 panic，Once 会认为已经执行过了
once.Do(func() {
    panic("出错了")
})
// once 的 done 标志被设为 1
// 下次调用不会重试！
once.Do(func() {
    fmt.Println("不会被执行")
})
```

结论：`sync.Once.Do` 中的函数应该是**幂等且不太可能失败**的操作。如果可能失败，考虑在函数内部自己处理错误。

---

## 八、sync.Cond：条件变量——"等你准备好了叫我"

### 8.1 为什么需要 Cond？

有些场景下，goroutine 需要在某个条件满足时才继续执行。比如：
- 队列里有数据了，消费者才能消费
- 缓冲区有空位了，生产者才能继续生产

最朴素的想法是轮询（忙等）：

```go
// ❌ 忙等：浪费 CPU
for len(queue) == 0 {
    time.Sleep(time.Millisecond) // 睡一下再查
}
```

更好的办法：让 goroutine **睡觉**，等条件满足时**被叫醒**。这就是 `sync.Cond`。

### 8.2 基本用法

Cond 必须和一个 Locker（通常是 Mutex）配合使用：

```go
var (
    mu    sync.Mutex
    cond  = sync.NewCond(&mu)
    queue []int
)

// 生产者
func producer() {
    for i := 0; i < 5; i++ {
        mu.Lock()
        queue = append(queue, i)
        fmt.Println("生产:", i)
        mu.Unlock()

        cond.Signal() // 通知一个等待的消费者："有货啦！"
        time.Sleep(time.Second)
    }
}

// 消费者
func consumer(id int) {
    for {
        mu.Lock()
        for len(queue) == 0 {
            cond.Wait() // 睡觉，等信号
            // Wait 返回时会自动重新加锁
        }
        item := queue[0]
        queue = queue[1:]
        fmt.Printf("消费者 %d 消费: %d\n", id, item)
        mu.Unlock()
    }
}
```

### 8.3 Cond 的三个方法

| 方法 | 含义 |
|------|------|
| `cond.Wait()` | 释放锁 → 阻塞等待 → 被唤醒后重新加锁。**必须持有锁才能调用。** |
| `cond.Signal()` | 唤醒一个正在 Wait 的 goroutine |
| `cond.Broadcast()` | 唤醒所有正在 Wait 的 goroutine |

### 8.4 新手常犯的错误 #10：Wait 不用 for 循环

```go
// ❌ 用 if 而不是 for
mu.Lock()
if len(queue) == 0 {  // 醒来后不重新检查条件
    cond.Wait()
}
item := queue[0] // 如果被"虚假唤醒"，这里可能 panic
```

```go
// ✅ 用 for 循环（Go 文档强烈建议）
mu.Lock()
for len(queue) == 0 { // 醒来后重新检查条件
    cond.Wait()
}
item := queue[0] // 安全
```

为什么要 `for` 而不是 `if`？两个原因：

1. **虚假唤醒**：操作系统可能无故唤醒等待的线程（虽然 Go 的实现不太可能，但标准文档建议防御性编程）
2. **被别的 goroutine 捷足先登**：Signal 唤醒了你，但在你拿到锁之前，另一个 goroutine 可能抢先消费了数据

### 8.5 Cond 实战：有限容量的生产者-消费者

```go
func main() {
    var (
        mu     sync.Mutex
        notEmpty = sync.NewCond(&mu) // 队列不空的条件
        notFull  = sync.NewCond(&mu) // 队列不满的条件
        queue    = make([]int, 0, 3) // 容量为 3 的队列
    )

    // 生产者
    go func() {
        for i := 0; i < 10; i++ {
            mu.Lock()
            for len(queue) == 3 {
                notFull.Wait() // 队列满了，等消费者腾地方
            }
            queue = append(queue, i)
            fmt.Println("生产:", i, "队列:", queue)
            notEmpty.Signal() // 通知消费者：有货了
            mu.Unlock()
        }
    }()

    // 消费者
    for i := 0; i < 10; i++ {
        mu.Lock()
        for len(queue) == 0 {
            notEmpty.Wait() // 队列空了，等生产者上货
        }
        item := queue[0]
        queue = queue[1:]
        fmt.Println("消费:", item, "队列:", queue)
        notFull.Signal() // 通知生产者：有空位了
        mu.Unlock()
    }
}
```

> **实际上大部分场景用 channel 更简洁**。Cond 适用于 channel 不好表达的复杂条件同步场景。

---

## 九、atomic：无锁的原子操作

### 9.1 什么是原子操作？

**原子操作 = 不可分割的操作 = 要么全做完要么全没做，中间不会被别的 goroutine 打断。**

常见的原子操作：
- 读一个整数
- 写一个整数
- 把一个整数 +1
- 比较并交换（CAS：Compare And Swap）

Go 的 `sync/atomic` 包提供了这些操作的原子版本。

### 9.2 什么时候用 atomic 而不是 Mutex？

| 场景 | 推荐 | 原因 |
|------|------|------|
| 保护一个整数（计数器、标志位） | `atomic` | 更快，无锁 |
| 保护复杂的数据结构（map、slice） | `Mutex` | atomic 只能保护单个值 |
| 保护一段代码逻辑 | `Mutex` | atomic 保护不了代码块 |

简单说：**只读/写/改一个值 → atomic；保护一段逻辑 → Mutex。**

### 9.3 常用 atomic 操作

```go
import "sync/atomic"

var counter int64 // ⚠️ atomic 操作只支持特定的类型

// 原子加
atomic.AddInt64(&counter, 1) // counter++ 的原子版本

// 原子读
value := atomic.LoadInt64(&counter)

// 原子写
atomic.StoreInt64(&counter, 100)

// 比较并交换（CAS）：如果 counter 的值是 100，就改成 200
swapped := atomic.CompareAndSwapInt64(&counter, 100, 200)
// swapped 为 true 表示修改成功，false 表示 counter 当前值不是 100

// 原子交换：把新值存进去，返回旧值
old := atomic.SwapInt64(&counter, 500)
```

### 9.4 用 atomic 实现无锁计数器

```go
func main() {
    var counter int64
    var wg sync.WaitGroup

    for i := 0; i < 100000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            atomic.AddInt64(&counter, 1) // 无锁但安全
        }()
    }

    wg.Wait()
    fmt.Println("counter =", atomic.LoadInt64(&counter)) // 稳稳的 100000
}
```

### 9.5 用 atomic 实现自旋锁（了解即可）

```go
type SpinLock struct {
    flag int32
}

func (s *SpinLock) Lock() {
    for !atomic.CompareAndSwapInt32(&s.flag, 0, 1) {
        // 不停尝试，直到成功
        runtime.Gosched() // 让出 CPU，避免完全空转
    }
}

func (s *SpinLock) Unlock() {
    atomic.StoreInt32(&s.flag, 0)
}
```

> ⚠️ 自旋锁在 Go 中很少直接用，了解即可。Go 的 `sync.Mutex` 已经做了自旋优化。

### 9.6 Go 1.19+ 新增的 atomic 类型

从 Go 1.19 开始，`sync/atomic` 引入了类型安全的泛型封装，强烈推荐：

```go
// 旧方式（易出错，类型不安全）
var counter int64
atomic.AddInt64(&counter, 1)

// 新方式（类型安全，不会写错类型）
var counter atomic.Int64
counter.Add(1)               // 原子加
value := counter.Load()      // 原子读
counter.Store(100)           // 原子写
swapped := counter.CompareAndSwap(100, 200) // CAS
old := counter.Swap(500)     // 交换
```

可用的类型：
- `atomic.Bool`
- `atomic.Int32` / `atomic.Int64` / `atomic.Uint32` / `atomic.Uint64`
- `atomic.Uintptr`（原子指针）
- `atomic.Pointer[T]`（泛型原子指针，Go 1.19+）
- `atomic.Value`（可以存任意类型，但慢一点）

### 9.7 atomic.Value：原子存储任意类型

```go
var config atomic.Value // 可以原子地存取任意类型

// 存储
config.Store(MyConfig{Host: "localhost", Port: 8080})

// 读取
cfg := config.Load().(MyConfig) // 需要类型断言
fmt.Println(cfg.Host)
```

---

## 十、sync.Map：并发安全的 Map

### 10.1 为什么不能直接用普通 map？

```go
// ❌ 并发写 map 会 panic！
var m = make(map[string]int)

go func() {
    for i := 0; i < 1000; i++ {
        m["key"] = i // 并发写
    }
}()

go func() {
    for i := 0; i < 1000; i++ {
        m["key"] = i // 并发写
    }
}()

// fatal error: concurrent map writes
```

### 10.2 三种方案对比

| 方案 | 写法 | 适合场景 |
|------|------|----------|
| `Mutex + map` | 自己加锁 | 写多读也多的场景 |
| `RWMutex + map` | 自己加读写锁 | 读多写少的场景 |
| `sync.Map` | 直接用 | 读多写少，且 key 的集合相对稳定 |

### 10.3 sync.Map 的基本用法

```go
var sm sync.Map

// 存储
sm.Store("name", "小明")
sm.Store("age", 18)

// 读取
value, ok := sm.Load("name")
if ok {
    fmt.Println(value.(string)) // 小明（需要类型断言）
}

// 读取，如果没有就存一个
actual, loaded := sm.LoadOrStore("score", 100)
fmt.Println(actual, loaded) // 100 false（首次存入，loaded=false）

actual, loaded = sm.LoadOrStore("score", 200)
fmt.Println(actual, loaded) // 100 true（已存在，loaded=true，返回旧值）

// 删除
sm.Delete("age")

// 遍历
sm.Range(func(key, value any) bool {
    fmt.Println(key, value)
    return true // 返回 false 会停止遍历
})
```

### 10.4 sync.Map 的内部原理（简化理解）

`sync.Map` 内部维护了两套 map：
- **read map**（只读 map）：原子操作访问，不加锁，很快
- **dirty map**（脏 map）：需要加锁访问，存放新写入的数据

流程：
- 读：先查 read map（无锁），没找到再查 dirty map（加锁）
- 写：直接写 dirty map（加锁）
- 当 dirty map 里的 key 被频繁访问时，会提升到 read map

这就是为什么 sync.Map 适合"读多写少且 key 稳定"的场景。

### 10.5 什么时候该用 sync.Map？（官方文档的说明）

> sync.Map 针对以下两种场景优化：
> 1. **某个 key 只写一次，但读很多次**（比如缓存只增长的条目）
> 2. **多个 goroutine 读、写、覆盖不相交的 key 集合**

**大部分时候**，用 `Mutex + map` 或 `RWMutex + map` 就够了，代码更直观。

---

## 十一、context：并发控制的指挥官

### 11.1 为什么需要 context？

在实际开发中，我们经常需要：
- 给一个操作设置超时时间
- 在多个 goroutine 之间传递取消信号
- 传递请求范围的值（如 trace ID、user ID）

`context` 包就是为这些需求而生的。

### 11.2 context 的四种创建方式

```go
// 1. 根 context（通常放在 main 或请求入口）
ctx := context.Background()

// 2. 空 context（当不确定用哪个时，和 Background 类似）
ctx := context.TODO()

// 3. 带超时的 context
ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
defer cancel() // ⚠️ 务必调用 cancel 释放资源

// 4. 带截止时间的 context
deadline := time.Now().Add(5 * time.Second)
ctx, cancel := context.WithDeadline(context.Background(), deadline)
defer cancel()

// 5. 带取消的 context
ctx, cancel := context.WithCancel(context.Background())
defer cancel()

// 6. 带值的 context
ctx := context.WithValue(context.Background(), "traceID", "abc123")
```

### 11.3 实战：用 context 实现超时控制

```go
func fetchWithTimeout(ctx context.Context, url string) error {
    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return err
    }

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return err // 超时会返回 context.DeadlineExceeded
    }
    defer resp.Body.Close()

    // 处理响应...
    return nil
}

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()

    if err := fetchWithTimeout(ctx, "https://httpbin.org/delay/5"); err != nil {
        fmt.Println("请求失败:", err) // 2 秒后超时
    }
}
```

### 11.4 实战：手动取消多个 goroutine

```go
func worker(ctx context.Context, id int) {
    for {
        select {
        case <-ctx.Done(): // ctx 被取消时，这个 channel 会关闭
            fmt.Printf("工人 %d: 收到取消信号，收工\n", id)
            return
        default:
            fmt.Printf("工人 %d: 工作中...\n", id)
            time.Sleep(500 * time.Millisecond)
        }
    }
}

func main() {
    ctx, cancel := context.WithCancel(context.Background())

    // 启动 3 个工人
    for i := 0; i < 3; i++ {
        go worker(ctx, i)
    }

    time.Sleep(2 * time.Second)
    fmt.Println("老板: 到点了，所有人下班！")
    cancel() // 通知所有人停止

    time.Sleep(time.Second)
    fmt.Println("主程序退出")
}
```

### 11.5 context 使用规范

```
✅ 正确：
- 把 context 作为函数的第一个参数
- 用 context.WithTimeout/WithDeadline 处理外部调用
- defer cancel()

❌ 错误：
- 把 context 存到 struct 里（除非是 http.Request 这种特殊情况）
- 传 nil context（不确定用啥就用 context.TODO()）
- 用 context.WithValue 传可选参数（应该用函数参数）
```

---

## 十二、并发模式实战

### 12.1 模式一：Fan-Out / Fan-In（扇出/扇入）

**扇出**：一个输入，分发给多个 worker 并行处理
**扇入**：多个 worker 的结果汇总到一个 channel

```go
func fanOutFanIn() {
    jobs := make(chan int, 100)
    results := make(chan int, 100)

    // 扇出：启动 5 个 worker
    for w := 0; w < 5; w++ {
        go func(id int) {
            for job := range jobs {
                fmt.Printf("Worker %d 处理任务 %d\n", id, job)
                results <- job * 2 // 计算结果
            }
        }(w)
    }

    // 发送任务
    go func() {
        for i := 0; i < 20; i++ {
            jobs <- i
        }
        close(jobs) // 任务发完了，关闭 channel
    }()

    // 扇入：汇总结果
    go func() {
        for i := 0; i < 20; i++ {
            result := <-results
            fmt.Println("结果:", result)
        }
        close(results)
    }()
}
```

### 12.2 模式二：Pipeline（流水线）

数据像流水线一样经过多个阶段处理：

```go
// 阶段 1：生成数字
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        for _, n := range nums {
            out <- n
        }
        close(out)
    }()
    return out
}

// 阶段 2：平方
func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        for n := range in {
            out <- n * n
        }
        close(out)
    }()
    return out
}

// 阶段 3：转成字符串
func toString(in <-chan int) <-chan string {
    out := make(chan string)
    go func() {
        for n := range in {
            out <- fmt.Sprintf("结果: %d", n)
        }
        close(out)
    }()
    return out
}

func main() {
    // 流水线：generate → square → toString
    for result := range toString(square(generate(1, 2, 3, 4, 5))) {
        fmt.Println(result)
    }
}
```

### 12.3 模式三：Worker Pool（工作池）

固定数量的 worker 处理海量任务：

```go
func workerPool() {
    const numWorkers = 5
    const numJobs = 20

    jobs := make(chan int, numJobs)
    results := make(chan int, numJobs)

    // 创建固定数量的 worker
    var wg sync.WaitGroup
    for w := 0; w < numWorkers; w++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for job := range jobs {
                fmt.Printf("Worker %d 处理任务 %d\n", id, job)
                time.Sleep(100 * time.Millisecond) // 模拟工作
                results <- job * 2
            }
        }(w)
    }

    // 发送任务
    for j := 0; j < numJobs; j++ {
        jobs <- j
    }
    close(jobs)

    // 等所有 worker 完成后关闭 results
    go func() {
        wg.Wait()
        close(results)
    }()

    // 收集结果
    for result := range results {
        fmt.Println("结果:", result)
    }
}
```

### 12.4 模式四：errgroup——并行任务中收集错误

`golang.org/x/sync/errgroup` 是 Go 官方扩展库，专门用于"一组并行任务中，任何一个出错就全部取消"：

```go
import "golang.org/x/sync/errgroup"

func main() {
    g, ctx := errgroup.WithContext(context.Background())

    urls := []string{
        "https://www.google.com",
        "https://www.github.com",
        "https://www.invalid-url-that-does-not-exist.com",
    }

    for _, url := range urls {
        url := url // 闭包陷阱
        g.Go(func() error {
            req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
            if err != nil {
                return err
            }
            resp, err := http.DefaultClient.Do(req)
            if err != nil {
                return err
            }
            defer resp.Body.Close()
            fmt.Println(url, "→", resp.Status)
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        fmt.Println("有请求失败:", err)
    }
}
```

---

## 十三、常见陷阱速查表

| # | 陷阱 | 后果 | 正确做法 |
|---|------|------|----------|
| 1 | main 函数退出太早 | goroutine 没执行完就被杀 | 用 WaitGroup 等待 |
| 2 | 闭包捕获循环变量 | 所有 goroutine 拿到同一个值 | 通过参数传入或 `i := i` |
| 3 | 无缓冲 channel 在本 goroutine 收发 | 死锁 | 收发必须在不同 goroutine |
| 4 | 往已关闭的 channel 发数据 | panic | 由发送方关闭 channel |
| 5 | Lock 之后忘记 Unlock | 死锁 | `defer mu.Unlock()` |
| 6 | 复制含有 Mutex 的结构体 | 锁失效 | 用指针接收者和指针传递 |
| 7 | 拿着读锁去加写锁 | 死锁 | 先释放读锁再加写锁 |
| 8 | WaitGroup.Add 放在 goroutine 里 | Wait 可能提前返回 | Add 在 go 关键字之前 |
| 9 | sync.Once 中的函数 panic | 不会重试 | Once 内的函数应该简单可靠 |
| 10 | Cond.Wait 后用 if 而非 for | 虚假唤醒导致 bug | 永远用 for 循环 |
| 11 | 并发读写普通 map | panic | 加锁或用 sync.Map |
| 12 | context 没有 defer cancel() | 内存泄漏 | 拿到 cancel 后立刻 defer |
| 13 | 忘记用 `-race` 检测 | 上线后随机 bug | 开发测试时必带 `-race` |

---

## 十四、一张图总结：什么时候用什么？

```
我需要多个 goroutine...
│
├── 它们需要通信/传递数据？
│   ├── 一对一简单传递 → channel（无缓冲=同步，有缓冲=异步）
│   ├── 一对多广播 → close(channel) 来通知
│   └── 复杂条件同步 → sync.Cond
│
├── 它们共享一个变量？
│   ├── 只是一个整数/布尔/指针 → atomic
│   └── 是复杂结构 → sync.Mutex 或 sync.RWMutex
│
├── 我需要等它们全部完成？
│   └── sync.WaitGroup
│
├── 某个初始化只需要做一次？
│   └── sync.Once
│
├── 需要超时/取消控制？
│   └── context.WithTimeout / context.WithCancel
│
└── 它们共享一个 map？
    ├── 写多读也多的普通场景 → sync.Mutex + map
    ├── 读多写少 → sync.RWMutex + map
    └── 读极多写极少且 key 稳定 → sync.Map
```

---

## 十五、总结

回到最开始那家银行：

| 银行概念 | Go 概念 | 核心要点 |
|----------|---------|----------|
| 排队的人 | **goroutine** | go 关键字启动，轻量级，几百万个不是问题 |
| 传纸条 | **channel** | goroutine 之间安全通信的管道 |
| 多窗口喊号 | **select** | 同时监听多个 channel |
| 填表时锁抽屉 | **sync.Mutex** | 保护临界区，一次一个人用 |
| 多人看同一本册子 | **sync.RWMutex** | 大家可以一起读，但写的人独享 |
| 人齐了再出发 | **sync.WaitGroup** | 等所有 goroutine 完成 |
| 银行开门只放一次音乐 | **sync.Once** | 只执行一次的操作 |
| 大堂经理举牌通知 | **sync.Cond** | 条件满足时唤醒等待的 goroutine |
| 电子计数器 | **atomic** | 轻量级原子操作，无需加锁 |
| 营业时间到就关门 | **context** | 超时和取消控制 |

学习并发编程的最好方式：**写代码，跑 `-race`，看报错，改代码。** 光看文章是学不会并发的。

**下一步建议：**

1. 把本文的代码示例都敲一遍，每个都加上 `go run -race` 跑一跑
2. 找一个你能想到的场景（比如聊天室、爬虫、文件下载器），用 Go 的并发实现出来
3. 阅读 Go 官方文档：[Effective Go - Concurrency](https://go.dev/doc/effective_go#concurrency)
4. 阅读 Go 官方博客：[Go Concurrency Patterns](https://go.dev/blog/pipelines)
5. 读一读 `sync` 包的源码——它只有几百行，注释写得非常好

> 并发不是银弹。**不要为了并发而并发**。先写出正确的串行代码，然后只在真正需要的地方引入并发。
