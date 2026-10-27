---
title: 'GO语言库包学习'
date: 2026-09-03T13:39:51+08:00
lastmod: 2026-10-27T22:39:51+08:00
draft: false
tags: ["go"]
---

# 命令行
```bash
go env #打印go的所有环境变量
go work init #在当前目录初始化go.work
go mod init xxx #在当前目录
```

# net

## 接口

### Conn

Conn： TCP、Unix 流式套接字等面向流协议的抽象

|方法|作用|
|:--:|:--:|
| `Read(b []byte) (n int, err error)` | 从连接读取数据 |
| `Write(b []byte) (n int, err error)` | 向连接写入数据 |
| `Close() error` | 关闭连接，解除阻塞的 Read/Write |
| `LocalAddr() Addr` | 返回本地网络地址 |
| `RemoteAddr() Addr` | 返回对端网络地址 |
| `SetDeadline(t time.Time) error` | 同时设置读和写的绝对截止时间 |
| `SetReadDeadline(t time.Time) error` | 仅设置读操作的截止时间 |
| `SetWriteDeadline(t time.Time) error` | 仅设置写操作的截止时间 |

### Listener

Listener: 面向流协议的监听器,由net.Listen创建，用于接受连接

|方法|作用|
|:--:|:--:|
|Accept() (Conn, error)	|阻塞等待并返回下一个连接|
|Close() error|关闭监听器，解除阻塞的 Accept|
|Addr() Addr|返回监听器的网络地址|

### PacketConn

PacketConn：面向数据包的通用连接, 是 UDP、IP 等数据包导向协议的抽象,与 Conn 的根本区别在于保留消息边界：一次 ReadFrom 对应一个完整的数据包，不会像 TCP 那样把多次写入合并成字节流。

| 方法 | 作用 |
|:--:|:--:|
| `ReadFrom(p []byte) (n int, addr Addr, err error)` | 读取一个数据包，同时返回发送方地址 |
| `WriteTo(p []byte, addr Addr) (n int, err error)` | 向指定地址发送一个数据包 |
| `Close() error` | 关闭连接 |
| `LocalAddr() Addr` | 返回本地地址 |
| `SetDeadline(t time.Time) error` | 设置读写截止时间 |
| `SetReadDeadline(t time.Time) error` | 设置读截止时间 |
| `SetWriteDeadline(t time.Time) error` | 设置写截止时间 |

### Addr

所有地址类型都实现Addr接口

```go
type Addr interface {
    Network() string  // 网络类型名，如 "tcp"、"udp"
    String() string   // 地址字符串形式
}
```

## 结构体

### TCPAddr / UDPAddr / IPAddr / UnixAddr

| 类型 | 对应网络 | 关键字段 | 作用 |
|:--:|:--:|:--:|:--:|
| `TCPAddr` | tcp / tcp4 / tcp6 | `IP IP`, `Port int`, `Zone string` | TCP 端点地址 |
| `UDPAddr` | udp / udp4 / udp6 | `IP IP`, `Port int`, `Zone string` | UDP 端点地址 |
| `IPAddr` | ip / ip4 / ip6 | `IP IP`, `Zone string` | IP 端点地址（无端口） |
| `UnixAddr` | unix / unixgram / unixpacket | `Name string`, `Net string` | Unix 域套接字路径 |

对应的解析函数：`ResolveTCPAddr`、`ResolveUDPAddr`、`ResolveIPAddr`、`ResolveUnixAddr`，将“host:port”字符串解析为具体地址结构。

### IP

IP 是 []byte 的别名，表示 IPv4 或 IPv6 地址。

| 常用函数 / 方法 | 作用 |
|:--:|:--:|
| `ParseIP(s string) IP` | 将字符串解析为 IP，失败返回 nil |
| `ParseCIDR(s string) (IP,*IPNET,error)`| 将字符串按CIDR解析，IPNet的Contains(ip IP) bool方法用于判断IP是否属于该子网 |
| `IPv4(a, b, c, d byte) IP` | 构造 IPv4 地址 |
| `(ip IP) String() string` | 转为字符串 |
| `(ip IP) IsLoopback() bool` | 是否为回环地址 |
| `(ip IP) To4() IP` | 转为 4 字节 IPv4 表示，非 IPv4 返回 nil |

### IPNet

```go
type IPNet struct {
    IP   IP
    Mask IPMask
}
```

IPNet 表示一个 IP 网段，常用于判断某个 IP 是否属于该子网。

| 常用函数 / 方法 | 作用 |
|:--:|:--:|
| `(n *IPNet) Contains(ip IP) bool` | 判断 IP 是否属于该网段 |
| `(n *IPNet) Network() string` | 返回网络类型名，如 `"ip+net"` |
| `(n *IPNet) String() string` | 返回 CIDR 形式的字符串，如 `"192.168.0.0/24"` |

```go
_, ipnet, _ := net.ParseCIDR("192.168.0.0/24")
ipnet.Contains(net.ParseIP("192.168.0.10")) // true
```

### Dialer

Dialer 提供细粒度的拨号控制，零值等价于 Dial。关键字段：

| 字段 | 作用 |
|:--:|:--:|
| `Timeout time.Duration` | 拨号完成的最大时间 |
| `Deadline time.Time` | 拨号的绝对截止时间，优先于 `Timeout` |
| `LocalAddr Addr` | 指定本地地址 |
| `FallbackDelay time.Duration` | “Happy Eyeballs”中 IPv4/IPv6 回退延迟，默认 300ms |
| `KeepAlive time.Duration` | TCP keep-alive 探测间隔 |
| `Resolver *Resolver` | 自定义 DNS 解析器 |
| `Control func(network, address string, c syscall.RawConn) error` | 连接创建后、实际拨号前的钩子，常用于设置 socket 选项 |

Dialer 的核心方法是 `DialContext(ctx context.Context, network, address string)`，支持上下文取消。

### Resolver

Resolver 允许自定义 DNS 行为。关键字段：

| 字段 | 作用 |
|:--:|:--:|
| `PreferGo bool` | 优先使用纯 Go 解析器，而非 cgo |
| `StrictErrors bool` | 任一查询出错即返回错误 |
| `Dial func(ctx, network, address) (Conn, error)` | 自定义 DNS 服务器连接方式 |

Resolver 提供与包级函数同名的方法（如 `resolver.LookupHost`），并支持 `LookupHost(ctx, host)` 形式以支持上下文取消。

## 包级方法

### 拨号与监听

拨号：
| 函数 | 作用 |
|:--:|:--:|
| `Dial(network, address string) (Conn, error)` | 建立连接，使用系统默认拨号行为 |
| `DialTimeout(network, address string, timeout time.Duration) (Conn, error)` | 带超时的拨号，超时包含域名解析时间 |
| `DialTCP(...)` / `DialUDP(...)` / `DialIP(...)` / `DialUnix(...)` | 直接获得具体类型的连接，绕过接口装箱 |

监听
| 函数 | 作用 |
|:--:|:--:|
| `Listen(network, address string) (Listener, error)` | 创建流式监听器（TCP、Unix） |
| `ListenPacket(network, address string) (PacketConn, error)` | 创建数据包监听器（UDP、IP） |
| `ListenTCP` / `ListenUDP` / `ListenUnix` | 返回具体类型，可调用类型特有的方法 |

### 域名解析

| 函数 | 作用 |
|:--:|:--:|
| `LookupHost(host string) ([]string, error)` | 正向解析，返回 IP 字符串列表 |
| `LookupIP(host string) ([]IP, error)` | 类似 LookupHost，返回 []IP |
| `LookupAddr(addr string) ([]string, error)` | 反向解析，IP → 域名 |
| `LookupCNAME(host string) (string, error)` | 查询规范域名 |
| `LookupMX` / `LookupNS` / `LookupTXT` / `LookupSRV` | 查询各类 DNS 记录 |

# tls

## 包级方法

|函数|作用|
|:--:|:--:|
|func tls.DialWithDialer(dialer *net.Dialer, network string, addr string, config *tls.Config) (*tls.Conn, error)| 创建带超时的tls连接|

# smtp

## 结构体

### Client

```go
type Client struct {
	// Text is the textproto.Conn used by the Client. It is exported to allow for
	// clients to add extensions.
	Text *textproto.Conn
	// keep a reference to the connection so it can be used to create a TLS
	// connection later
	conn net.Conn
	// whether the Client is using TLS
	tls        bool
	serverName string
	// map of supported extensions
	ext map[string]string
	// supported auth mechanisms
	auth       []string
	localName  string // the name to use in HELO/EHLO
	didHello   bool   // whether we've said HELO/EHLO
	helloError error  // the error from the hello
}
```

|函数|作用|
|:--:|:--:|
|func (c *smtp.Client) Auth(a smtp.Auth) error|认证|
|func (c *smtp.Client) Mail(from string) error|设置邮箱发送者地址|
|func (c *smtp.Client) Rcpt(to string) error|设置邮箱接受者地址|
|func (c *smtp.Client) Data() (io.WriteCloser, error)|启动写入数据返回写入器|
|func (c *smtp.Client) Quit() error|结束连接|
## 包级方法

|函数|作用|
|:--:|:--:|
|NewClient(conn net.Conn, host string) (*smtp.Client, error)| 创建smtp连接|
|PlainAuth(identity string, username string, password string, host string) smtp.Auth|创建认证|

