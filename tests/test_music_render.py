"""Hugo 正文音乐渲染回归检查；无需安装第三方 Python 包。"""

import os
import re
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
FRONT_MATTER = """---
title: 渲染检查
date: 2020-01-01T00:00:00+08:00
draft: false
tags: ["test"]
---

"""
IMAGES = """![普通图片](/images/音程.png "图片说明")

![**加粗** 图片](</images/带 空格.png> "有 & 符号")

![音乐与声音](/images/music.png)

![带属性的图片](/images/sized.png){width=320 height=200}

![嵌入图片](data:image/png;base64,iVBORw0KGgo=)

![不安全图片](javascript:alert%281%29)
"""
POST = FRONT_MATTER + """文字前缀 ![音乐](/voices/学习.mp3 "学习旋律") 文字后缀

![音乐](<https://example.com/我的 歌曲.mp3?x=1&y=2>)

![音乐](../audio/demo.mp3)

![音乐](javascript:alert%281%29)

""" + IMAGES + """
```markdown
![音乐](/voices/not-rendered.mp3)
```
"""
PROJECT = FRONT_MATTER + """![音乐](/voices/project.mp3)

![音乐](/voices/project-2.mp3 "项目演示")
"""
OTHER = FRONT_MATTER + "![音乐](/images/music.png)\n\n" + IMAGES


class Tags(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.label_texts = []
        self._label = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "span" and "embedded-audio-name" in attrs.get("class", "").split():
            self._label = []

    def handle_data(self, data):
        if self._label is not None:
            self._label.append(data)

    def handle_endtag(self, tag):
        if tag == "span" and self._label is not None:
            self.label_texts.append("".join(self._label))
            self._label = None

    def matching(self, tag, class_name=None):
        return [
            attrs for name, attrs in self.tags
            if name == tag and (class_name is None or class_name in attrs.get("class", "").split())
        ]


class MusicRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="mife-music-test-")
        cls.addClassCleanup(cls.tmp.cleanup)
        temp = Path(cls.tmp.name)
        site = temp / "site"
        site.mkdir()
        shutil.copy2(ROOT / "hugo.toml", site / "hugo.toml")
        for section, content in (("posts", POST), ("projects", PROJECT), ("other", OTHER)):
            folder = site / "content" / section
            folder.mkdir(parents=True)
            (folder / "render.md").write_text(content, encoding="utf-8")

        # 对比 Hugo 默认图片渲染，防止新增钩子改变普通图片。
        themes = temp / "themes"
        shutil.copytree(ROOT / "themes" / "mife-theme", themes / "mife-theme")
        env = os.environ.copy()
        env["HUGO_CACHEDIR"] = str(temp / "cache")

        def build(destination):
            result = subprocess.run(
                ["hugo", "--source", str(site), "--themesDir", str(themes),
                 "--destination", str(destination), "--noBuildLock", "--minify"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
            )
            if result.returncode:
                raise RuntimeError("Hugo build failed:\n" + result.stdout + result.stderr)

        cls.output = temp / "with-hook"
        build(cls.output)
        (themes / "mife-theme" / "layouts" / "_default" / "_markup" / "render-image.html").unlink()
        cls.baseline = temp / "without-hook"
        build(cls.baseline)

    def page(self, section, baseline=False):
        root = self.baseline if baseline else self.output
        return Tags((root / section / "render" / "index.html").read_text(encoding="utf-8"))

    def test_post_audio_paths_title_and_fallback(self):
        page = self.page("posts")
        players = page.matching("audio", "embedded-audio-element")
        self.assertEqual(len(players), 4)
        self.assertEqual(unquote(players[0]["src"]), "/voices/学习.mp3")
        self.assertEqual(unquote(players[1]["src"]), "https://example.com/我的 歌曲.mp3?x=1&y=2")
        self.assertEqual(players[2]["src"], "../audio/demo.mp3")
        self.assertEqual(players[3]["src"], "#ZgotmplZ")
        for audio in players:
            self.assertIn("controls", audio)
            self.assertEqual(audio["preload"], "none")
            self.assertTrue(audio["aria-labelledby"])
        labels = page.matching("span", "embedded-audio-name")
        self.assertEqual(len({label["id"] for label in labels}), 4)
        self.assertEqual([p["aria-labelledby"] for p in players], [label["id"] for label in labels])
        self.assertEqual(page.label_texts, ["学习旋律", "音乐", "音乐", "音乐"])
        self.assertNotIn("data-zh", labels[0])  # 自定义标题不被语言切换覆盖。
        self.assertEqual(labels[1]["data-zh"], "音乐")
        fallbacks = [a for a in page.matching("a") if a.get("data-zh") == "下载音频"]
        self.assertEqual(len(fallbacks), 4)
        self.assertEqual(fallbacks[3]["href"], "#ZgotmplZ")

    def test_project_audio_and_labels(self):
        page = self.page("projects")
        players = page.matching("audio", "embedded-audio-element")
        self.assertEqual([p["src"] for p in players], ["/voices/project.mp3", "/voices/project-2.mp3"])
        labels = page.matching("span", "embedded-audio-name")
        self.assertEqual(page.label_texts, ["音乐", "项目演示"])
        self.assertEqual(labels[0]["data-zh"], "音乐")
        self.assertNotIn("data-zh", labels[1])
        self.assertNotEqual(players[0]["aria-labelledby"], players[1]["aria-labelledby"])

    def test_ordinary_images_match_hugo_default(self):
        for section in ("posts", "projects", "other"):
            with self.subTest(section=section):
                expected = self.page(section, True).matching("img")
                if section in ("posts", "projects"):
                    expected = [image for image in expected if image.get("alt") != "音乐"]
                actual = self.page(section).matching("img")
                # URL percent 编码的大小写不影响资源地址。
                for image in actual + expected:
                    image["src"] = re.sub(r"%[0-9a-fA-F]{2}", lambda m: m.group().upper(), image["src"])
                self.assertEqual(actual, expected)
        self.assertFalse(self.page("other").matching("audio", "embedded-audio-element"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
