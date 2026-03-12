# MIFE Blog - AI 开发指南

> 本文档用于帮助 AI 助手快速了解项目结构、技术栈和开发规范，以便提供准确的开发支持。

---

## 📋 项目概览

| 项目信息 | 详情 |
|---------|------|
| **项目名称** | MIFE Blog |
| **类型** | 个人博客（静态网站） |
| **框架** | Hugo v0.157.0 |
| **主题** | 自定义 Mife Theme（黑金风格） |
| **部署** | GitHub Pages |
| **在线地址** | https://mife-user.github.io/ |
| **开发环境** | Termux (Android) |

---

## 🗂️ 项目结构

```
my-blog/
├── .github/workflows/
│   └── hugo.yml              # GitHub Actions 部署配置
├── archetypes/
│   ├── default.md            # 默认模板（JSON 数组格式）
│   ├── posts.md              # 文章专用模板
│   └── projects.md           # 项目专用模板
├── content/
│   ├── posts/                # 博客文章 (.md)
│   └── projects/             # 项目展示 (.md)
├── public/                   # 构建输出目录（自动生成）
├── static/
│   ├── audio/                # 音频文件（背景音乐）
│   └── images/               # 图片资源（头像、背景）
├── themes/mife-theme/        # 自定义主题
│   ├── assets/css/           # CSS 资源
│   ├── layouts/
│   │   ├── _default/         # 默认布局模板
│   │   ├── partials/         # 局部模板
│   │   │   ├── head.html     # 头部（含全部 CSS 样式）
│   │   │   ├── header.html   # 导航栏 + 搜索弹窗
│   │   │   ├── footer.html   # 页脚 + JavaScript 逻辑
│   │   │   └── *.html        # 其他局部组件
│   │   ├── projects/         # 项目页面模板
│   │   ├── taxonomy/         # 分类/标签页面
│   │   └── index.html        # 首页模板
│   ├── static/               # 主题静态资源
│   └── theme.toml            # 主题配置
├── build.sh                  # 构建脚本
├── hugo.toml                 # Hugo 主配置
└── README.md                 # 项目说明
```

---

## ⚙️ 核心配置

### hugo.toml 关键配置

```toml
baseURL = 'https://mife-user.github.io/'
languageCode = 'zh-CN'
title = 'MIFE Blog'
theme = 'mife-theme'

[params]
  author = 'MIFE'                    # 作者名
  username = 'mife'                  # 用户名
  bio = '开发者 · 创作者 · 探索者'     # 个人简介
  github = 'https://github.com/mife-user'
  email = '15723556393@163.com'
  avatar = 'images/avatar.jpg'       # 头像路径（相对于 static/）
  background = 'images/background.jpg' # 背景路径
  enableComments = true
  issueLabel = 'comments'

[menu]  # 导航菜单
  [[menu.main]]
    name = '关于'
    url = '#about'
    weight = 1
  [[menu.main]]
    name = '文章'
    url = '#posts'
    weight = 2
  [[menu.main]]
    name = '项目'
    url = '#projects'
    weight = 3
```

---

## 🎨 主题设计系统

### CSS 变量（head.html）

```css
:root {
    --bg-primary: rgba(10, 10, 10, 0.85);      /* 主背景 */
    --bg-secondary: rgba(18, 18, 18, 0.9);     /* 次级背景 */
    --bg-card: rgba(26, 26, 26, 0.9);          /* 卡片背景 */
    --gold-primary: #d4af37;                   /* 主金色 */
    --gold-light: #f4d46a;                     /* 亮金色 */
    --gold-dark: #aa8c2c;                      /* 暗金色 */
    --text-primary: #ffffff;                   /* 主文字 */
    --text-secondary: #b0b0b0;                 /* 次级文字 */
    --text-muted: #666666;                     /* 弱化文字 */
    --border-color: rgba(42, 42, 42, 0.8);     /* 边框颜色 */
}
```

### 字体
- 桌面端：`'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto`
- 中文：系统默认中文字体

---

## 📝 内容创作规范

### 文章 Front Matter

```yaml
---
title: '文章标题'
date: 2026-03-09T12:00:00+08:00  # ISO 8601 格式
draft: false                      # true=草稿，false=发布
tags: ["标签 1", "标签 2"]
---
```

### 项目 Front Matter

```yaml
---
title: '项目名称'
date: 2026-03-11T09:43:00+08:00
draft: false
tags: ["Go", "Gin", "网盘"]
---
```

### 注意事项
1. **标签格式**：统一使用 JSON 数组格式 `tags: ["标签 1", "标签 2"]`（文章和项目都必须使用此格式）
2. **草稿状态**：`draft: true` 的文章在正式构建时不会显示
3. **文件命名**：支持中文文件名，但 URL 会被编码
4. **模板文件**：使用 `hugo new content posts/标题.md` 或 `hugo new content projects/标题.md` 创建时，会自动使用 `archetypes/` 目录下的模板，已统一为 JSON 数组格式

---

## 🔧 常用命令

### 本地开发
```bash
# 本地预览（Termux）
hugo server --noBuildLock --bind 0.0.0.0

# 构建站点
hugo --noBuildLock

# 创建新文章
hugo new content posts/文章标题.md

# 创建新项目
hugo new content projects/项目名称.md
```

### 构建脚本 (build.sh)
```bash
#!/bin/bash
set -a
source .env        # 加载环境变量（如果存在）
set +a
hugo --noBuildLock "$@"
```

### 发布流程
```bash
# 1. 修改内容后
git add -A
git commit -m "feat: 描述变更内容"
git push

# 2. GitHub Actions 自动部署到 GitHub Pages
```

---

## 🎯 核心功能说明

### 1. 搜索功能
**位置**: `themes/mife-theme/layouts/partials/header.html` + `footer.html`

**实现原理**:
- 搜索弹窗在 header.html 中定义
- 搜索逻辑在 footer.html 的 JavaScript 中
- 使用 Hugo 模板在构建时将所有文章数据嵌入 JavaScript

**关键代码** (footer.html):
```javascript
function loadPosts() {
    if (allPosts.length > 0) return;
    {{ range where .Site.RegularPages "Section" "posts" }}
    allPosts.push({
        title: {{ .Title | jsonify | safeJS }},
        date: {{ .Date.Format "2006-01-02" | jsonify | safeJS }},
        permalink: {{ .Permalink | jsonify | safeJS }},
        tags: {{ if .Params.tags }}{{ delimit .Params.tags "\", \"" | printf "[\"%s\"]" | safeJS }}{{ else }}[]{{ end }},
        summary: {{ .Summary | truncate 100 | jsonify | safeJS }},
        section: "posts"
    });
    {{ end }}

    {{ range where .Site.RegularPages "Section" "projects" }}
    allPosts.push({
        title: {{ .Title | jsonify | safeJS }},
        date: {{ .Date.Format "2006-01-02" | jsonify | safeJS }},
        permalink: {{ .Permalink | jsonify | safeJS }},
        tags: {{ if .Params.tags }}{{ delimit .Params.tags "\", \"" | printf "[\"%s\"]" | safeJS }}{{ else }}[]{{ end }},
        summary: {{ .Summary | truncate 100 | jsonify | safeJS }},
        section: "projects"
    });
    {{ end }}
}
```

**⚠️ 注意事项**:
- `tags` 字段必须使用 `delimit + printf + safeJS` 组合生成 JavaScript 数组
- 其他字段使用 `jsonify | safeJS` 避免双重引号问题
- 搜索支持：标题、标签、摘要（不区分大小写），**支持文章和项目搜索**

### 2. 多语言支持
**实现方式**: 使用 `data-zh` 和 `data-en` 属性

```html
<!-- HTML -->
<p data-zh="中文文本" data-en="English text">中文文本</p>

<!-- JavaScript 切换 -->
function toggleLanguage() {
    currentLang = currentLang === 'zh' ? 'en' : 'zh';
    document.querySelectorAll('[data-zh][data-en]').forEach(el => {
        el.textContent = currentLang === 'zh' ? el.getAttribute('data-zh') : el.getAttribute('data-en');
    });
}
```

### 3. 评论功能
**类型**: GitHub Issues / Utterances

**配置** (hugo.toml):
```toml
enableComments = true
issueLabel = 'comments'
```

**实现**: `partials/github-comments.html` 或 `partials/utterances-comments.html`

### 4. 背景音乐
**位置**: `static/audio/` + `footer.html`

**控制**: 左下角音乐按钮，支持播放/暂停

---

## 🚨 已知问题与修复记录

### 2026-03-12: 项目搜索功能修复
**问题**: 搜索功能只能搜索文章，无法搜索项目

**原因**: `loadPosts()` 函数只加载了 `posts` 目录的内容

**修复**:
```html
<!-- 修复后：同时加载文章和项目 -->
{{ range where .Site.RegularPages "Section" "posts" }}
allPosts.push({
    title: {{ .Title | jsonify | safeJS }},
    date: {{ .Date.Format "2006-01-02" | jsonify | safeJS }},
    permalink: {{ .Permalink | jsonify | safeJS }},
    tags: {{ if .Params.tags }}{{ delimit .Params.tags "\", \"" | printf "[\"%s\"]" | safeJS }}{{ else }}[]{{ end }},
    summary: {{ .Summary | truncate 100 | jsonify | safeJS }},
    section: "posts"
});
{{ end }}

{{ range where .Site.RegularPages "Section" "projects" }}
allPosts.push({
    title: {{ .Title | jsonify | safeJS }},
    date: {{ .Date.Format "2006-01-02" | jsonify | safeJS }},
    permalink: {{ .Permalink | jsonify | safeJS }},
    tags: {{ if .Params.tags }}{{ delimit .Params.tags "\", \"" | printf "[\"%s\"]" | safeJS }}{{ else }}[]{{ end }},
    summary: {{ .Summary | truncate 100 | jsonify | safeJS }},
    section: "projects"
});
{{ end }}
```

### 2026-03-12: 统一 Tags 格式
**问题**: 文章和项目使用不同的 tags 格式，导致不一致

**修复**:
```yaml
# 统一使用 JSON 数组格式（文章和项目都使用此格式）
tags: ["标签 1", "标签 2", "标签 3"]
```

### 2026-03-12: 项目页面格式优化
**问题**: 项目页面样式与文档格式不一致

**修复**:
- 标题添加 📦 emoji 图标
- 标签样式改为边框 + 金色文字，悬停时渐变填充
- 优化标题层级样式（h1/h2/h3 使用金色主题）
- 添加返回按钮样式

### 2026-03-12: 搜索功能修复
**问题**: 搜索框输入关键词后无反应，一直显示"输入关键词开始搜索..."

**原因**: `tags` 字段使用 `jsonify` 生成的是字符串而非 JavaScript 数组

**修复**:
```html
<!-- 修复前 -->
tags: {{ .Params.tags | jsonify }}

<!-- 修复后 -->
tags: {{ if .Params.tags }}{{ delimit .Params.tags "\", \"" | printf "[\"%s\"]" | safeJS }}{{ else }}[]{{ end }}
```

### 2026-03-12: 移动端头像遮挡修复
**问题**: 手机端头像被导航栏遮挡

**修复**: 调整 `.avatar` 的 `z-index` 为 1100（高于导航栏的 1000）

---

## 📱 响应式设计断点

```css
/* 移动端 */
@media (max-width: 480px) { }   /* 小屏手机 */
@media (max-width: 768px) { }   /* 手机/平板 */

/* 桌面端 */
@media (min-width: 1024px) { }  /* PC */
```

---

## 🔐 环境变量

构建脚本支持 `.env` 文件（可选）:
```bash
# .env 示例
HUGO_ENV=production
GITHUB_TOKEN=xxx
```

---

## 📦 依赖版本

| 依赖 | 版本 | 说明 |
|-----|------|------|
| Hugo | 0.157.0+extended | 静态站点生成器 |
| Node.js | - | 可选（用于 npm 依赖） |
| Dart Sass | - | CSS 预处理器 |

---

## 🎯 AI 开发注意事项

### 1. Hugo 模板语法
- 使用 `{{ }}` 包裹模板代码
- `| jsonify` 将值转换为 JSON 格式
- `| safeJS` 标记为安全的 JavaScript（避免 HTML 转义）
- `| relURL` 生成相对 URL
- `| urlize` 将文本转换为 URL 友好格式

### 2. 文件路径规则
- `static/` 目录文件直接映射到网站根目录
- `content/` 目录文件由 Hugo 处理生成 HTML
- 图片引用：`![描述](/images/xxx.jpg)` 或 `![描述](images/xxx.jpg)`

### 3. CSS/JS 位置
- **所有 CSS** 内联在 `head.html` 的 `<style>` 标签中
- **所有 JS** 内联在 `footer.html` 的 `<script>` 标签中
- 无外部 CSS/JS 文件引用

### 4. 修改后的操作
```bash
# 1. 修改主题文件后，重新构建
bash build.sh

# 2. 验证 public/ 目录输出
ls -la public/

# 3. 提交并推送
git add -A
git commit -m "描述变更"
git push
```

### 5. 调试技巧
- 查看生成的 HTML: `grep "关键词" public/index.html`
- 检查 JavaScript: 浏览器开发者工具 Console
- 本地预览：`hugo server --noBuildLock --bind 0.0.0.0`

---

## 📞 快速参考

| 需求 | 操作 |
|-----|------|
| 发布新文章 | `hugo new content posts/标题.md` → 编辑 → `git push` |
| 修改配置 | 编辑 `hugo.toml` → `git push` |
| 更换头像/背景 | 替换 `static/images/` 文件 → `git push` |
| 修改主题样式 | 编辑 `themes/mife-theme/layouts/partials/head.html` |
| 修改搜索逻辑 | 编辑 `themes/mife-theme/layouts/partials/footer.html` |
| 修改导航菜单 | 编辑 `hugo.toml` 的 `[menu]` 部分 |
| 本地预览 | `hugo server --noBuildLock --bind 0.0.0.0` |

---

## 📝 更新日志

| 日期 | 更新内容 |
|-----|---------|
| 2026-03-12 | 统一 archetypes 模板为 JSON 数组格式（default.md, posts.md, projects.md） |
| 2026-03-12 | 统一项目和文章的 tags 格式为 JSON 数组；修复项目搜索功能；优化项目页面样式 |
| 2026-03-12 | 修复搜索功能 tags 字段；修复移动端头像遮挡问题 |

---

**文档更新时间**: 2026-03-12  
**维护者**: MIFE

**重要提示**: 每次执行请求后，请记得在本文档中更新修改记录和修复历史。
