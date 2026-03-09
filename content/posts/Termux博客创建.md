---
title: 'Termux 从零搭建博客：npm + AI + Git + Hugo 完整操作记录/'
date: 2026-03-09T12:00:00+08:00
draft: false

---

## 前言
兴致启然，尝试用 Termux 完成了一整套开发流程：安装 npm、安装 Qwen AI、安装 Git、搭建 Hugo 静态博客，并成功本地运行。本文记录每一步细节、命令和踩坑点。

## 一、更新 Termux 环境
打开 Termux，先更新源和软件，避免安装出错：
```bash
pkg update && pkg upgrade -y
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
出现版本号，说明安装完成。
 
## 三、安装 Qwen AI（通义千问）
（可以自己找在终端运行的AI用，较为推荐千问）
使用 npm 全局安装 Qwen AI 工具：
 
```bash
  

npm install -g qwen
 
``` 
安装后可以在 Termux 里直接使用 AI 辅助写命令、写代码。
 
## 四、安装 Git
 
搭建博客、上传代码到 GitHub 必须用到 Git：
 
```bash
  

pkg install git -y
 
``` 
配置 Git 用户名和邮箱：
 
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

创建博客文件夹：
 
```bash
  

hugo new site myblog
cd myblog
 
``` 
安装主题：
 
```bash
  

git submodule add https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod
echo "theme = 'PaperMod'" >> config.toml
 
``` 
实际上，可以利用AI，自己写主题.注意关键词,严格按照hugo项目结构,重点注意图片文件的引用

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

手机上可以下载markor写
 
## 八、本地运行预览
 
启动 Hugo 服务：
 
```bash
  

hugo server --bind=0.0.0.0
 
``` 
在手机浏览器打开：
 
plaintext
  

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
 
总结
 
今天在 Termux 里完成了：
 
- 安装 npm、nodejs
- 安装 Qwen AI
- 安装 git
- 安装 hugo
- 创建并运行博客
 
只用一部手机，就能搭建属于自己的博客。有什么问题可以联系我，邮箱或者咨询ai。

