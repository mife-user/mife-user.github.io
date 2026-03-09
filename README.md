# MIFE Blog

基于 Hugo 构建的个人博客，采用黑金主题风格。

🔗 在线访问：https://mife-user.github.io/

## ✨ 特性

- 🎨 黑金渐变主题，优雅大气
- 🌍 中英文切换支持
- 📱 响应式设计，适配移动端
- ⚡ 基于 Hugo，构建速度快
- 🚀 GitHub Pages 自动部署

## 📁 目录结构

```
my-blog/
├── content/           # 内容目录
│   ├── posts/        # 博客文章
│   └── projects/     # 项目展示
├── static/images/    # 静态图片（头像、背景）
├── themes/mife-theme/ # 自定义主题
├── hugo.toml         # Hugo 配置文件
└── .gitignore
```

## 🚀 使用方法

### 环境要求

- [Hugo](https://gohugo.io/) (已安装在 Termux 中)

### 发布新文章

1. 创建新文章：
   ```bash
   hugo new content posts/文章标题.md
   ```

2. 编辑生成的文件，修改 Front Matter：
   ```yaml
   ---
   title: '文章标题'
   date: 2026-03-09T12:00:00+08:00
   draft: false  # 改为 false 表示发布
   tags:
     - 标签 1
     - 标签 2
   ---
   
   文章内容...
   ```

3. 提交并推送：
   ```bash
   git add -A
   git commit -m "feat: 发布新文章 - 文章标题"
   git push
   ```

### 添加新项目

1. 创建新项目：
   ```bash
   hugo new content projects/项目名称.md
   ```

2. 编辑文件内容：
   ```yaml
   ---
   title: '项目名称'
   date: 2026-03-09T12:00:00+08:00
   draft: false
   tags:
     - 技术栈
     - 类型
   ---
   
   项目描述...
   ```

3. 提交并推送：
   ```bash
   git add -A
   git commit -m "feat: 添加新项目 - 项目名称"
   git push
   ```

### 本地预览

```bash
hugo server --noBuildLock --bind 0.0.0.0
```

然后在浏览器中访问显示的地址（通常是 http://localhost:1313）。

### 修改博客配置

编辑 `hugo.toml` 文件：

```toml
[params]
  author = 'MIFE'              # 作者名
  username = 'mife'            # 用户名
  bio = '开发者 · 创作者 · 探索者'  # 个人简介
  github = 'https://github.com/mife-user'  # GitHub 链接
  email = '15723556393@163.com'  # 邮箱
  avatar = 'images/avatar.jpg'   # 头像路径
  background = 'images/background.jpg'  # 背景图片路径
```

### 更换头像和背景

1. 将新图片放入 `static/images/` 目录
2. 修改 `hugo.toml` 中的 `avatar` 和 `background` 配置
3. 提交并推送：
   ```bash
   git add -A
   git commit -m "chore: 更新头像/背景"
   git push
   ```

## 🎨 自定义主题

主题位于 `themes/mife-theme/` 目录：

```
themes/mife-theme/
├── layouts/          # 模板文件
│   ├── _default/     # 默认布局
│   ├── partials/     # 局部模板
│   └── index.html    # 首页模板
├── static/images/    # 主题图片
└── theme.toml        # 主题配置
```

## 📝 写作格式

支持 Markdown 语法：

```markdown
# 标题

## 二级标题

这是**粗体**和*斜体*文本。

- 列表项 1
- 列表项 2

[链接文本](https://example.com)

![图片描述](图片路径)

```python
# 代码块
print("Hello, World!")
```
```

## 📄 许可证

MIT License

---

**Happy Blogging!** 🎉
