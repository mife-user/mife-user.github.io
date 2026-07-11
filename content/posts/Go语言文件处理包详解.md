---
title: 'Go语言文件处理包详解：os、io、bufio、filepath、fs、embed'
date: 2026-07-10T15:00:00+08:00
draft: false
tags: ["Go", "文件处理", "os", "io", "bufio", "filepath", "fs", "embed"]
---

Go 的标准库对文件处理提供了分层抽象的 API。底层是 `os` 包负责系统调用，中间是 `io` 包定义读写接口，上层是 `bufio` 提供缓冲、`filepath` 处理路径、`fs` 提供文件系统抽象、`embed` 在编译时嵌入文件。

## 一、os 包：文件的基础操作

`os` 包直接封装操作系统的文件 API。在 Unix 上调用 `open(2)`/`read(2)`/`write(2)`，在 Windows 上调用对应的 Win32 API。

### 1.1 打开和创建文件

```go
// 只读方式打开
f, err := os.Open("config.yaml")
if err != nil {
    // 文件不存在、权限不足等都会导致 err != nil
    log.Fatal(err)
}
defer f.Close()

// 指定 flag 和权限打开
f, err = os.OpenFile("data.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
```

`OpenFile` 的 flag 参数是位掩码，常用组合：

| Flag | 行为 |
|------|------|
| `os.O_RDONLY` | 只读 |
| `os.O_WRONLY` | 只写 |
| `os.O_RDWR` | 读写 |
| `os.O_CREATE` | 不存在则创建 |
| `os.O_APPEND` | 写入追加到末尾 |
| `os.O_TRUNC` | 打开时清空文件 |
| `os.O_EXCL` | 与 `O_CREATE` 合用，文件已存在则失败 |

> ⚠️ `os.O_WRONLY|os.O_CREATE` 和 `os.O_WRONLY|os.O_CREATE|os.O_TRUNC` 是两种最常见的写文件模式。前者保留已有内容并从文件头开始覆盖写入，后者清空后从头写。如果你要追加日志，必须加 `os.O_APPEND`，否则每次 `Write` 都会从位置 0 开始覆盖。

```go
// 创建新文件（等价于 OpenFile(name, O_RDWR|O_CREATE|O_TRUNC, 0666)）
f, err := os.Create("output.txt")
```

`os.Create` 有一个不那么直观的行为：如果文件已存在，它会被截断（truncate），而不是 append。很多人以为 Create 相当于 "touch"，实际上它会清空已有内容。

### 1.2 读取文件

```go
// 一次性读全部内容（小文件适用）
data, err := os.ReadFile("config.yaml")
// data 是 []byte

// 分块读取（大文件必须这样，否则内存爆炸）
f, _ := os.Open("large_file.bin")
buf := make([]byte, 32*1024) // 32KB 缓冲区
for {
    n, err := f.Read(buf)
    if err == io.EOF {
        break
    }
    // 处理 buf[:n]
    process(buf[:n])
}
```

`f.Read(buf)` 的行为和 C 的 `read(2)` 类似：`n` 可能小于 `len(buf)`，不代表已经读完。只有 `err == io.EOF` 才表示读到文件末尾。

> ⚠️ `os.ReadFile` 内部用 `os.Open` + `io.ReadAll` 实现，没有大小限制的保护。如果文件是 4GB 的日志文件，`os.ReadFile` 会尝试分配 4GB 内存然后 OOM。对大文件必须用分块读取。

### 1.3 写入文件

```go
// 一次性写入（小数据适用）
err := os.WriteFile("output.txt", []byte("hello world"), 0644)

// 写入字符串
f, _ := os.Create("output.txt")
f.WriteString("line 1\n")
f.WriteString("line 2\n")

// 写入字节切片
f.Write([]byte("raw bytes"))

// 带缓冲的写入器（推荐：减少系统调用次数）
w := bufio.NewWriter(f)
w.WriteString("buffered write\n")
w.Flush() // 必须 Flush，否则数据还在内存里没写到磁盘
```

`os.WriteFile` 不是追加写入，它每次都会覆盖整个文件。如果你想追加：

```go
f, _ := os.OpenFile("app.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
f.WriteString("new log entry\n")
```

### 1.4 文件信息与遍历目录

```go
// 获取文件信息
info, err := os.Stat("config.yaml")
fmt.Println(info.Name())  // config.yaml
fmt.Println(info.Size())  // 1024 (字节)
fmt.Println(info.Mode())  // -rw-r--r--
fmt.Println(info.IsDir()) // false

// 遍历目录
entries, err := os.ReadDir(".")
for _, entry := range entries {
    fmt.Println(entry.Name(), entry.IsDir())
}

// 用 WalkDir 递归遍历
err = filepath.WalkDir(".", func(path string, d fs.DirEntry, err error) error {
    if err != nil {
        return err // 无法访问的文件/目录，可以选择跳过或报错
    }
    fmt.Println(path)
    return nil
})
```

`os.ReadDir` 返回的是 `[]os.DirEntry`，不是 `[]os.FileInfo`。`DirEntry` 是一个轻量接口，只包含 `Name()`、`IsDir()`、`Type()`、`Info()` 四个方法。如果需要详细信息（Size、ModTime 等），调用 `Info()` 获取 `FileInfo`，但这个调用会额外做一次 `stat` 系统调用。

> ⚠️ `filepath.WalkDir` 和旧版 `filepath.Walk` 的区别：WalkDir 的回调接收 `fs.DirEntry`，Walk 的回调接收 `os.FileInfo`。WalkDir 性能更好，因为它不需要在遍历目录项时就获取完整的 FileInfo。Go 1.16+ 应该用 WalkDir。

### 1.5 文件权限（FileMode）

Unix 文件权限用低 9 位表示 `rwxrwxrwx`（owner/group/other），在 Go 中用八进制字面量 `0644`、`0755` 等：

```go
0644 // owner 可读写，group 和 other 只读 → 普通文件常用权限
0755 // owner 全权限，group 和 other 可读可执行 → 可执行文件/目录常用
0600 // 仅 owner 可读写 → 私密文件（密钥、证书）
```

`os.FileMode` 还包含文件类型位（通过 `ModeDir`、`ModeSymlink` 等常量判断）：

```go
if info.Mode().IsRegular() {
    // 普通文件
}
if info.Mode().IsDir() {
    // 目录
}
if info.Mode()&os.ModeSymlink != 0 {
    // 符号链接
}
if info.Mode().Perm() == 0644 {
    // 权限位恰好是 0644
}
```

### 1.6 文件操作实战

```go
// 复制文件
func CopyFile(src, dst string) error {
    srcFile, err := os.Open(src)
    if err != nil {
        return fmt.Errorf("open src: %w", err)
    }
    defer srcFile.Close()

    dstFile, err := os.Create(dst)
    if err != nil {
        return fmt.Errorf("create dst: %w", err)
    }
    defer dstFile.Close()

    _, err = io.Copy(dstFile, srcFile)
    return err
}

// 安全地写入文件（先写临时文件，成功后再 rename，原子操作）
func AtomicWrite(filename string, data []byte, perm os.FileMode) error {
    tmp := filename + ".tmp"
    if err := os.WriteFile(tmp, data, perm); err != nil {
        return err
    }
    return os.Rename(tmp, filename)
}
```

原子写入模式很重要：如果程序在 `WriteFile` 中途崩溃，原文件不会被损坏，因为你一直在写的是 `.tmp` 文件。`os.Rename` 在同一个文件系统上是原子操作（Unix 的 `rename(2)` 保证）。

### 1.7 环境变量和进程信息

`os` 包还包含进程相关操作：

```go
// 环境变量
os.Getenv("HOME")
os.Setenv("DEBUG", "true")
os.LookupEnv("DATABASE_URL") // 返回 (value, exists)

// 扩展环境变量
os.ExpandEnv("$HOME/.config") // /home/user/.config

// 进程信息
os.Getpid()   // 进程 ID
os.Getwd()    // 当前工作目录
os.UserHomeDir() // 用户主目录路径
os.TempDir()  // 临时目录 (/tmp 或 %TEMP%)
```

---

## 二、io 包：读写接口与组合器

`io` 包定义了 `Reader` 和 `Writer` 两个核心接口。Go 标准库中几乎所有 I/O 相关类型都实现了这两个接口。

### 2.1 Reader 和 Writer 接口

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}
```

`Read` 的契约很关键：`n` 可能小于 `len(p)` 不等于出错。当 `err == io.EOF` 且 `n > 0` 时，调用者应该先处理 `p[:n]`，下一次调用才会返回 `(0, io.EOF)`。这是 Go I/O 中最常见的误解。

```go
// 正确的 Read 循环
buf := make([]byte, 1024)
for {
    n, err := r.Read(buf)
    if n > 0 {
        // 处理 buf[:n]，不管 err 是什么
        process(buf[:n])
    }
    if err == io.EOF {
        break
    }
    if err != nil {
        log.Fatal(err)
    }
}
```

### 2.2 常用组合器

```go
// io.Copy — 把 Reader 的数据全部复制到 Writer（内部用 32KB 缓冲区）
written, err := io.Copy(dst, src)

// io.CopyN — 复制最多 N 字节
written, err := io.CopyN(dst, src, 1024)

// io.CopyBuffer — 使用自定义大小的缓冲区
buf := make([]byte, 64*1024)
written, err := io.CopyBuffer(dst, src, buf)

// io.ReadAll — 读取 Reader 的全部内容
data, err := io.ReadAll(r)

// io.ReadFull — 精确读取 len(buf) 字节
buf := make([]byte, 256)
_, err := io.ReadFull(r, buf) // 少于 256 字节会返回 io.ErrUnexpectedEOF

// io.LimitReader — 限制读取 N 字节后返回 EOF
lr := io.LimitReader(r, 1024*1024*10) // 最多读 10MB
data, _ := io.ReadAll(lr)

// io.MultiReader — 将多个 Reader 串联成一个
r := io.MultiReader(
    strings.NewReader("header\n"),
    fileReader,
    strings.NewReader("\nfooter"),
)

// io.MultiWriter — 一份数据同时写入多个 Writer
w := io.MultiWriter(os.Stdout, logFile)
```

`io.Copy` 内部使用 `io.CopyBuffer`，如果没有指定缓冲区会自动分配一个 32KB 的。对大文件复制，增大缓冲区可以提高吞吐：

```go
// 1GB 文件复制，用 1MB 缓冲区
buf := make([]byte, 1024*1024)
io.CopyBuffer(dst, src, buf)
```

### 2.3 Pipe — 内存中的管道

`io.Pipe()` 返回一对 `*PipeReader` 和 `*PipeWriter`。写入管道的字节可以从管道读出，适合在 goroutine 间传递数据、或将 Writer 接口适配为 Reader：

```go
r, w := io.Pipe()

go func() {
    defer w.Close()
    // 生成大量数据并写入 pipe
    for i := 0; i < 1000; i++ {
        fmt.Fprintf(w, "line %d\n", i)
    }
}()

// 主 goroutine 从 pipe 读取
scanner := bufio.NewScanner(r)
for scanner.Scan() {
    fmt.Println(scanner.Text())
}
```

> ⚠️ Pipe 是同步的——`Write` 会阻塞直到 `Read` 消费了数据，反之亦然。它不是无界缓冲的 channel。如果写入速度远大于读取速度，应该用 `bytes.Buffer` 或 channel。

### 2.4 TeeReader — 读取的同时记录数据

```go
// 从 HTTP 请求体读取的同时把原始数据写入日志
var buf bytes.Buffer
tee := io.TeeReader(req.Body, &buf)

// 正常解析请求体
var payload Payload
json.NewDecoder(tee).Decode(&payload)

// 原始请求体在 buf 中，可以打日志
log.Printf("raw request body: %s", buf.String())
```

### 2.5 SectionReader — 文件片段读取器

```go
// 把一个文件的 [offset, offset+limit) 范围当作独立的 Reader
f, _ := os.Open("large.dat")
sr := io.NewSectionReader(f, 1024, 4096) // 从字节 1024 开始，读 4096 字节

data := make([]byte, 4096)
sr.Read(data) // 只读 large.dat 的 1024~5120 区间
```

`io.SectionReader` 还实现了 `io.ReaderAt`，可以并发地从不同偏移量读取同一文件，每个 goroutine 读取一段：

```go
// 多 goroutine 并发读文件的 4 个段
sr := io.NewSectionReader(f, 0, fileSize)
var wg sync.WaitGroup
segSize := fileSize / 4
for i := 0; i < 4; i++ {
    wg.Add(1)
    go func(offset int64) {
        defer wg.Done()
        buf := make([]byte, segSize)
        sr.ReadAt(buf, offset)
        // 处理 buf
    }(int64(i) * segSize)
}
wg.Wait()
```

---

## 三、bufio 包：缓冲 I/O

操作系统的 `read(2)`/`write(2)` 是系统调用，开销不小。对于频繁的小数据读写，`bufio` 在用户态维护一个缓冲区，积累到一定量再触发系统调用。

### 3.1 Buffered Reader

```go
f, _ := os.Open("access.log")
r := bufio.NewReader(f)     // 默认 4096 字节缓冲区
r := bufio.NewReaderSize(f, 64*1024) // 64KB 缓冲区

// 读一个字节
b, err := r.ReadByte()

// 读一行（不包括换行符）
line, err := r.ReadString('\n')
line, err := r.ReadBytes('\n')

// 回退一个字节（把读出来的放回去）
r.UnreadByte()

// 偷看下 n 个字节，但不移动读位置
peek, err := r.Peek(4) // 看前 4 个字节，比如判断文件魔数
```

### 3.2 Buffered Writer

```go
f, _ := os.Create("output.txt")
w := bufio.NewWriter(f)     // 默认 4096 字节缓冲区
w := bufio.NewWriterSize(f, 64*1024)

w.WriteString("hello\n")
w.WriteByte('x')
w.Write([]byte("raw data\n"))

// 关键：Flush 把缓冲数据写入底层 Writer
w.Flush()
```

> ⚠️ 经常看到这样的 bug：写了数据但文件是空的。原因就是忘了 `Flush()`。`defer w.Flush()` 可以避免遗漏，但要注意 `Flush` 可能返回 error，而 defer 会吞掉这个 error。更严谨的做法：

```go
func writeData(filename string, data []string) (err error) {
    f, err := os.Create(filename)
    if err != nil {
        return err
    }
    defer func() {
        if cerr := f.Close(); cerr != nil && err == nil {
            err = cerr
        }
    }()
    w := bufio.NewWriter(f)
    for _, line := range data {
        if _, err := w.WriteString(line + "\n"); err != nil {
            return err
        }
    }
    return w.Flush() // 在 Close 之前 Flush
}
```

### 3.3 Scanner — 逐行/逐词扫描

`bufio.Scanner` 是处理按分隔符分割的文本流的最佳工具。默认按行分割：

```go
f, _ := os.Open("access.log")
scanner := bufio.NewScanner(f)
for scanner.Scan() {
    line := scanner.Text()
    // 处理每一行
}
if err := scanner.Err(); err != nil {
    log.Fatal(err)
}
```

按词分割：

```go
scanner := bufio.NewScanner(strings.NewReader("hello world foo bar"))
scanner.Split(bufio.ScanWords)
for scanner.Scan() {
    fmt.Println(scanner.Text()) // hello, world, foo, bar
}
```

自定义分割函数：

```go
// 按逗号分割
scanner.Split(func(data []byte, atEOF bool) (advance int, token []byte, err error) {
    if atEOF && len(data) == 0 {
        return 0, nil, nil
    }
    for i, b := range data {
        if b == ',' {
            return i + 1, data[:i], nil
        }
    }
    if atEOF {
        return len(data), data, nil
    }
    return 0, nil, nil // 请求更多数据
})
```

> ⚠️ `Scanner` 的默认缓冲区只有 64KB（`MaxScanTokenSize`）。如果某一行超过 64KB，会返回 `bufio.ErrTooLong`。处理超大行时需要先调大缓冲区：

```go
scanner := bufio.NewScanner(f)
buf := make([]byte, 0, 1024*1024)
scanner.Buffer(buf, 10*1024*1024) // 最大支持 10MB 单行
```

---

## 四、filepath 包：跨平台路径操作

`filepath` 包处理文件路径，自动适配操作系统的路径分隔符（Unix `/`，Windows `\`）。

### 4.1 路径拼接与分割

```go
filepath.Join("a", "b", "c")       // a/b/c (Unix) 或 a\b\c (Windows)
filepath.Split("/a/b/c.txt")        // ("/a/b/", "c.txt")
filepath.Dir("/a/b/c.txt")          // /a/b
filepath.Base("/a/b/c.txt")         // c.txt
filepath.Ext("/a/b/c.txt")          // .txt
filepath.Clean("a//b/../c/./d")    // a/c/d
```

> ⚠️ 不要用 `strings.Join(parts, "/")` 拼路径，在 Windows 上会出错。始终用 `filepath.Join`。同理，不要用 `strings.Split(path, "/")`，用 `filepath.SplitList`。

### 4.2 绝对路径与相对路径

```go
abs, _ := filepath.Abs("config.yaml")     // 绝对路径
rel, _ := filepath.Rel("/a/b", "/a/b/c")  // c

// Glob 模式匹配
files, _ := filepath.Glob("*.go")          // 当前目录下所有 .go 文件
files, _ = filepath.Glob("**/*.go")        // ⚠️ 不支持 ** 递归匹配

// 判断路径是否匹配模式
filepath.Match("*.go", "main.go")           // true
filepath.Match("[0-9]*.txt", "1_data.txt") // true
```

### 4.3 WalkDir — 递归遍历

```go
var goFiles []string
filepath.WalkDir(".", func(path string, d fs.DirEntry, err error) error {
    if err != nil {
        // 遇到无法访问的目录时不要 panic，跳过或返回 error
        fmt.Fprintf(os.Stderr, "walk error: %v\n", err)
        return nil
    }
    if d.IsDir() {
        // 跳过隐藏目录
        if strings.HasPrefix(d.Name(), ".") && d.Name() != "." {
            return filepath.SkipDir
        }
        return nil
    }
    if filepath.Ext(path) == ".go" {
        goFiles = append(goFiles, path)
    }
    return nil
})
```

### 4.4 路径通配符规则

`filepath.Match` 和 `filepath.Glob` 使用的模式语法：

| 模式 | 匹配 |
|------|------|
| `*` | 任意非分隔符字符（不跨目录） |
| `?` | 任意单个非分隔符字符 |
| `[abc]` | 字符集 |
| `[a-z]` | 字符范围 |

如果想递归匹配，需要手动实现或用第三方库（如 `doublestar`）：

```go
// 手动递归 glob
func GlobRecursive(pattern string) ([]string, error) {
    var matches []string
    filepath.WalkDir(".", func(path string, d fs.DirEntry, err error) error {
        if d.IsDir() || err != nil {
            return err
        }
        matched, _ := filepath.Match(pattern, filepath.Base(path))
        if matched {
            matches = append(matches, path)
        }
        return nil
    })
    return matches, nil
}
```

---

## 五、io/fs 包：文件系统抽象（Go 1.16+）

`io/fs` 从具体文件系统（`os.DirFS`）和内存文件系统（`fstest.MapFS`）中抽象出一个统一的 `fs.FS` 接口。这是 `embed` 包的基础。

### 5.1 FS 接口

```go
type FS interface {
    Open(name string) (File, error)
}

type File interface {
    Stat() (FileInfo, error)
    Read([]byte) (int, error)
    Close() error
}
```

有了 `fs.FS`，代码可以完全不依赖 `os.Open`，既可以操作真实文件系统也可以操作内存中的文件系统。典型的应用场景是：测试时不碰磁盘。

### 5.2 真实文件系统

```go
// 把某个目录抽象为 fs.FS
var staticFiles fs.FS = os.DirFS("./static")

// 读这个目录下的文件
content, err := fs.ReadFile(staticFiles, "index.html")

// 遍历这个文件系统
fs.WalkDir(staticFiles, ".", func(path string, d fs.DirEntry, err error) error {
    fmt.Println(path)
    return nil
})
```

> ⚠️ `os.DirFS` 的根目录在调用时就固定了。`Open("../../etc/passwd")` 是无效的——`fs.FS` 的实现会验证路径不超出根目录（`fs.ValidPath` 会拒绝包含 `..` 的路径）。

### 5.3 测试用内存文件系统

```go
import "testing/fstest"

func TestConfigParser(t *testing.T) {
    fs := fstest.MapFS{
        "config.yaml": &fstest.MapFile{
            Data: []byte("server:\n  port: 8080\n"),
        },
        "secrets/key.txt": &fstest.MapFile{
            Data: []byte("my-secret-key"),
            Mode: 0600,
        },
    }

    // 用这个 fs 测试你的配置解析器
    cfg, err := ParseConfig(fs, "config.yaml")
    if err != nil {
        t.Fatal(err)
    }
    if cfg.Server.Port != 8080 {
        t.Errorf("expected port 8080, got %d", cfg.Server.Port)
    }
}
```

你写的代码接受 `fs.FS` 参数而不是直接用 `os.Open`：

```go
func ParseConfig(fsys fs.FS, filename string) (*Config, error) {
    f, err := fsys.Open(filename)
    if err != nil {
        return nil, err
    }
    defer f.Close()
    // 解析逻辑...
}
```

生产环境传 `os.DirFS("./config")`，测试环境传 `fstest.MapFS{...}`。这在 Go 标准库和很多开源项目中是标准做法。

### 5.4 Sub — 子文件系统

```go
// 只暴露 /static 子目录为独立的 FS
root := os.DirFS(".")
static, err := fs.Sub(root, "static")
// static 现在只能访问 ./static/ 下的文件
```

---

## 六、embed 包：编译时嵌入文件（Go 1.16+）

`embed` 在编译时将文件嵌入到二进制中，运行时不需要磁盘文件。

### 6.1 基本用法

```go
import "embed"

//go:embed config.yaml
var configData []byte

//go:embed config.yaml
var configString string

//go:embed static/*
var staticFiles embed.FS

//go:embed templates/*.html
var templates embed.FS
```

```go
func main() {
    // 嵌入的单文件
    fmt.Println(string(configData))

    // 嵌入的目录树
    data, _ := staticFiles.ReadFile("static/logo.png")

    // 和 http.FileServer 配合
    sub, _ := fs.Sub(staticFiles, "static")
    http.Handle("/", http.FileServer(http.FS(sub)))
    http.ListenAndServe(":8080", nil)
}
```

### 6.2 模式匹配规则

```go
//go:embed *.txt           // 当前包目录下的所有 .txt 文件
//go:embed templates/*     // templates 目录下的所有文件（不含子目录）
//go:embed templates/**    // Go 1.22+，templates 目录下的所有文件（含子目录）
//go:embed all:static      // 包括以下划线或点开头的文件（默认排除）
```

默认排除：
- 文件名以 `.` 开头的文件和目录
- 文件名以 `_` 开头的文件和目录

加 `all:` 前缀会包含这些被默认排除的文件。

### 6.3 路径约束

`embed` 的路径相对于**包含 `go:embed` 指令的 Go 源文件所在的包目录**，不是项目根目录。路径不能包含 `..`，不能是绝对路径。

### 6.4 多个 embed 指令

```go
//go:embed templates/layout.html
//go:embed templates/home.html
//go:embed templates/about.html
var templateFiles embed.FS
```

所有匹配的文件都合并到同一个 `embed.FS` 中。

### 6.5 实战：内嵌 Web 前端

```go
//go:embed all:dist
var frontend embed.FS

func main() {
    // 去掉 dist/ 前缀
    dist, _ := fs.Sub(frontend, "dist")

    mux := http.NewServeMux()
    mux.Handle("/", http.FileServer(http.FS(dist)))
    mux.HandleFunc("/api/hello", handleHello)

    http.ListenAndServe(":8080", mux)
}
```

编译后的二进制只包含一个可执行文件，`dist/` 目录下的所有前端资产都在里面。部署时不需要 Nginx 托管静态文件。

---

## 七、高级技巧与常见陷阱

### 7.1 defer 和 Close 的错误处理

典型错误写法：

```go
func badCopy(src, dst string) error {
    f, _ := os.Open(src)
    defer f.Close()
    // 读写逻辑
    return nil
    // f.Close() 的错误被忽略
}
```

正确的写法：

```go
func goodCopy(src, dst string) (err error) {
    f, err := os.Open(src)
    if err != nil {
        return err
    }
    defer func() {
        if cerr := f.Close(); cerr != nil && err == nil {
            err = cerr
        }
    }()
    // 读写逻辑...
    return nil
}
```

对只读文件，`Close` 的错误通常可以忽略（操作系统保证读操作不会产生延迟写入错误）。对写入文件，`Close` 的错误**绝对不能忽略**——`Close` 可能触发最后的 `fsync`，这时才暴露出磁盘满、NFS 超时等问题。

### 7.2 临时文件的安全创建

```go
// 错误：竞态条件，两个进程可能拿到同一个文件名
tmp := "/tmp/myapp_" + randomString()

// 正确：操作系统保证原子性
f, err := os.CreateTemp("", "myapp_*")
// f.Name() 是唯一的临时文件名
defer os.Remove(f.Name()) // 清理
```

> ⚠️ `CreateTemp` 的两个参数：第一个是目录（空字符串表示 `os.TempDir()`），第二个是文件名模式，`*` 会被替换为随机字符串。模式中至少要有一个 `*`。

### 7.3 处理大文件：内存映射

对于 GB 级别的文件，`os.File.Read` 需要用户态/内核态的多次复制。`syscall.Mmap` 将文件直接映射到进程地址空间：

```go
import "golang.org/x/exp/mmap" // 官方实验性包

func readLargeFile(path string) ([]byte, error) {
    r, err := mmap.Open(path)
    if err != nil {
        return nil, err
    }
    defer r.Close()

    // r 实现了 io.ReaderAt
    buf := make([]byte, 1024)
    r.ReadAt(buf, 0) // 从偏移 0 开始读
    return buf, nil
}
```

mmap 的优势：操作系统负责按需加载页面（demand paging），不会一次性占用整个文件大小的物理内存。但 mmap 有平台差异，Windows 上行为与 Unix 不完全一致。

### 7.4 文件锁

Go 标准库没有提供文件锁。但可以通过 `syscall.Flock`（Unix）或 `LockFileEx`（Windows）实现：

```go
// Unix only
import "syscall"

func LockFile(f *os.File) error {
    return syscall.Flock(int(f.Fd()), syscall.LOCK_EX)
}

func UnlockFile(f *os.File) error {
    return syscall.Flock(int(f.Fd()), syscall.LOCK_UN)
}
```

文件锁常用于防止多个进程实例同时运行（PID 文件模式）。在跨平台场景，自己写文件锁容易出问题，建议用 `golang.org/x/sys` 或更高层的库。

### 7.5 读取目录时处理被删除的文件

遍历目录是经典的时间窗口问题——从 `ReadDir` 返回文件列表到你对每个文件做操作之间，文件可能已被删除：

```go
entries, _ := os.ReadDir("/tmp/processing")
for _, e := range entries {
    f, err := os.Open(e.Name())
    if os.IsNotExist(err) {
        continue // 文件在处理前被删了，跳过
    }
    // 处理 f
}
```

### 7.6 fs.FS 适配器速查表

| 场景 | 适配方式 |
|------|---------|
| 本地目录 | `os.DirFS("./config")` |
| 测试数据 | `fstest.MapFS{...}` |
| 嵌入文件 | `//go:embed` + `embed.FS` |
| HTTP 文件服务器 | `http.FS(fsys)` |
| 子目录隔离 | `fs.Sub(fsys, "subdir")` |
| 只读保证 | `fs.ReadFile(fsys, name)` |

---

## 八、性能对比与选型建议

| 操作 | 推荐方案 | 不推荐 |
|------|---------|--------|
| 一次性读小文件 | `os.ReadFile` | 手动 `Open` + `Read` + `Close` |
| 逐行读文本 | `bufio.Scanner` | `ReadString('\n')` 循环 |
| 大文件复制 | `io.Copy` + 大缓冲区 | `io.Copy` 默认缓冲（只有 32KB） |
| 频繁小写入 | `bufio.Writer` | 直接 `f.Write` |
| 测试文件 I/O | `fstest.MapFS` | mock 或真实临时文件 |
| 嵌入静态资源 | `embed.FS` | 手动读取 + 字符串常量 |
| 递归目录遍历 | `filepath.WalkDir` | 旧版 `filepath.Walk` |
| 字节拼接写入 | `io.MultiWriter` 或 `bytes.Buffer` | 多次 `Write` |

核心原则：Go 的标准库已经完整覆盖了文件处理的所有场景。能用标准库就用标准库，只在标准库有明显性能瓶颈或功能缺失时才引入第三方库。`os` + `io` + `bufio` + `filepath` + `fs` + `embed` 六个包组合起来能解决 95% 的文件处理需求。
