---
title: 'Godot引擎完全入门指南：从零基础到能做出游戏'
date: 2026-06-07T12:00:00+08:00
draft: false
tags: ["Godot", "游戏开发", "入门教程", "GDScript", "开源引擎"]
---

<!--
  目录自动生成说明：
  文章中的 ## 和 ### 标题会自动生成目录，出现在文章开头。
  使用 ## 标题 作为一级目录项，### 标题 作为二级目录项。
  点击目录项可平滑滚动到对应位置。
-->

## 前言：为什么要写这篇指南

2026 年，Godot 已经成为全球增长最快、社区最活跃的开源游戏引擎之一。但中文世界中系统性的 Godot 入门资料仍然稀缺——大部分教程要么过于简略（"点这个按钮，写这行代码，运行"），要么直接跳入某个具体领域（渲染、物理），缺少一份从"完全零基础"到"理解底层原理"的完整路线图。

**本指南的目标**：彻底讲清楚 Godot 的每一个核心概念——不仅是"怎么用"，更是"为什么这样设计"以及"底层是怎么工作的"。读完这篇，你可以：

- 理解 Godot 的设计哲学，不再"知其然不知其所以然"
- 掌握节点系统的完整知识体系
- 理解 GDScript 语言的深度特性
- 了解渲染管线、物理引擎、信号机制的工作原理
- 有能力独立开始制作自己的游戏

本指南基于 **Godot 4.X** 系列（当前为 4.4），所有代码示例使用原生 **GDScript**。

---

## 一、什么是 Godot？

### 1.1 一句话定义

**Godot**（读作 /ɡəˈdoʊ/，"戈多"）是一个**完全免费、开源**的跨平台游戏引擎。它不仅免费（不收一分钱），而且开源（你可以看到并修改它的每一行源代码），使用极其宽松的 MIT 许可证——你用 Godot 做的游戏，完全归你所有，甚至不需要在游戏里标注 "Made with Godot"。

### 1.2 历史渊源

Godot 由阿根廷开发者 **Juan Linietsky** 和 **Ariel Manzur** 于 2007 年左右开始开发。最初是他们在工作室内部使用的私有引擎，2014 年在 Kickstarter 上众筹后以 MIT 许可证开源发布。

之所以叫 "Godot"，取自 Samuel Beckett 的荒诞派戏剧《等待戈多》（Waiting for Godot）——寓意着游戏创作者们一直在"等待"的那个理想引擎，终于来了。

### 1.3 Godot 能做什么？

- **2D 游戏**：Godot 的 2D 能力是行业顶级的，拥有独立的 2D 渲染引擎（不是 3D 的"降维"处理）
- **3D 游戏**：从 4.0 版本开始，3D 能力大幅提升，支持 Vulkan 渲染、全局光照、体积雾等现代特性
- **移动游戏**：支持导出到 iOS 和 Android
- **Web 游戏**：支持导出到 HTML5 / WebAssembly
- **桌面应用**：甚至可以用 Godot 制作非游戏的 GUI 应用程序（编辑器本身就是用 Godot 做的）
- **主机游戏**：通过第三方服务商支持 Nintendo Switch、PlayStation、Xbox

### 1.4 Godot 4.X vs 3.X：你需要知道的变化

当前主流版本是 **Godot 4.4**（截至 2026 年 6 月）。4.0 是一次巨大重构，主要变化：

- 渲染后端从 OpenGL ES 3.0 切换到 **Vulkan**（保留 OpenGL 兼容模式用于旧设备）
- 全新的 **TileMap** 系统（支持多层、地形自动拼接、导航网格）
- 全新的 **GDExtension** 系统（取代旧的 GDNative，支持 C++ / Rust / Swift 等语言扩展）
- 计算着色器（Compute Shader）支持
- GDScript 语言级 `await` 和一等 `Signal` 类型
- 更简洁的 API（`move_and_slide()` 不再需要传参数）

本指南所有内容基于 **Godot 4.X**。

---

## 二、为什么选择 Godot？

### 2.1 与其他引擎的快速对比

| 特性 | Godot | Unity | Unreal Engine |
|------|-------|-------|---------------|
| 价格 | 完全免费 | 个人免费 / 企业付费 | 营收超 100 万美元后分成 |
| 开源 | ✅ MIT 协议 | ❌ 源码可查看但有许可限制 | ✅ 源码开放但有许可限制 |
| 安装包大小 | ~40 MB | ~5 GB+ | ~20 GB+ |
| 启动速度 | 秒开 | 数分钟 | 数分钟 |
| 2D 支持 | ⭐⭐⭐⭐⭐ 原生独立 2D 引擎 | ⭐⭐⭐ 够用 | ⭐⭐ 较弱 |
| 3D 支持 | ⭐⭐⭐⭐ 快速追赶中 | ⭐⭐⭐⭐ 成熟 | ⭐⭐⭐⭐⭐ 业界顶级 |
| 脚本语言 | GDScript / C# / C++ | C# | C++ / Blueprint |
| 社区规模 | 快速增长 | 最大 | 很大 |

### 2.2 Godot 的独特优势

**（1）极低的入门门槛**

整个引擎不到 40 MB，下载解压即用。不需要注册账号，不需要安装额外的运行时环境。双击 `godot.exe` 就能开始做游戏。

**（2）自包含的设计哲学**

Godot 编辑器本身就是用 Godot 引擎制作的——这是一个递归设计。编辑器的 UI 系统和你做游戏时用的 UI 系统是**同一套**。意味着你学到的每一个 UI 控件知识，同时也是编辑器本身的知识。

**（3）专为游戏设计的概念模型**

Unity 和 Unreal 最初都不是专门为通用游戏开发设计的——Unity 源自于一个 Mac 游戏项目失败后的引擎化，Unreal 源自于 FPS 游戏。而 Godot 的核心概念（场景、节点、信号）从第一行代码起就是为通用游戏开发而设计的。

**（4）真正的"你的游戏"**

MIT 许可证意味着：即使你做了一个年收入 10 亿美元的游戏，你也不需要给 Godot 一分钱。你的游戏代码、资源、设计都属于你，没有任何隐藏条款。

---

## 三、核心哲学：万物皆场景

### 3.1 场景是什么？

在 Godot 中，**场景（Scene）** 是最核心的概念。一个场景可以简单理解为：

> **一个有组织的节点集合，作为一个独立的功能单元**

场景可以是一个角色、一把武器、一个关卡、一个 UI 界面、一个音效管理器——任何东西。

关键在于：**场景不仅仅是一个"组织单位"，它是一个可以独立运行、独立测试、独立编辑的完整小世界**。

### 3.2 场景的层级嵌套：搭积木式开发

场景可以包含其他场景——这是 Godot 最重要的设计思想：

```
游戏主场景 (main.tscn)
├── 玩家场景 (player.tscn)
│   ├── Sprite2D          ← 角色的贴图
│   ├── CollisionShape2D  ← 碰撞体
│   ├── AnimationPlayer   ← 动画播放器
│   └── WeaponArea          ← 武器碰撞检测
├── 敌人场景 (enemy.tscn) × 多个实例
│   ├── Sprite2D
│   ├── CollisionShape2D
│   └── HealthBar           ← 敌人自己的血条
├── UI 场景 (hud.tscn)
│   ├── ScoreLabel
│   └── HealthBar
└── 关卡场景 (level_01.tscn)   ← 关卡本身也可以是场景
    ├── TileMap              ← 地形
    ├── 敌人出生点 × N
    └── 道具 × N
```

这种设计的好处：

1. **每个场景可独立编辑和运行**——你可以只运行 `player.tscn` 来调试角色移动，不需要加载整个游戏
2. **场景可以无限复用**——同一个 `enemy.tscn` 可以实例化 100 次到不同位置
3. **修改会传播**——修改 `enemy.tscn` 的贴图，所有关卡中的所有敌人都自动更新
4. **场景可以继承**——这是 Godot 独有的强大特性

### 3.3 继承场景：面向对象编程在场景层面的体现

假设你有一个基础敌人场景：

```
base_enemy.tscn  (定义基本行为：移动、受伤、死亡)
├── enemy_fast.tscn   (继承自 base_enemy，覆盖：速度更快，更换贴图)
├── enemy_flying.tscn (继承自 base_enemy，覆盖：飞行移动，添加阴影)
└── boss.tscn         (继承自 base_enemy，覆盖：多阶段，大血条，特殊攻击)
```

当你在 `base_enemy` 中修了一个移动相关的 bug，所有继承场景**自动继承这个修复**，不需要逐个修改。这是面向对象编程中的"继承"概念在场景层面的优雅体现——**Godot 是极少数原生支持场景继承的引擎**。

### 3.4 `.tscn` 和 `.tres` 文件格式

这两个是 Godot 最核心的文本格式文件，都是人类可读的：

- **`.tscn`**（Text SCeNe）：存储场景。它本质上是一个 INI-like 格式的文本文件，记录了这个场景里有哪些节点、每个节点的属性和子节点关系
- **`.tres`**（Text RESource）：存储单个资源（材质、着色器、动画库、自定义资源等）

为什么是文本格式？因为文本格式可以：

- 用 `git diff` 清晰地看到每次修改了什么
- 多人协作时合并冲突更容易处理
- 用任何文本编辑器打开查看和手动修改

一个实际的 `.tscn` 文件长这样：

```ini
[gd_scene load_steps=3 format=3 uid="uid://c5o7k8h0p6xtn"]

[sub_resource type="CircleShape2D" id="CircleShape2D_1"]
radius = 30.0

[node name="Player" type="CharacterBody2D"]
position = Vector2(100, 200)
script = ExtResource("1_player_gd")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("CircleShape2D_1")
```

你可以看到：
- `[gd_scene ...]` 是文件头，定义了格式版本和 UID
- `[sub_resource ...]` 定义了内嵌资源（这个碰撞形状是一个半径 30 的圆）
- `[node ...]` 定义了节点实例，`parent="."` 表示父节点是上一个声明的节点

---

## 四、节点系统——Godot 的 DNA

### 4.1 节点是什么？

**节点（Node）** 是 Godot 中最基本的构建块——**一切皆节点**。

| 你想要... | 用这个节点 |
|-----------|-----------|
| 显示一张图片 | `Sprite2D` |
| 检测碰撞 | `CollisionShape2D` + `Area2D` / `CharacterBody2D` |
| 播放动画 | `AnimationPlayer` |
| 播放声音 | `AudioStreamPlayer` |
| 倒计时 | `Timer` |
| 显示一个按钮 | `Button` |
| 显示文字 | `Label` |
| 显示 3D 模型 | `MeshInstance3D` |
| 相机视角 | `Camera2D` / `Camera3D` |
| 光源照明 | `PointLight2D` / `OmniLight3D` |

### 4.2 节点的生命周期

每个节点从"出生"到"死亡"，经历一系列回调方法。**理解这些回调的调用顺序，是正确使用 Godot 的基础**：

```
_obj_init()         ← 对象构造（GDScript 对象被创建时）
    ↓（但要等场景树准备好才能访问其他节点）
_enter_tree()       ← 进入场景树的瞬间触发（此时子节点可能还没准备好）
    ↓
_ready()            ← 所有子节点都准备好了（这是你写初始化逻辑的地方）
    ↓
_process(delta)     ← 每帧调用（跟随显示器帧率：60fps / 144fps / ...）
    ↓                （同时）
_physics_process(delta) ← 每物理帧调用（固定频率，默认 60Hz）
    ↓
_exit_tree()        ← 离开场景树的瞬间触发
    ↓（被 queue_free() 延迟释放的瞬间）
析构：内存被回收
```

**关键规则——你必须牢记：**

1. **`_ready()` 在所有子节点的 `_ready()` 执行完之后才执行**——所以你可以在父节点的 `_ready()` 中安全地访问子节点
2. **`_enter_tree()` 时子节点可能尚未就绪**——不要在这里访问子节点
3. **`_process(delta)` 的 `delta` 是上一帧到当前帧的实际时间**（单位秒），帧率不固定，所有与时间相关的计算必须乘以 `delta`
4. **`_physics_process(delta)` 的 `delta` 是固定的**（默认 1/60 秒 = 0.01666...），用于物理计算以保证确定性
5. **`_init()` 中不能访问场景树**——此时节点还没有被加入任何树

### 4.3 节点类型体系全景图

这是 Godot 4 节点体系的主要分支：

```
Object（最基类，所有东西的根）
└── Node（场景树的基本单元）
    ├── CanvasItem（2D 和 UI 的基类，拥有绘制能力）
    │   ├── Node2D（2D 游戏对象：有 position / rotation / scale）
    │   │   ├── Sprite2D           —— 精灵（显示贴图）
    │   │   ├── AnimatedSprite2D   —— 帧动画精灵
    │   │   ├── Area2D             —— 检测区域（触发器）
    │   │   ├── CharacterBody2D    —— 代码控制的运动角色
    │   │   ├── RigidBody2D        —— 物理模拟刚体
    │   │   ├── StaticBody2D       —— 静态物理物体
    │   │   ├── TileMap            —— 瓦片地图
    │   │   ├── Path2D             —— 路径
    │   │   ├── CollisionShape2D   —— 2D 碰撞形状
    │   │   ├── CollisionPolygon2D —— 2D 碰撞多边形
    │   │   ├── RayCast2D          —— 2D 射线检测
    │   │   ├── Line2D             —— 画线
    │   │   ├── CPUParticles2D     —— CPU 粒子
    │   │   ├── GPUParticles2D     —— GPU 粒子
    │   │   ├── Light2D            —— 2D 灯光系统
    │   │   │   ├── PointLight2D   —— 点光源
    │   │   │   └── DirectionalLight2D —— 方向光
    │   │   ├── AudioStreamPlayer2D —— 2D 空间化音频
    │   │   ├── Camera2D           —— 2D 相机
    │   │   ├── NavigationAgent2D  —— 2D 寻路代理
    │   │   ├── NavigationRegion2D —— 2D 导航区域
    │   │   └── ...
    │   └── Control（UI 控件：有锚点和边距系统）
    │       ├── Label              —— 文本标签
    │       ├── Button             —— 按钮
    │       ├── LineEdit           —— 单行文本输入
    │       ├── TextEdit           —— 多行文本编辑
    │       ├── Panel              —— 面板（带样式背景）
    │       ├── ColorRect          —— 纯色矩形
    │       ├── TextureRect        —— 贴图矩形
    │       ├── ProgressBar        —— 进度条
    │       ├── ScrollContainer    —— 滚动容器
    │       ├── TabContainer       —— 标签页容器
    │       ├── PopupMenu          —— 弹出菜单
    │       ├── ItemList           —— 列表
    │       └── 各种 Container（自动布局容器）
    │           ├── HBoxContainer  —— 水平排列
    │           ├── VBoxContainer  —— 垂直排列
    │           ├── GridContainer  —— 网格排列
    │           └── ...
    ├── Node3D（3D 游戏对象：有 position / rotation / scale）
    │   ├── Sprite3D               —— 3D 精灵（始终面朝相机）
    │   ├── MeshInstance3D         —— 3D 网格实例
    │   ├── Camera3D               —— 3D 相机
    │   ├── Area3D                 —— 3D 检测区域
    │   ├── CharacterBody3D        —— 代码控制的 3D 角色
    │   ├── RigidBody3D            —— 3D 物理刚体
    │   ├── StaticBody3D           —— 3D 静态物理物体
    │   ├── CollisionShape3D       —— 3D 碰撞形状
    │   ├── Light3D                —— 3D 灯光系统
    │   │   ├── OmniLight3D        —— 点光源
    │   │   ├── SpotLight3D        —— 聚光灯
    │   │   └── DirectionalLight3D —— 方向光（太阳光）
    │   ├── GPUParticles3D         —— 3D GPU 粒子
    │   ├── AudioStreamPlayer3D    —— 3D 空间化音频
    │   ├── NavigationAgent3D      —— 3D 寻路代理
    │   └── ...
    └── 功能性节点（没有空间位置的节点）
        ├── Timer                  —— 计时器
        ├── AudioStreamPlayer      —— 全局音频播放器
        ├── AnimationPlayer        —— 动画播放器
        ├── Tween                  —— 补间动画（代码中创建）
        ├── HTTPRequest            —— HTTP 请求
        ├── FileDialog             —— 文件选择对话框
        └── ...
```

### 4.4 为什么节点设计如此重要？

节点系统的本质是一种**组件化设计**，但它比传统的 ECS（Entity-Component-System，实体-组件-系统）更直观：

- **Unity 的方式**：一个 `GameObject` 上平铺挂载多个 `Component`——你看到一个长长的组件列表：Transform、SpriteRenderer、BoxCollider2D、Rigidbody2D、AudioSource、自定义脚本 A、自定义脚本 B……
- **Godot 的方式**：组件就是节点，节点可嵌套形成树——`RigidBody2D` 节点下面挂着 `Sprite2D`、`CollisionShape2D`、`AudioStreamPlayer2D` 这些子节点。视觉上更清晰，编辑时可以单独拖拽每个子节点调整位置

**核心洞察**：树的层级结构比平铺列表更自然。比如"剑"上面有一个"碰撞体"，在树结构里它是剑的子节点——你在编辑器中拖动剑，碰撞体就跟着一起移动。这种父子关系不是手动指定的绑定，而是**树结构内建的语义**。

---

## 五、场景树——你的游戏世界的数据结构

### 5.1 场景树的本质

场景树本质上是一棵 **N 叉树**（每个节点可以有任意多个子节点）。根节点是一个 `Window`（当游戏运行时）。

引擎每一帧要遍历这棵树，做很多事情。大致流程（简化版）：

```
每一帧：
1. 从根节点开始，深度优先遍历每一棵子树
2. 对每个节点：
   a. 检查是否有新节点进入/退出 → 发射相应通知
   b. 调用 _process(delta)（如果该节点覆写了此方法）
   c. 递归处理该节点的所有子节点
3. 在每个物理节拍（physics tick）：
   a. 批量收集所有物理节点
   b. 调用它们的 _physics_process(delta)
   c. 执行物理模拟步进
```

### 5.2 获取节点引用的多种方式

```gdscript
# 方式一：使用 $ 语法糖（最常用，等价于 get_node()）
@onready var sprite: Sprite2D = $Sprite2D
@onready var timer: Timer = $Timer
@onready var weapon: Node2D = $Weapon

# 方式二：使用 get_node()（与 $ 完全等价）
@onready var sprite: Sprite2D = get_node("Sprite2D")

# 方式三：通过路径获取嵌套节点
@onready var sword: Area2D = $Weapon/Sword

# 方式四：使用 % 获取"唯一名称"节点（Godot 4 新特性）
# 在编辑器中右键节点 → "Access as Unique Name"
@onready var player: Player = %Player
# %Player 会搜索整个场景树中标记为"唯一名称"的 Player 节点
# 即使它在深层嵌套中也能直接获取，非常适合大型场景

# 方式五：获取父节点
var parent_node := get_parent()
var typed_parent := get_parent() as Node2D

# 方式六：获取根节点
var root := get_tree().root
var main := get_tree().current_scene

# 方式七：按分组查找
var enemies := get_tree().get_nodes_in_group("enemies")
```

### 5.3 场景树与所有权的关键规则

一个容易被忽视但非常重要的概念：**谁创建节点，谁负责销毁它（或者它的父节点销毁时自动带走它）**。

```gdscript
# 创建一个子弹实例
var bullet: Area2D = bullet_scene.instantiate()
add_child(bullet)
# 现在 bullet 是当前节点的子节点
# 如果当前节点被 queue_free() 销毁，bullet 也会被一并销毁

# 转移所有权（把子弹移给父场景管理）
bullet.reparent(get_tree().current_scene)
# 现在子弹不随当前节点销毁了，它随场景根节点销毁而销毁

# 手动销毁
bullet.queue_free()
# queue_free() 是安全的：它不会立即销毁，而是等当前帧结束后统一清理
```

### 5.4 场景树的性能考量

- **不要过于深嵌套**：每层嵌套都增加遍历开销。如果角色有 20 层深的子节点树，每一帧都要递归 20 层。通常 3-5 层就足够了
- **使用分组（Groups）管理大量对象**：分组底层是哈希集合，查找速度 O(1)，而遍历场景树是 O(N)
- **使用 `process_priority` 控制执行顺序**：值越小越先执行（默认是 0）

```gdscript
# 让相机在角色移动之后才更新
func _ready():
    process_priority = 1  # 比默认的 0 大 → 晚执行
```

---

## 六、信号机制——解耦的艺术

### 6.1 什么是信号？

**信号（Signal）** 是 Godot 内置的**观察者模式**实现。它是一种对象间的通信机制，让一个对象可以在"某事发生了"的时候通知其他对象，而无需知道或关心"谁在听"。

**类比**：

- ❌ **直接调用**：你走过去拍每个人的肩膀说"我死了"——你需要知道每一个人的位置
- ✅ **信号**：你按下一个广播按钮，所有对此感兴趣的人自动收到通知——你不需要知道谁在听

### 6.2 信号底层的实现原理

信号的底层实现类似于一个**回调函数列表**：

```gdscript
# Godot 内部实际上维护了类似这样的结构：
class SignalInternal:
    var connected_callables: Array[Callable] = []

    func connect(callable: Callable) -> void:
        connected_callables.append(callable)

    func emit(arg1 = null, arg2 = null) -> void:
        for callable in connected_callables:
            callable.call(arg1, arg2)

    func disconnect(callable: Callable) -> void:
        var idx := connected_callables.find(callable)
        if idx != -1:
            connected_callables.remove_at(idx)
```

每当你 `emit` 一个信号，引擎会遍历所有已连接的 `Callable` 并依次调用它们。这是一个**同步过程**——信号发射后，所有连接的回调都会在**当前帧内**完成调用。

### 6.3 信号连接的全部方式

**（1）在编辑器中可视连接**

在编辑器中，选中节点 → 右侧 "Node" 标签 → "Signals" 分页 → 双击某个信号 → 选择接收节点和方法。编辑器会自动生成连接代码。

**（2）代码连接**

```gdscript
# 基本连接
func _ready() -> void:
    $Button.pressed.connect(_on_button_pressed)
    $Area2D.body_entered.connect(_on_body_entered)
    $Timer.timeout.connect(_on_timeout)

# 带参数传递的连接（使用 bind）
func _ready() -> void:
    # 发射信号时，额外的参数会 append 到回调参数后面
    $Button.pressed.connect(_on_button_pressed.bind(42))
    # 回调收到：_on_button_pressed(extra_arg: int = 42)

# 一次性连接（回调触发一次后自动断开）
func _ready() -> void:
    $Timer.timeout.connect(_on_timeout, CONNECT_ONE_SHOT)

# 延迟连接（回调在下一帧才执行——但 emit 那边的逻辑是同步的）
func _ready() -> void:
    $Timer.timeout.connect(_on_timeout, CONNECT_DEFERRED)

# 断开连接
func _ready() -> void:
    $Button.pressed.disconnect(_on_button_pressed)

# 检查是否已连接
func _ready() -> void:
    if not $Button.pressed.is_connected(_on_button_pressed):
        $Button.pressed.connect(_on_button_pressed)
```

**（3）自定义信号**

```gdscript
extends Node

# 定义信号（可以带参数类型标注）
signal health_changed(new_health: int, max_health: int)
signal player_died()
signal item_collected(item_name: String, quantity: int)

# 发射信号（Godot 4 新语法）
func take_damage(amount: int) -> void:
    health -= amount
    health_changed.emit(health, max_health)
    if health <= 0:
        player_died.emit()

func collect_item(name: String, count: int) -> void:
    inventory[name] = inventory.get(name, 0) + count
    item_collected.emit(name, count)
```

### 6.4 信号 vs. 直接调用：什么时候用哪种？

| 场景 | 用信号 | 直接调用 |
|------|:------:|:--------:|
| 你不知道谁会响应（解耦） | ✅ 最佳 | ❌ |
| 多个不同对象需要响应同一事件 | ✅ 一个 emit 全部通知 | 可以但很繁琐 |
| 父子节点间通信 | 可以用（`$Parent.my_method()`） | ✅ 更简单直接 |
| UI 交互（按钮点击、滑块变化等） | ✅ 编辑器内建支持 | ❌ |
| 严格的调用顺序很重要 | ❌ 无法保证顺序 | ✅ 你控制调用顺序 |
| 性能敏感的热路径 | ❌ 微小但可测量的开销 | ✅ 更快 |
| 需要返回值 | ❌ 信号不能返回值 | ✅ |

### 6.5 全局信号总线模式

这是 Godot 社区广泛使用的模式：创建一个全局自动加载（autoload）单例来承载跨场景的信号：

```gdscript
# signal_bus.gd（设置为 Autoload，名称：SignalBus）
extends Node

# 全局事件
signal player_died(score: int)
signal level_completed(level_id: int)
signal score_changed(new_score: int)
signal game_paused()
signal game_resumed()
```

然后在项目设置中将它添加为 Autoload。这样任何场景中的任何节点都可以：

```gdscript
# 发射信号
SignalBus.player_died.emit(final_score)

# 接收信号
func _ready() -> void:
    SignalBus.player_died.connect(_on_player_died)

func _on_player_died(score: int) -> void:
    # 显示游戏结束画面，保存分数
    pass
```

这种模式彻底解耦了场景之间的依赖——UI 不需要知道玩家节点的存在，敌人不需要知道分数系统的存在。

---

## 七、GDScript 深度解析

### 7.1 GDScript 的定位与设计理念

GDScript 是 Godot 的原生脚本语言，语法类似 Python（缩进定义代码块），但为游戏开发做了大量定制优化：

- **严格类型是可选的**：快速原型时写动态类型，正式项目加类型标注提升性能和安全性
- **游戏类型是语言的一等公民**：`Vector2`、`Vector3`、`Transform3D`、`Color`、`AABB` 等类型有语法级别的优化
- **信号是语言特性**：不是库，而是一等语言构造
- **`await` 内建支持**：原生异步/协程

为什么 Godot 不用 Lua / Python / JavaScript？因为这三者都不是为游戏帧循环设计的——它们缺少内建的 `Vector2` 等类型、没有信号概念、异步模型不匹配。GDScript 从设计之初就是**只为游戏开发服务的语言**。

### 7.2 类型系统全解

```gdscript
# === 动态类型：灵活，但运行时有类型检查开销 ===
var speed = 200          # Variant 类型，内部可以存任何东西
var name = "Player"

# === 静态类型：编辑器会给出自动补全，编译时有类型检查，运行更快 ===
var speed: float = 200.0
var name: String = "Player"
var position: Vector2 = Vector2.ZERO
var enemies: Array[Node2D] = []       # 类型化数组
var inventory: Dictionary = {}         # 字典（Key-Value）

# === 类型推断：写 := 让编译器自动推断类型 ===
var speed := 200.0              # 推断为 float
var pos := Vector2(100, 200)    # 推断为 Vector2
var is_active := true           # 推断为 bool

# === 自定义类的类型标注 ===
var player: Player              # 如果定义了 class_name Player
var scene: PackedScene           # 场景资源
var texture: Texture2D           # 贴图资源
```

**静态类型的性能收益**：当变量类型在编译期已知时，GDScript 编译器可以生成特定类型的操作指令，跳过了运行时的类型检查。在性能关键代码（如 `_process` 循环中的大量计算）中，这个差异可以达到 **20%-40%** 的性能提升。

### 7.3 `@onready` 的工作原理

```gdscript
# 传统方式：在 _ready() 中手动获取引用
var sprite: Sprite2D

func _ready() -> void:
    sprite = $Sprite2D  # 必须在这里才能安全获取

# @onready 方式：自动延迟初始化（推荐）
@onready var sprite: Sprite2D = $Sprite2D
@onready var anim_player: AnimationPlayer = $AnimationPlayer
```

`@onready` 的内部机制：

1. 变量在 `_init()` 阶段被初始化为 `null`
2. 在节点进入场景树之后、`_ready()` 调用之前，变量的赋值表达式被执行
3. 所以 `_ready()` 中访问 `@onready var` 总是安全的——它已经被赋值了

### 7.4 `@export` 的秘密

```gdscript
@export var speed: float = 200.0          # 在属性面板中出现一个数字输入框
@export var max_health: int = 100          # 整数输入框
@export var can_fly: bool = false          # 勾选框
@export var weapon_scene: PackedScene      # 场景资源拖放区
@export var sprite_frames: SpriteFrames    # 精灵帧资源拖放区
@export var team_color: Color = Color.WHITE  # 颜色选择器

# @export 的分类注解
@export_category("Movement")               # 在属性面板中创建一个分类标题
@export var walk_speed: float = 150.0
@export var run_speed: float = 300.0
@export var jump_velocity: float = -400.0

@export_category("Combat")
@export var attack_damage: int = 10
@export var attack_range: float = 50.0

# @export_range 限制数值范围
@export_range(0.0, 1.0) var volume: float = 0.8
@export_range(1, 100, 1, "or_greater") var level: int = 1

# @export_enum 限制为枚举值
@export_enum("Warrior", "Mage", "Archer") var character_class: String = "Warrior"

# @export_file 限制为文件选择器
@export_file("*.png", "*.jpg") var portrait_path: String
```

`@export` 有两个核心作用：

1. **变量值被序列化到 `.tscn` 文件中**——这意味着你可以为每个实例设置不同的值，值不会在代码修改时丢失
2. **变量出现在编辑器的属性面板中**——可视化调整，设计师和策划不需要看代码就能调参数

### 7.5 常用内置类型的完整操作

```gdscript
# ===== Vector2：2D游戏数学的核心 =====
var pos := Vector2(100, 200)       # 创建
var zero := Vector2.ZERO           # (0, 0)
var one := Vector2.ONE             # (1, 1)
var right := Vector2.RIGHT         # (1, 0)
var left := Vector2.LEFT           # (-1, 0)
var up := Vector2.UP               # (0, -1) ← 注意！Y轴向下
var down := Vector2.DOWN           # (0, 1)

# 向量运算
var sum := a + b                   # 加法
var diff := a - b                  # 减法
var scaled := a * 3.0              # 标量乘法
var length := v.length()           # 长度
var sq_length := v.length_squared()# 长度平方（更快，避免了开根号）
var dir := v.normalized()          # 归一化（方向向量，长度为 1）
var dist := a.distance_to(b)       # 两点距离
var angle := v.angle()             # 向量角度（弧度）
var dot := a.dot(b)                # 点积（判断方向关系）
var cross := a.cross(b)            # 叉积（2D 中返回标量）
var lerped := a.lerp(b, 0.5)       # 线性插值（返回 a 和 b 的中点）

# ===== Vector3：3D游戏数学的核心 =====
var pos3 := Vector3(1, 2, 3)
var forward := Vector3.FORWARD     # (0, 0, -1) ← 注意！
# 大部分 Vector2 的方法在 Vector3 中也有对应

# ===== Color：颜色表示 =====
var red := Color.RED               # (1, 0, 0, 1)  RGBA
var green := Color.GREEN           # (0, 1, 0, 1)
var blue := Color.BLUE             # (0, 0, 1, 1)
var transparent := Color(1, 0, 0, 0.5)  # 半透明红色
var from_hex := Color("#FF5733")   # 从十六进制创建
var darker := color.darkened(0.3)  # 变暗 30%
var lighter := color.lightened(0.3)# 变亮 30%

# ===== Transform2D：2D坐标变换 =====
var t := Transform2D.IDENTITY
t = Transform2D(rotation, scale, position)  # 旋转、缩放、位移
var global_pos := t * local_pos             # 局部坐标 → 全局坐标
var local_pos := t.affine_inverse() * global_pos  # 全局坐标 → 局部坐标

# ===== Array：数组（GDScript 中数组是动态的）=====
var numbers: Array[int] = [1, 2, 3, 4, 5]
numbers.append(6)                   # 追加
numbers.insert(0, 0)                # 在位置 0 插入
numbers.erase(3)                    # 删除值为 3 的元素（第一个匹配）
numbers.remove_at(0)               # 删除索引 0 处的元素
var has_5 := numbers.has(5)         # 检查是否包含
var idx := numbers.find(3)          # 查找位置（-1 表示未找到）
numbers.sort()                      # 排序
numbers.shuffle()                   # 随机打乱
var filtered := numbers.filter(func(x): return x > 2)  # 过滤
var mapped := numbers.map(func(x): return x * 2)       # 映射

# ===== Dictionary：字典 =====
var data: Dictionary = {
    "name": "Hero",
    "hp": 100,
    "items": ["sword", "shield"]
}
var name: String = data["name"]     # 访问
data["mp"] = 50                     # 添加/修改
var has_key := data.has("hp")       # 检查键是否存在
data.erase("mp")                    # 删除键
for key in data:                    # 遍历键
    print(key, ": ", data[key])
for value in data.values():         # 遍历值
    print(value)
```

### 7.6 `await` 和协程

Godot 4 使用 `await` 关键字处理异步，摒弃了 Godot 3 的 `yield`：

```gdscript
# 等待一段时间
func delayed_action() -> void:
    await get_tree().create_timer(2.0).timeout
    print("2 秒后执行")

# 等待动画播放完成
func play_and_wait() -> void:
    $AnimationPlayer.play("attack")
    await $AnimationPlayer.animation_finished
    $AnimationPlayer.play("idle")

# 等待下一帧
func wait_one_frame() -> void:
    await get_tree().process_frame
    # 下一帧的代码

# 等待下一个物理帧
func wait_one_physics_frame() -> void:
    await get_tree().physics_frame
    # 下一个物理帧的代码

# 等待信号（带超时）
func wait_with_timeout(timeout: float = 1.0) -> bool:
    var elapsed := 0.0
    while elapsed < timeout:
        if check_condition():
            return true
        await get_tree().physics_frame
        elapsed += get_physics_process_delta_time()
    return false  # 超时

# 链式异步操作（模拟加载流程）
func load_game() -> void:
    show_loading_screen()
    await get_tree().process_frame  # 等一帧让加载画面显示
    await load_player_data()
    await load_level_data()
    await get_tree().create_timer(0.5).timeout  # 让玩家看到加载画面
    hide_loading_screen()
    start_game()
```

**底层原理**：`await` 实际上将当前函数挂起，把执行权交还给引擎主循环。当等待的条件满足时，函数从暂停点继续执行。注意这不是多线程——Godot 是单线程游戏循环模型。如果 `await` 后面的代码会花很长时间（如加载大量资源），它仍然会阻塞主线程。

### 7.7 `class_name` 和自定义类

```gdscript
# player.gd
class_name Player
extends CharacterBody2D

# 这个脚本现在是一个"类型"，可以在其他地方标注使用
@export var move_speed: float = 200.0
@export var jump_velocity: float = -400.0

func take_damage(amount: int) -> void:
    # ...
    pass

# 在其他脚本中
var player: Player = $Player       # 类型安全的引用
player.take_damage(10)             # 编辑器会给出自动补全
```

使用 `class_name` 后，这个脚本在编辑器的节点列表中会显示为一行，创建新节点时可以直接选择。

---

## 八、物理引擎底层原理

### 8.1 物理节点体系

Godot 4 的物理节点分为四大类：

```
CollisionObject2D/3D（碰撞对象基类）
├── StaticBody2D/3D      —— 完全不动的物体（墙壁、地板、平台）
├── RigidBody2D/3D       —— 完全物理模拟（重力、碰撞反弹、旋转惯性）
├── CharacterBody2D/3D   —— 代码控制移动但仍检测碰撞（玩家、NPC）
└── Area2D/3D            —— 检测区域，不产生物理碰撞（触发器、伤害范围）
```

**选择规则**：
- 物体需要自然下落、被推、碰撞反弹？→ `RigidBody2D`（木箱、足球、弹珠）
- 物体需要在代码中精确控制移动但需要检测碰撞？→ `CharacterBody2D`（玩家、敌人）
- 物体完全不动只做阻挡？→ `StaticBody2D`（地面、墙壁）
- 只需要知道"有东西进入了这个区域"？→ `Area2D`（金币拾取范围、攻击判定框）

### 8.2 CharacterBody2D 的 `move_and_slide()` 原理

这是 2D 游戏中最常用的移动方式。`move_and_slide()` 内部做了非常复杂的处理：

```gdscript
extends CharacterBody2D

@export var speed: float = 300.0
@export var jump_velocity: float = -400.0

# 获取重力（从项目设置中读取默认重力值）
var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")

func _physics_process(delta: float) -> void:
    # 1. 施加重力
    if not is_on_floor():
        velocity.y += gravity * delta

    # 2. 处理跳跃输入
    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    # 3. 处理水平移动
    var direction := Input.get_axis("move_left", "move_right")
    if direction != 0:
        velocity.x = direction * speed
    else:
        velocity.x = move_toward(velocity.x, 0, speed * delta * 10)  # 减速摩擦

    # 4. 执行移动和碰撞处理
    move_and_slide()
```

当 `move_and_slide()` 被调用时，引擎内部做了这些事情：

1. **读取当前的 `velocity`**
2. **沿速度方向做离散碰撞检测**：将一次移动分解为多次小的步进，每次步进检测是否碰撞
3. **碰到墙壁时**：
   - 将速度沿墙壁法线方向的分量归零（所以你不会穿过墙）
   - 保留沿墙壁切线方向的分量（所以你沿墙滑行而不是卡住）
4. **碰到地板时**：
   - `is_on_floor()` 返回 `true`
   - 更新 `get_last_motion()` 为实际移动的距离
5. **碰到天花板时**：
   - `is_on_ceiling()` 返回 `true`
6. **碰到斜坡时**：
   - 自动沿斜坡向上或向下滑动（除非设置 `floor_block_on_wall`）

### 8.3 碰撞检测的数学：分离轴定理（SAT）

Godot 使用 **分离轴定理（Separating Axis Theorem，SAT）** 进行 2D 凸多边形的碰撞检测。这是一个优雅而高效的算法：

**核心思想**：对于两个凸多边形 A 和 B：
- 取 A 的所有边的法向量 + B 的所有边的法向量，作为**候选分离轴**
- 将 A 和 B 分别投影到每个轴上
- 如果存在任何一个轴，使得 A 和 B 在该轴上的投影**不重叠** → **没有碰撞！**
- 如果所有轴上的投影都重叠 → **发生了碰撞**

```
示意图（两个矩形）：

    轴1（水平）
    A的投影: [0 ─────────── 100]
    B的投影:       [50 ─────────── 150]
    结论：投影重叠 → 在这个轴上无法分离

    轴2（垂直）
    A的投影: [0 ── 50]
    B的投影:          [60 ── 110]
    结论：投影不重叠！→ 存在分离轴 → A 和 B 没有碰撞！
```

这就是为什么 Godot 的碰撞检测只对**凸多边形**有效——SAT 算法的前提是多边形必须是凸的。如果你需要用凹多边形做碰撞体，需要拆分成多个凸多边形。

### 8.4 碰撞层和掩码透彻理解

```gdscript
# collision_layer：我"属于"哪些层（我是谁？）
# collision_mask：我要"检测"哪些层（我能碰到谁？）
# 每层是一个位（bit），共 32 层（第 0 层到第 31 层）

# 示例设置
collision_layer = 1        # 二进制：0000_0000_0000_0001 → 我属于第 1 层（玩家层）
collision_mask = 2 | 4     # 二进制：0000_0000_0000_0110 → 我检测第 2 层（敌人层）和第 3 层（道具层）

# 等效写法
collision_layer = 1 << 0   # 第 0 位 = 第 1 层
collision_mask = (1 << 1) | (1 << 2)  # 第 1 位和第 2 位 = 第 2 层和第 3 层
```

**实际项目中的层设计示例**：

| 层编号 | 用途 |
|:------:|------|
| 1 | 玩家 |
| 2 | 敌人 |
| 3 | 玩家子弹 |
| 4 | 敌人子弹 |
| 5 | 地面/墙壁 |
| 6 | 可拾取道具 |
| 7 | 检测区域（触发器） |

然后设置：
- 玩家的 `collision_mask` = 2 | 4 | 5 | 6 → 能被敌人碰到、被敌人子弹打中、站在地面上、拾取道具
- 玩家子弹的 `collision_mask` = 2 → 只检测敌人（不会打中玩家）
- 敌人的 `collision_mask` = 1 | 3 | 5 → 能碰到玩家、被玩家子弹打中、站在地面上

这样就天然避免了友军伤害。

---

## 九、渲染管线概览

### 9.1 Godot 4 的渲染后端

```
RenderingServer（渲染服务器——所有渲染请求的中枢）
├── Vulkan 后端（主力渲染器：现代、高性能、跨平台）
├── OpenGL 3 后端（兼容模式：适配旧设备）
└── 移动端优化路径（Vulkan Mobile / OpenGL ES）
```

Godot 4 使用 **Forward+ 渲染**（前向+渲染）作为默认的 3D 渲染方式：

**Forward+ 的渲染流程**：

1. **深度预遍（Depth Pre-pass）**：先渲染一次场景中所有不透明物体，**只写入深度缓冲**（不写颜色）。这一步之后，深度缓冲里记录了每个像素的深度值
2. **光照聚类（Light Clustering）**：将屏幕分成网格（如每个 tile 是 16×16 像素），对每个 tile 分析哪些光源会影响它。即使场景中有 1000 个灯光，每个像素也只需要计算附近几个灯——大幅减少光照计算量
3. **前向渲染（Forward Rendering）**：对每个物体进行着色。对于透明物体，在最后单独处理（因为透明物体不能走深度预遍）

**为什么选 Forward+ 而不是延迟渲染（Deferred Rendering）？**
- Forward+ 天然支持 MSAA 抗锯齿（延迟渲染很难做 MSAA）
- Forward+ 的透明物体处理更自然（延迟渲染中透明物需要额外的前向通道）
- Forward+ 在不同硬件上的表现更一致

### 9.2 Canvas——Godot 2D 渲染的秘密

这是理解 Godot 2D 性能为什么如此优秀的关键：

Godot 的 2D 渲染**不是**把 3D 渲染管线"降维"使用，而是拥有一套**完全独立的 2D 渲染管线**。

每个 `CanvasItem`（`Node2D` 或 `Control`）节点对应一个或多个绘制命令。这些命令存储在节点自己的绘制列表中：

```gdscript
# 你可以在 _draw() 中自定义绘制
func _draw() -> void:
    draw_rect(Rect2(0, 0, 100, 100), Color.RED)
    draw_circle(Vector2(50, 50), 30, Color.BLUE)
    draw_line(Vector2(0, 0), Vector2(100, 100), Color.GREEN, 2.0)
    draw_string(ThemeDB.fallback_font, Vector2(10, 10), "Hello!")
```

渲染时，当前 `Viewport` 的 Canvas 收集所有 `CanvasItem` 的绘制命令，按 `z_index` 排序，然后批量提交给 GPU：

```
Viewport
└── Canvas（管理该视口的所有 2D 绘制命令）
    ├── CanvasItem 1（z_index = 0）
    │   ├── draw_texture(...)
    │   └── draw_rect(...)
    ├── CanvasItem 2（z_index = 1）
    │   └── draw_texture(...)
    └── CanvasItem 3（z_index = -1，在背景层）
        └── draw_circle(...)

渲染顺序：先渲染 z_index 小的，后渲染 z_index 大的（大的覆盖小的）
```

这也是为什么 Godot 2D 能做到"几万个精灵同时移动不卡"——它不需要走 3D 管线的完整流程（不需考虑相机投影、光照、材质等）。

---

## 十、动画系统

### 10.1 AnimationPlayer——Godot 的动画核心

`AnimationPlayer` 可以动画化**任何节点的任何属性**。你不需要给每个属性单独创建动画曲线——一个 `AnimationPlayer` 管理该节点及其所有子节点上所有属性的动画：

```gdscript
# 代码驱动动画播放
func play_animation() -> void:
    $AnimationPlayer.play("walk")          # 播放
    $AnimationPlayer.play("attack")        # 切换
    await $AnimationPlayer.animation_finished  # 等待播完
    $AnimationPlayer.play("idle")          # 回到 idle

# 队列播放（当前动画播完后自动播下一个）
func queue_animation() -> void:
    $AnimationPlayer.play("walk")
    $AnimationPlayer.queue("idle")

# 设置播放速度
func speed_up() -> void:
    $AnimationPlayer.speed_scale = 1.5           # 1.5 倍速

# 设置混合时间
func setup_blending() -> void:
    var anim := $AnimationPlayer.get_animation("walk")
    anim.blend_time = 0.2           # 从其他动画切换到 walk 时，用 0.2 秒混合

# 检查当前状态
func check_state() -> void:
    var is_playing: bool = $AnimationPlayer.is_playing()
    var current_anim: String = $AnimationPlayer.current_animation
    var position: float = $AnimationPlayer.current_animation_position
```

### 10.2 AnimationTree——状态机动画系统

对于角色的动作系统（一个角色同时只能处于一种动画状态：idle / walk / run / jump / attack 等），推荐使用 `AnimationTree` 配合 `AnimationNodeStateMachine`：

```
状态机示例：

    ┌──────┐    ←→    ┌──────┐    ←→    ┌──────┐
    │ Idle │          │ Walk │          │ Run  │
    └──────┘          └──────┘          └──────┘
       ↓  ↑              ↓  ↑
    ┌──────┐          ┌────────┐
    │ Jump │          │ Attack │
    └──────┘          └────────┘
       ↓
    ┌──────┐
    │ Fall │
    └──────┘
```

```gdscript
# 通过 AnimationTree 控制动画状态
@onready var anim_tree: AnimationTree = $AnimationTree
@onready var state_machine: AnimationNodeStateMachinePlayback = anim_tree["parameters/playback"]

func _physics_process(delta: float) -> void:
    # 根据角色状态切换动画
    if not is_on_floor():
        if velocity.y < 0:
            state_machine.travel("Jump")
        else:
            state_machine.travel("Fall")
    elif abs(velocity.x) > run_threshold:
        state_machine.travel("Run")
    elif abs(velocity.x) > 10:
        state_machine.travel("Walk")
    else:
        state_machine.travel("Idle")
```

`AnimationTree` 的优雅之处在于它自动管理动画**混合（Blending）**——从 Walk 切换到 Run 不是瞬间切换，而是在你设置的混合时间内平滑过渡。

### 10.3 Tween——代码驱动的补间动画

`Tween` 用于在代码中创建平滑的属性变化，非常适合 UI 动画、特效、过场等：

```gdscript
# 创建 Tween
var tween := create_tween()

# 基础用法：2 秒内将节点从当前位置移动到 (500, 300)
tween.tween_property($Sprite, "position", Vector2(500, 300), 2.0)

# 设置缓动曲线和过渡类型
tween.tween_property($Sprite, "scale", Vector2(2, 2), 1.0)\
    .set_ease(Tween.EASE_OUT)\
    .set_trans(Tween.TRANS_BACK)

# 链式动画（按顺序执行）
var tween := create_tween()
tween.tween_property($Sprite, "scale", Vector2(1.5, 1.5), 0.5)   # 先放大
tween.tween_property($Sprite, "rotation", TAU, 1.0)               # 再旋转一圈
tween.tween_property($Sprite, "scale", Vector2(1, 1), 0.5)        # 再缩回原大小

# 并行动画（同时执行）
var tween := create_tween()
tween.set_parallel(true)
tween.tween_property($Sprite, "position:x", 500, 1.0)   # 同时移X
tween.tween_property($Sprite, "position:y", 300, 1.0)   # 同时移Y
tween.tween_property($Sprite, "modulate:a", 0.0, 1.0)   # 同时淡出

# 带回调的序列
var tween := create_tween()
tween.tween_property($Enemy, "modulate", Color.RED, 0.1)          # 闪红一下
tween.tween_callback(_on_enemy_hit_flash_complete)                # 闪完回调

# 循环动画
var tween := create_tween()
tween.set_loops()  # 无限循环
tween.tween_property($Indicator, "position:y", -10, 0.5)\
    .set_ease(Tween.EASE_IN_OUT)\
    .set_trans(Tween.TRANS_SINE)
tween.tween_property($Indicator, "position:y", 10, 0.5)\
    .set_ease(Tween.EASE_IN_OUT)\
    .set_trans(Tween.TRANS_SINE)
```

**可用的缓动类型（`set_ease`）**：
- `Tween.EASE_IN` —— 慢→快（加速入场）
- `Tween.EASE_OUT` —— 快→慢（减速出场）
- `Tween.EASE_IN_OUT` —— 慢→快→慢
- `Tween.EASE_OUT_IN` —— 快→慢→快

**可用的过渡类型（`set_trans`）**：
- `Tween.TRANS_LINEAR` —— 线性
- `Tween.TRANS_SINE` —— 正弦曲线
- `Tween.TRANS_QUINT` —— 五次曲线
- `Tween.TRANS_EXPO` —— 指数曲线
- `Tween.TRANS_ELASTIC` —— 弹性（像弹簧一样）
- `Tween.TRANS_BOUNCE` —— 弹跳
- `Tween.TRANS_BACK` —— 回退（先超过目标再回退）

---

## 十一、UI 系统

### 11.1 Control 节点的锚点系统

Godot 的 UI 建立在 `Control` 节点体系上。每个 `Control` 都是一个矩形区域，通过**锚点（Anchors）**和**边距（Offsets）**来定位：

- **锚点**：定义了控件相对于**父容器**哪个位置"钉住"。锚点是比例值（0.0 到 1.0），`(0, 0)` 是左上角，`(1, 1)` 是右下角
- **边距**：相对于锚点位置的偏移（像素）

**常用的锚点预设**：

```
左上角锚定（默认）：控件从父容器的左上角偏移 margin
    anchor_left = 0, anchor_top = 0

全屏拉伸：控件随父容器尺寸变化而变化
    anchor_left = 0, anchor_top = 0, anchor_right = 1, anchor_bottom = 1

底部居中：控件始终在父容器底部中间
    anchor_left = 0.5, anchor_top = 1, anchor_right = 0.5, anchor_bottom = 1

居中：控件始终在父容器正中心
    anchor_left = 0.5, anchor_top = 0.5, anchor_right = 0.5, anchor_bottom = 0.5
```

### 11.2 九个重要的自动布局容器

`Container` 类节点会自动排列其子 `Control` 节点，不需要你手动计算位置：

```gdscript
# HBoxContainer —— 水平排列子控件
HBoxContainer:
    ├── Label "生命："
    ├── ProgressBar (血条)
    └── Label "100/100"

# VBoxContainer —— 垂直排列子控件
VBoxContainer:
    ├── Label "标题"
    ├── Button "开始游戏"
    ├── Button "设置"
    └── Button "退出"

# GridContainer —— 网格排列（自动计算列数）
GridContainer (columns = 3):
    ├── Button "1"  ├── Button "2"  ├── Button "3"
    ├── Button "4"  ├── Button "5"  ├── Button "6"
    └── Button "7"  ├── Button "8"  ├── Button "9"

# MarginContainer —— 为单个子控件添加统一的边距
# CenterContainer —— 将单个子控件在中心居中
# PanelContainer —— 带样式背景面板的单子控件容器
# ScrollContainer —— 当子内容超出容器大小时自动出现滚动条
# AspectRatioContainer —— 强制子控件保持特定宽高比
# FlowContainer —— CSS Flexbox 风格的流式布局，自动换行
```

### 11.3 主题系统

```gdscript
# 在代码中修改单个控件的样式
func apply_style() -> void:
    $Button.add_theme_color_override("font_color", Color.RED)
    $Button.add_theme_color_override("font_hover_color", Color.YELLOW)
    $Label.add_theme_font_size_override("font_size", 24)
    $Panel.add_theme_stylebox_override("panel", preload("res://my_panel_style.tres"))

# 自定义字体
func set_custom_font() -> void:
    var font := load("res://assets/fonts/my_font.ttf") as FontFile
    $Label.add_theme_font_override("font", font)

# 创建 Theme 资源（全局主题）
# 在编辑器中创建 Theme 资源 → 设置默认字体、按钮样式、颜色等
# 然后设置到项目的 GUI → Theme 覆盖中
```

---

## 十二、资源管理

### 12.1 资源（Resource）是什么？

在 Godot 中，**资源（Resource）** 是一个可以序列化、可以在多个地方共享的数据容器。它是独立于节点的：

```
Resource 体系
├── Texture2D（图片）
│   ├── ImageTexture          —— 从代码中动态创建的贴图
│   ├── CompressedTexture2D   —— 导入的压缩贴图（png/jpg）
│   └── AtlasTexture          —— 图集中的一部分
├── Material（材质）
│   ├── StandardMaterial3D    —— 标准 3D 材质
│   └── ShaderMaterial        —— 自定义着色器材质
├── Font（字体）
│   ├── FontFile              —— 字体文件
│   └── SystemFont            —— 系统字体
├── AudioStream（音频流）
│   ├── AudioStreamMP3
│   ├── AudioStreamWAV
│   └── AudioStreamOggVorbis
├── AnimationLibrary
├── Shape2D / Shape3D（碰撞形状）
│   ├── CircleShape2D
│   ├── RectangleShape2D
│   ├── CapsuleShape2D
│   ├── BoxShape3D
│   └── SphereShape3D
├── TileSet（瓦片集）
├── GDScript（是的，脚本也是资源！）
├── PackedScene（场景也是资源！）
└── 自定义 Resource
```

### 12.2 引用计数——资源的内存管理

Godot 使用 **引用计数（Reference Counting）** 管理资源内存，不需要手动释放：

```gdscript
var texture := load("res://icon.svg") as Texture2D
# 此时 texture 的引用计数 = 1

var sprite1 := Sprite2D.new()
sprite1.texture = texture
# 引用计数 = 2（sprite1 也持有对纹理的引用）

var sprite2 := Sprite2D.new()
sprite2.texture = texture
# 引用计数 = 3

# 当 sprite1 被销毁时，引用计数 -1 → 2
# 当 sprite2 被销毁时，引用计数 -1 → 1
# 当 texture 变量被赋值为 null 时，引用计数 -1 → 0
# 引用计数为 0 → 资源自动从内存中卸载
```

这就是为什么你可以放心使用 `load()` 而不用担心内存泄漏——引擎在后台维护引用计数。

### 12.3 路径系统：`res://` 和 `user://`

```gdscript
# res:// —— 指向项目根目录
# 只读（打包后在 .pck 文件中，无法写入）
var texture := load("res://assets/textures/player.png")
var scene := load("res://scenes/main.tscn") as PackedScene

# user:// —— 指向用户数据目录
# 可读写（用于游戏存档、配置文件等）
# 实际路径取决于操作系统：
#   Windows: %APPDATA%/Godot/app_userdata/项目名/
#   Linux:   ~/.local/share/godot/app_userdata/项目名/
#   macOS:   ~/Library/Application Support/Godot/app_userdata/项目名/

func save_game() -> void:
    var file := FileAccess.open("user://savegame.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(game_data))

func load_game() -> Variant:
    if not FileAccess.file_exists("user://savegame.json"):
        return null
    var file := FileAccess.open("user://savegame.json", FileAccess.READ)
    return JSON.parse_string(file.get_as_text())
```

### 12.4 自定义 Resource

你可以创建自己的资源类型，非常适合存储游戏数据：

```gdscript
# character_stats.gd
class_name CharacterStats
extends Resource

@export var character_name: String = "无名"
@export var max_health: int = 100
@export var attack: int = 10
@export var defense: int = 5
@export var move_speed: float = 200.0
@export var portrait: Texture2D

# 在编辑器中：右键 → 新建资源 → CharacterStats
# 就可以创建一个 .tres 文件来存储角色数据
# 然后拖到任何 @export var stats: CharacterStats 属性中
```

这在数据驱动设计中非常强大——你可以为每种敌人创建一个 `.tres` 文件定义其属性，策划不需要碰代码就能调整数值。

---

## 十三、从零开始：你的第一个完整游戏

让我们构建一个完整的躲避游戏，以此串联所有学到的概念。

### 游戏设计

- 玩家在屏幕底部左右移动
- 敌人（彩色方块）从屏幕顶部不断掉落
- 碰到敌人就 Game Over
- 得分随时间增长
- 显示 UI（分数、游戏结束面板、重新开始按钮）

### 项目节点结构

```
Game (Node2D) —— 游戏主场景
├── Player (CharacterBody2D) —— 玩家角色
│   ├── Sprite2D —— 蓝色方块（玩家的视觉）
│   ├── CollisionShape2D —— 矩形碰撞体
│   └── Area2D —— 与敌人的碰撞检测
│       └── CollisionShape2D
├── EnemySpawner (Node2D) —— 敌人生成器
│   └── Timer —— 控制生成间隔
└── UI (CanvasLayer) —— UI 层（始终在画面最前方）
    ├── ScoreLabel (Label) —— 分数显示
    └── GameOverPanel (Panel) —— 游戏结束面板
        ├── Label ("游戏结束！")
        ├── Label (最终分数)
        └── Button ("重新开始")
```

### SignalBus（全局信号总线）

```gdscript
# signal_bus.gd —— 设置为 Autoload，名称 SignalBus
extends Node

signal player_died(final_score: int)
signal score_changed(new_score: int)
```

### Player.gd

```gdscript
class_name Player
extends CharacterBody2D

@export var speed: float = 400.0

func _ready() -> void:
    # Area2D 检测到敌人 → game over
    $Area2D.body_entered.connect(_on_body_entered)

func _physics_process(_delta: float) -> void:
    # 水平移动
    var direction := Input.get_axis("move_left", "move_right")
    velocity.x = direction * speed
    move_and_slide()

    # 限制在屏幕内（32 是角色一半宽度）
    global_position.x = clampf(
        global_position.x,
        32.0,
        get_viewport_rect().size.x - 32.0
    )

func _on_body_entered(body: Node2D) -> void:
    if body is Enemy:
        die()

func die() -> void:
    set_physics_process(false)  # 停止移动
    hide()                       # 隐藏角色
    SignalBus.player_died.emit(score)  # 通知全局信号总线
```

### Enemy.gd

```gdscript
class_name Enemy
extends Area2D

@export var fall_speed: float = 300.0

func _physics_process(delta: float) -> void:
    position.y += fall_speed * delta

    # 掉出屏幕底部后自动回收
    if position.y > get_viewport_rect().size.y + 50.0:
        queue_free()

func _on_body_entered(body: Node2D) -> void:
    if body is Player:
        body.die()          # 通知玩家死亡
    queue_free()            # 敌人自己也消失
```

### EnemySpawner.gd

```gdscript
class_name EnemySpawner
extends Node2D

@export var enemy_scene: PackedScene
@export var spawn_interval: float = 1.0
@export var min_x: float = 50.0
@export var max_x: float = 350.0

var score: int = 0

func _ready() -> void:
    $Timer.wait_time = spawn_interval
    $Timer.timeout.connect(_spawn_enemy)
    $Timer.start()

    # 监听游戏结束
    SignalBus.player_died.connect(_on_player_died)

func _spawn_enemy() -> void:
    if not enemy_scene:
        return

    var enemy := enemy_scene.instantiate() as Enemy
    enemy.position = Vector2(
        randf_range(min_x, max_x),
        -50.0  # 从屏幕顶部上方出现
    )
    enemy.body_entered.connect(_on_enemy_hit)
    add_child(enemy)

    # 增加分数
    score += 10
    SignalBus.score_changed.emit(score)

func _on_enemy_hit(_body: Node2D) -> void:
    pass  # 在 Enemy 自身的回调中处理

func _on_player_died(_final_score: int) -> void:
    $Timer.stop()
```

### GameUI.gd

```gdscript
class_name GameUI
extends CanvasLayer

func _ready() -> void:
    SignalBus.score_changed.connect(_on_score_changed)
    SignalBus.player_died.connect(_on_player_died)

    $GameOverPanel.hide()
    $GameOverPanel/Button.pressed.connect(_restart_game)

func _on_score_changed(new_score: int) -> void:
    $ScoreLabel.text = "分数：%d" % new_score

func _on_player_died(final_score: int) -> void:
    $GameOverPanel.show()
    $GameOverPanel/FinalScoreLabel.text = "最终分数：%d" % final_score

func _restart_game() -> void:
    get_tree().reload_current_scene()
```

### 输入映射（Input Map）

在项目设置 → 输入映射中添加以下动作：
- `move_left`：键盘 A 键 / 左箭头键
- `move_right`：键盘 D 键 / 右箭头键

---

## 十四、进阶话题概览

以下每个话题都可以单独展开为一篇万字长文，这里给出概要和学习方向。

### 14.1 着色器（Shader）

Godot 有两种着色器编写方式：
- **Godot Shading Language**（文本代码，类似 GLSL 但做了简化）
- **Visual Shader**（节点式可视化编辑，无需写代码）

```glsl
// 一个 2D 溶解效果的片段着色器
shader_type canvas_item;

uniform float dissolve_amount: hint_range(0.0, 1.0) = 0.0;
uniform sampler2D noise_texture;
uniform vec4 edge_color: source_color = vec4(1.0, 0.5, 0.0, 1.0);

void fragment() {
    vec4 color = texture(TEXTURE, UV);
    float noise = texture(noise_texture, UV).r;

    // 噪声小于溶解阈值 → 像素变为透明
    float edge = step(dissolve_amount, noise) - step(dissolve_amount + 0.05, noise);
    color.a *= step(dissolve_amount, noise);
    color.rgb += edge * edge_color.rgb;  // 溶解边缘发光

    COLOR = color;
}
```

### 14.2 多人网络

Godot 4 内置了 ENet 网络库，支持：
- **RPC（远程过程调用）**：`@rpc` 注解的方法会通过网络同步调用
- **网络同步器（MultiplayerSynchronizer）**：自动同步属性值
- **权威服务器模式**：服务器拥有最终决定权，客户端做预测
- **P2P 模式**：每个玩家之间的直接连接

### 14.3 GDExtension（C++ 扩展）

如果你需要极致性能或使用 C++ 生态的库，可以编写 GDExtension：

```cpp
// 编译成 .dll / .so / .dylib，在 Godot 中像普通节点一样使用
#include <godot_cpp/classes/sprite2d.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

class FastNode : public Sprite2D {
    GDCLASS(FastNode, Sprite2D)

protected:
    static void _bind_methods() {}

public:
    void _process(double delta) override {
        // 这里的代码以 C++ 原生速度运行
        set_position(get_position() + Vector2(100.0 * delta, 0.0));
    }
};
```

此外，通过社区绑定还支持 **Rust**、**Swift**、**Nim**、**Zig** 等语言编写扩展。

### 14.4 TileMap（瓦片地图）

Godot 4 的 TileMap 系统完全重写了，是目前 2D 引擎中最先进的瓦片地图之一：
- **多层瓦片**：地面层、装饰层、碰撞层分别管理
- **自动拼接**：画一条路，相邻瓦片自动匹配拼接
- **地形系统**：定义不同的地形类型（草地、泥土、水），画一个区域自动匹配过渡
- **导航网格**：自动生成寻路用的导航图

---

## 十五、常见陷阱与最佳实践

### 15.1 不要做的事

| ❌ 错误做法 | ✅ 正确做法 | 原因 |
|------------|-----------|------|
| 在 `_process()` 中 `load()` 资源 | 在 `_ready()` 或 `@onready` 中预加载 | `load()` 有 I/O 开销，每帧调用会卡顿 |
| 在 `_process()` 中 `get_node()` | 用 `@onready var ref = $Node` 缓存引用 | `get_node()` 有查找开销 |
| 忽略 `delta` 参数 | 所有帧相关计算乘以 `delta` | 不乘 delta 会导致不同帧率下行为不一致 |
| 用 `==` 比较浮点数 | 使用 `is_equal_approx()` 或 `abs(a - b) < 0.001` | 浮点数精度问题 |
| 用 `queue_free()` 后继续使用该节点 | `queue_free()` 后立即 `return`，不再使用 | `queue_free()` 是延迟销毁 |
| 忘记断开信号连接 | 使用 `CONNECT_ONE_SHOT` 或在 `_exit_tree()` 中断开 | 可能导致对象已被销毁但回调仍被调用 |
| `RigidBody2D` 和 `CharacterBody2D` 混用 | 选择其一，不要给同一个物体同时设置两种移动 | 两者冲突会导致不可预测的行为 |
| 每帧都创建新对象（子弹等） | 使用对象池（Object Pool）复用 | 频繁创建销毁会导致 GC 尖峰 |
| 在 `_input()` 中处理移动 | 在 `_physics_process()` 中使用 `Input.get_vector()` 等函数 | `_input()` 每输入事件调用一次，不适合持续移动 |

### 15.2 性能优化清单

1. **Profile before optimizing**（先测量再优化）——使用 Godot 内置的调试器 → 性能分析器
2. **减少绘制调用**——合并精灵到图集（Atlas），减少纹理切换次数
3. **正确使用碰撞层和掩码**——不要让每个物体扫描所有其他物体
4. **可见性剔除**——使用 `VisibleOnScreenNotifier2D` / `VisibleOnScreenEnabler2D` 让离屏物体暂停处理
5. **对象池**——对于频繁创建/销毁的物体（子弹、粒子、特效），用对象池复用
6. **静态物体不要覆写 `_process()`**——`StaticBody2D` 不需要每帧处理
7. **使用 `NavigationServer`**——对于大量寻路单位，使用底层的 NavigationServer API 比逐节点查询快得多
8. **`set_process(false)`**——不需要每帧更新的节点，主动关掉 `_process`

```gdscript
# 对象池的简单实现
class_name ObjectPool
extends Node

@export var scene: PackedScene
@export var pool_size: int = 20

var _pool: Array[Node] = []

func _ready() -> void:
    for i in pool_size:
        var obj := scene.instantiate()
        obj.set_process(false)
        obj.hide()
        add_child(obj)
        _pool.append(obj)

func get_object() -> Node:
    for obj in _pool:
        if not obj.visible:  # 不可见 = 空闲
            obj.show()
            obj.set_process(true)
            return obj
    # 池耗尽则新建
    var obj := scene.instantiate()
    add_child(obj)
    _pool.append(obj)
    return obj

func return_object(obj: Node) -> void:
    obj.hide()
    obj.set_process(false)
```

### 15.3 项目目录结构建议

```
res://
├── assets/              # 所有资源文件
│   ├── textures/        # 贴图（按类型分子文件夹）
│   │   ├── characters/
│   │   ├── environments/
│   │   ├── ui/
│   │   └── effects/
│   ├── sounds/          # 音效
│   ├── music/           # 背景音乐
│   └── fonts/           # 字体文件
├── scenes/              # 场景文件
│   ├── player/
│   ├── enemies/
│   ├── levels/
│   └── ui/
├── scripts/             # GDScript 脚本
│   ├── autoload/        # 全局自动加载单例
│   ├── components/      # 可复用的组件脚本
│   └── utils/           # 工具和辅助函数
├── shaders/             # 着色器
├── resources/           # 自定义资源文件（.tres）
│   ├── characters/      # 角色数据（CharacterStats）
│   └── items/           # 物品数据
└── addons/              # 第三方插件
```

---

## 学习路线图建议

```
第 1 周：学会移动一个方块，理解节点和场景的基本概念
    → 输出：一个能用键盘左右移动的彩色方块

第 2 周：加入碰撞和敌人，做一个简单的躲避游戏
    → 输出：有障碍物、有碰撞检测、有分数的小游戏

第 3 周：学习信号和 UI，加入菜单和计分系统
    → 输出：有主菜单、记分、游戏结束画面的完整游戏流程

第 4 周：学习 AnimationPlayer，让角色动起来
    → 输出：角色有 idle/walk/jump 动画

第 5 周：深入学习 GDScript 的类型系统、await 和资源管理
    → 输出：代码质量提升，开始使用静态类型和自定义 Resource

第 6 周：掌握 TileMap，做一个有地形的完整关卡
    → 输出：一个有地板、墙壁、平台的 2D 平台跳跃关卡

第 7-8 周：学习着色器和粒子效果
    → 输出：加入视觉特效（粒子、后处理、shader 动画）

第 9-12 周：完成一个完整游戏并导出发布
    → 输出：一个可以发到 itch.io 的完整游戏
```

**最重要的建议**：不要等到"学完"才开始做。第一天就做一个能动的方块，第二天就加上障碍物，第三天就加上得分。最好的学习就是动手做项目，遇到不懂的去查文档、看源码。

Godot 官方文档质量极高，有中文翻译：
- 官方文档：https://docs.godotengine.org/ （选择 `zh_CN` 语言）
- 官方教程：https://docs.godotengine.org/zh_CN/stable/getting_started/step_by_step/
- Godot 社区：https://godotengine.org/community/

---

*本文基于 Godot 4.X 系列撰写。如果你有具体的方面想深入了解（如着色器编程、多人网络同步、GDExtension 开发、物理引擎源码分析等），后续可以继续展开。*
