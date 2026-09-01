# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

MIFE Blog — a Hugo v0.157.0 static site with a custom black-gold theme, deployed to GitHub Pages at `https://mife-user.github.io/`. Development happens in Termux (Android). Detailed docs live in `AI_GUIDE.md`.

## Commands

```bash
# Local dev server
hugo server --noBuildLock --bind 0.0.0.0

# Build (also see build.sh which sources .env before running hugo)
hugo --noBuildLock
bash build.sh

# Create content
hugo new content posts/标题.md
hugo new content projects/项目名称.md
```

No tests, no linting — this is a static site. Deployment is automatic: push to `main` triggers `.github/workflows/hugo.yml` which builds with `hugo --gc --minify` and deploys to GitHub Pages.

## Architecture

```
content/               # All site content (Markdown)
  posts/               # Blog posts
  projects/            # Project showcases
  links/               # Friend links page
themes/mife-theme/
  layouts/
    _default/          # baseof.html, list.html, single.html
    partials/          # head.html (ALL CSS inline), footer.html (ALL JS inline),
                       #   header.html (nav + search modal), github-comments.html
    projects/          # Project single template
    taxonomy/          # Tag pages
    links/             # Friend links templates
    index.html         # Homepage
  assets/css/          # responsive.css
static/                # Static files mapped to site root (images/, audio/, js/)
archetypes/            # Hugo content templates
```

## Key patterns

- **All CSS is inline in `head.html`** `<style>` tags. **All JS is inline in `footer.html`** `<script>` tags. No external CSS/JS files.
- **Tags format**: must use JSON array `tags: ["标签1", "标签2"]` in front matter — do NOT use YAML list format.
- **Search**: Hugo template in `footer.html` embeds all posts + projects as a JS array at build time. Search is client-side only.
- **Math**: KaTeX + auto-render rendered client-side (CDN-first, local `static/js/` fallback). Inline `$...$` / `\(...\)`, display `$$...$$` / `\[...\]`. CSS inlined in `head.html`, fonts at `static/js/fonts/`.
- **i18n**: `data-zh` / `data-en` attributes on elements, toggled by JS in footer.html.
- **Comments**: Utterances widget loaded in `partials/utterances-comments.html`, uses GitHub Issues with label `comments`.
- **Drafts**: `draft: true` content is hidden in production builds. Set to `false` to publish.
- **Obsidian**: `.obsidian/` config exists under `content/` — the author uses Obsidian to edit content.
- **Site config**: `hugo.toml` — baseURL, params (author, social links, avatar/background paths), menu navigation.

## Writing style for posts

All blog posts must follow these conventions:

- **Professional programmer perspective**: Write as an experienced developer explaining to peers. No "大家好啊今天我们来学习" openings.
- **No AI-isms**: Avoid phrases like "总的来说", "此外", "值得注意的是", "正如我们所见", "总而言之", "首先...其次...最后" (use direct language instead), "在当今这个时代".
- **No excessive rhetoric**: Skip flowery descriptions, metaphors that don't add technical clarity, and filler paragraphs. Every sentence should carry information.
- **Code-driven**: Show code first, explain after. Readers learn by reading code, not prose. Every concept must have a concrete, runnable example.
- **Detail matters**: Cover edge cases, error handling, performance implications, and gotchas. A good post anticipates what the reader will trip over.
- **Pitfall callouts**: Use `> ⚠️` blockquotes for common mistakes and unexpected behavior.
- **Real-world scenarios**: All examples should come from actual production use cases, not contrived "foo/bar" examples (unless the abstraction is genuinely generic).
- **Chinese with technical terms in English**: Write in Chinese but keep Go keywords, API names, error messages, and technical terms in their original English form.
- **Structure**: `##` for major sections, `###` for subsections. Each major section should be self-contained enough to be useful if read standalone.
