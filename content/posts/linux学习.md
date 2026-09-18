---
title: 'Linux学习'
date: 2026-08-17T13:25:04+08:00
draft: false
tags: ["linux"]
---

# 命令学习

## 简要

|指令|作用|
|:-:|:-:|
|ls|输出当前目录下的文件名称|
## 详细

### 程序

#### 命令行启动
- 直接启动程序，占用当前终端
```bash
# 使用绝对路径
/path/to/your/program
# 或在程序所在目录下使用
./program
```
- 后台运行（&），终端不会占用
```bash
/path/to/your/program &
```
- 后台运行且不受终端关闭影响（nohup）
输出会重定向到nohup.out文件（默认）
```bash
nohup /path/to/your/program > nohup.out 2>&1 &
```
#### 作为系统服务管理（systemd）

- 创建服务文件：在 /etc/systemd/system/ 目录下创建一个 .service 文件
```bash
[Unit]
Description=My Application Service
After=network.target

[Service]
ExecStart=/path/to/your/program
Restart=always
User=yourusername

[Install]
WantedBy=multi-user.target
```
- 启动和管理服务：使用 systemctl 命令来管理
```bash
# 重新加载systemd配置
sudo systemctl daemon-reload
# 设置开机自启
sudo systemctl enable myapp.service
# 立即启动服务
sudo systemctl start myapp.service
# 查看服务状态
sudo systemctl status myapp.service
```

#### 停止程序

- 终止前台程序
```bash
ctrl+c
```
- 终止后台或未知PID的程序
```bash
ps aux | grep your_program_name
#或
pgrep -a your_program_name

# 优雅终止 (默认发送SIGTERM信号)
kill <PID>
# 强制终止 (发送SIGKILL信号，当正常kill无效时使用)
kill -9 <PID>

# 直接用名称，它们会匹配并终止所有同名进程
pkill your_program_name
# 强制终止
pkill -9 your_program_name

#终止所有与给定名称完全匹配的进程
killall your_program_name
```

