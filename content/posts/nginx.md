---
title: Nginx认识
date: 2026-04-06T14:50:53Z
draft: false
tags:
  - Go
  - 网关
  - nginx
---
# 前言

就我而言，我不是很理解写博客有什么用，写一些对知识点的理解啊，或者是一些笔记，都是写在笔记本上面，再专门来写博客，感觉很是浪费时间，面试官真的喜欢看这玩意儿吗，现在特别无聊的时候，用语音写一下，记录一些小东西
# 茅塞顿开的灵感
## 路径转发

在想那些location后面加的那个路径到底是什么意思，为什么要用这个来选择是否删除或者替换请求？原来是因为nginx它占用80端口,其他服务在别的端口,但是因为现在有些项目它的API不是统一的前缀,然而nginx是通过路径来将请求转发到其他服务,所以需要统一前缀,如果后端不是统一的前缀,就得加上斜杠.比如,后端的接是/user/load，那么前端发来的请求是/api/user/load，就需要在proxy_pass后面的地址加上斜杠，将API替换掉，变成/user/load.

# Nginx的作用

Nginx是一个高性能的HTTP和反向代理服务器，主要作用包括：

1. **反向代理**：将客户端请求转发到后端服务器，隐藏真实服务器IP
2. **负载均衡**：将请求分发到多个后端服务器，提高系统可用性和性能
3. **静态资源服务**：直接处理静态文件请求，减轻后端服务器负担
4. **URL重写**：修改请求URL路径，实现路径映射
5. **SSL/TLS终止**：处理HTTPS请求，减轻后端服务器加密解密负担

# Nginx的使用方法

## 基本配置结构

Nginx的配置文件通常位于`/etc/nginx/nginx.conf`，主要包含以下部分：

- `events`：配置连接处理
- `http`：配置HTTP服务器
- `server`：配置虚拟主机
- `location`：配置路径匹配规则

## 常用命令

```bash
# 启动nginx
systemctl start nginx

# 停止nginx
systemctl stop nginx

# 重新加载配置
nginx -s reload

# 测试配置语法
nginx -t
```

# Nginx的Docker Compose配置

以下是一个简洁的nginx docker-compose配置示例：

```yaml
version: '3'
services:
  nginx:
    image: nginx:latest  # 使用最新版nginx镜像
    ports:
      - "80:80"  # 映射主机80端口到容器80端口
      - "443:443"  # 映射主机443端口到容器443端口（HTTPS）
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d  # 挂载配置文件目录
      - ./nginx/html:/usr/share/nginx/html  # 挂载静态文件目录
      - ./nginx/certs:/etc/nginx/certs  # 挂载SSL证书目录
    restart: always  # 容器退出时自动重启
    networks:
      - app-network  # 加入自定义网络

# 定义网络
networks:
  app-network:
    driver: bridge
```

## 配置文件示例（nginx/conf.d/default.conf）

```nginx
server {
    listen 80;  # 监听80端口
    server_name example.com;  # 服务器名称

    # 重定向HTTP到HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;  # 监听443端口，启用SSL
    server_name example.com;  # 服务器名称

    # SSL配置
    ssl_certificate /etc/nginx/certs/fullchain.pem;  # 证书文件路径
    ssl_certificate_key /etc/nginx/certs/privkey.pem;  # 私钥文件路径

    # 静态文件服务
    location / {
        root /usr/share/nginx/html;  # 静态文件根目录
        index index.html index.htm;  # 默认索引文件
    }

    # 反向代理到后端API服务
    location /api/ {
        proxy_pass http://backend:8080/;  # 转发到后端服务
        proxy_set_header Host $host;  # 传递主机头
        proxy_set_header X-Real-IP $remote_addr;  # 传递真实IP
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # 传递转发链
        proxy_set_header X-Forwarded-Proto $scheme;  # 传递协议
    }
}
```

# 结语

目前博客的主要就是积累一些小灵感,有待后续补充,希望这些小灵感能够帮助你我理解。
