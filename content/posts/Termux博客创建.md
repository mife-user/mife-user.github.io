---
title: Termux 从零搭建博客：npm + AI + Git + Hugo 完整操作记录/
date: 2026-03-09T12:00:00+08:00
draft: false
tags: ［＂Termux＂,＂Hugo＂］
---

## 前言
兴致启然，尝试在手机上便用 Termux 完成了一整套开发流程：安装 npm、安装 Qwen AI、安装 Git、搭建 Hugo 静态博客，利用github pages部署，利用utterances实现评论功能，并成功本地运行。本文记录每一步细节、命令和踩坑点。
（请阅读完再操作）

## 一、更新 Termux 环境
在谷歌商城安装后
打开 Termux，先更新源和软件，避免安装出错：（国内记得开vpn）
```bash
pkg update && pkg upgrade -y
```
本质为linux，用其指令
常见：
```bash
cd //用于进入某文件夹
clear //清空
//忘了，自己学🤫
``` 
## 二、安装 Node.js 和 npm

npm 用于安装各种工具包，包括后面的 AI 工具：
``` bash
pkg install nodejs -y
``` 
验证是否安装成功：
``` bash
node -v
npm -v
``` 
出现版本号，说明安装完成。手机还是很好用的，不用管环境变量😍
 
## 三、安装 Qwen AI（通义千问）
（可以自己找在终端运行的AI用，较为推荐千问）
使用 npm 全局安装 Qwen AI 工具：
 
```bash
npm install -g qwen
``` 
安装后可以在 Termux 里直接使用 AI 辅助写命令、写代码。可以自己学习npm相关代码指令，像一些工具都会用到，很有用
 
## 四、安装 Git
 
搭建博客、上传代码到 GitHub 必须用到 Git：
 
```bash
pkg install git -y
``` 
获取ssh用于上传：(直接回车，可以自己学习设置密码）

```bash
# 把邮箱换成你 GitHub 注册邮箱
ssh-keygen -t ed25519 -C "your_github_email@xxx.com"
```
查看并复制密码
```bash
cat ~/.ssh/id_ed25519.pub
```
把公钥添加到 GitHub：
 
1. 打开 GitHub → 右上角头像 → Settings → SSH and GPG keys
2. 点击 New SSH key
3.  Title 随便填（比如  Termux Phone ），Key type 选  Authentication key 
4. 把刚才复制的公钥粘贴到 Key 输入框
5. 点击 Add SSH key，输入 GitHub 密码

确认配置 Git 用户名和邮箱：
 
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
``` 
查看配置：
 
```bash
git config --list
``` 
git设置与推送：

```bash

git init

git add .

git commit -m "提交说明"

git push origin 分支名

```
记得生成ssh密钥，方便以后上传
简要说明,具体操作自行注意,需要相关笔记的可以联系我邮箱
## 五、安装 Hugo
 
Hugo 是静态博客生成器，用来把 Markdown 生成网页：
 
```bash
pkg install hugo -y 
``` 
检查版本：
 
```bash
hugo version
``` 
## 六、创建 Hugo 博客项目

注意事项：
用安卓的权限，最好不要在Termux目录下面创建git仓库和你的博客文件夹，先用命令关联
```bash
termux-setup-storage
``` 
这个会赋予权限，让其能够访问手机存储的文件
接下来的操作，自己可以尝试，不过我更推荐让ai来帮忙写。如果无需则跳到第十项。
创建博客文件夹：
 
```bas 
hugo new site myblog
cd myblog 
``` 
安装主题：
 
```bash
  

git submodule add https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod
echo "theme = 'PaperMod'" >> config.toml
 
``` 
上面地址在hugo官网找模版，然后更改

## 七、新建文章
 
创建第一篇文章：
 
```bash
hugo new posts/termux-blog.md
``` 
用 nano 编辑文章：
 
```bash
nano content/posts/termux-blog.md
``` 
把文章头部的  draft: true  改为  draft: false  就是正式发布。

手机上可以下载Onsidian写，nano不好用
 
## 八、本地运行预览
 
启动 Hugo 服务：
 
```bash
hugo server --bind=0.0.0.0
``` 
在手机浏览器打开：
http://localhost:1313
 
## 九、常见问题与解决
 
1. 报错：.hugo_build.lock 无法创建
原因：项目放在手机共享存储，不支持文件锁。
解决：
 
```bash
  

rm .hugo_build.lock
hugo
 
``` 
2. nano 编辑器不会保存
保存： Ctrl + O  → 回车
退出： Ctrl + X 
3. 图片不显示
图片必须放在  static/  文件夹，路径以  /  开头。
## 十、利用qwen
在手机目录创建你的git仓库（先创建个文件夹，再利用git初始化），别忘了给Termux权限,让他访问到你的文件.

进入你的文件夹（my-blog)
```bash
cd /storage
cd /shared
cd /my-blog
```

打开qwen
```bash
qwen
```

按提示完成登陆

接下来给出提示词帮助创建hugo

```
类似于（要求自己选择更改）：
请你为我生成一个完整、可直接使用的 Hugo 主题，结构严格符合 Hugo 官方规范，不要使用任何框架，只使用原生 HTML + CSS + 少量 JS。

要求：
1. 主题名称：my-theme
2. 风格：极简、干净、响应式，适合技术博客 
3. 包含：
   - 首页（文章列表）
   - 文章详情页
   - 目录跳转
   - 代码高亮
   - 分页
   - 标签、分类
1. 目录结构必须是标准 Hugo 主题结构。
2. 不要超前设计
3. 代码风格简洁，要对pc与手机端适配。
4. 博客文章输出支持Markdown。
5. 需要的配置信息告诉我再填写（如github地址，个人邮箱）
6. 头像，背景图片放于本地，链接使用github的地址，上传后再提醒我修改
7. 最后上传到github

```
## 十一、常见问题

### 图片无法显示：

等待上传到github后，复制仓库的图片链接（如果找不到图片链接就将那些图片的网络链接告诉ai,一般图片链接是固定格式）
❌ 错误（这是页面，不是图片）
 `https://github.com/xxx/xxx/blob/main/xxx.jpg `

✅ 正确（必须是 raw 格式）
 `https://raw.githubusercontent.com/用户名/仓库名/main/图片名.jpg`
 然后告诉qwen修改对应图片链接

### 添加音乐播放按纽，无法播放

在网易云下载后，转换为MP3,然后询问qwen将音乐文件放在哪里，放入后让qwen实现即可（后续如果失败，操作跟图片一样，需要更改链接，询问ai如何操作即可）

### 评论功能失败

告诉qwen利用utterances
实现评论功能，后续按照提示操作，授权等

# 总结
 
今天在 Termux 里完成了：
 
- 安装 npm、nodejs
- 安装 Qwen AI
- 安装 git
- 安装 hugo
- 创建并运行博客
 最后注意保证提示词完善，为blog添加新东西，记得加各种提示词：如保证当前主体风格不变......
 这什么每次操作结束要退出的时候，让AI总结文档，放在当前目录下，每次调用的时候，让他先读文档
只用一部手机，就能搭建属于自己的博客。有什么问题可以联系我，邮箱或者咨询ai。

