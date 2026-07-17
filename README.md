# MIFE Blog

🔗 https://mife-user.github.io/

基于 Hugo 的黑金主题个人博客。本文档只说明如何添加收藏与友链。

---

## 📌 添加收藏

编辑 `themes/mife-theme/layouts/favorites/single.html`，页面内有三个分类区：

| 分类 | 用途 |
|------|------|
| 📄 收藏文章 | 值得反复读的技术文章 |
| 🌐 收藏网站 | 常用工具、资源站点 |
| 🎬 收藏视频 | 值得看的技术视频 |

### 添加方法

在对应分类的 `<div class="fav-grid">` 内部，复制粘贴以下模板块：

```html
<!-- 新链接 — 标题 -->
<a href="目标URL" target="_blank" rel="noopener" class="fav-item">
    <span class="fav-item-icon">🔗</span>
    <div class="fav-item-body">
        <span class="fav-item-title">链接标题</span>
        <span class="fav-item-desc">一句话简介。</span>
    </div>
    <span class="fav-item-arrow">↗</span>
</a>
```

改三处即可：
1. `href="目标URL"` — 链接地址
2. `🔗` — 换成合适的 emoji 图标
3. 标题和简介文字

然后**同步更新该分类标题行右侧的计数徽标**（`<span class="fav-count">N</span>` 中的 N）。

提交推送即生效：
```bash
git add -A
git commit -m "feat: 更新收藏夹"
git push
```

---

## 🔗 添加友链

编辑 `themes/mife-theme/layouts/links/single.html`。

### 添加方法

在 `<div class="links-grid">` 内部，复制粘贴以下模板块：

```html
<!-- 新友链 — 名称 -->
<div class="user-card">
    <a href="目标URL" target="_blank" class="user-link">
        <div class="user-avatar">
            <img src="头像图片URL" alt="站点名称" class="avatar-img">
        </div>
        <h3 class="user-name">站点名称</h3>
        <p class="user-bio">一句话简介。</p>
    </a>
</div>
```

改四处即可：
1. `href="目标URL"` — 对方站点地址
2. `src="头像图片URL"` — 头像图链接
3. 站点名称
4. 一句话简介

提交推送即生效：
```bash
git add -A
git commit -m "feat: 更新友链"
git push
```

---

## 🔧 本地预览

```bash
hugo server --noBuildLock --bind 0.0.0.0
```

浏览器访问 `http://localhost:1313`。
