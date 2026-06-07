---
title: 'Godot节点完全参考手册：属性、方法、信号详解'
date: 2026-06-07T12:00:00+08:00
draft: false
tags: ["Godot", "游戏开发", "GDScript", "节点参考", "API文档"]
---

<!--
  目录自动生成说明：
  文章中的 ## 和 ### 标题会自动生成目录，出现在文章开头。
  使用 ## 标题 作为一级目录项，### 标题 作为二级目录项。
  点击目录项可平滑滚动到对应位置。
-->

## 前言：为什么要写这篇手册

Godot 官方文档很全面，但对于新手来说，几百个节点、上千个属性和方法散布在各个页面中，很难形成体系化的认知。本文的目标是：**把 Godot 4 中最常用的节点逐一类聚，用纯 GDScript 代码示例讲清楚每个节点的核心属性、方法和信号，让你能快速查阅并立即投入使用。**

本文不是官方文档的翻译——官方文档是"字典"，本文是"导读"。我会告诉你每个节点**在什么场景下用**、**最重要的几个属性是什么**、**最常用的方法怎么调用**、**有哪些坑需要注意**。

所有代码示例使用原生 **GDScript**，基于 **Godot 4.X** 系列。

---

## 一、Node——万物之源

`Node` 是所有节点的基类，理解它就理解了整个引擎的基础。

### 1.1 核心属性

```gdscript
# 基础属性
node.name             # 节点名称（在场景树中唯一标识）
node.owner            # 节点的"所有者"（通常是场景的根节点）
node.scene_file_path  # 该节点所属的 .tscn 文件路径

# 场景树相关
node.process_priority       # _process() 的执行优先级（越小越先执行，默认 0）
node.process_physics_priority  # _physics_process() 的执行优先级

# 进程开关（性能优化关键！）
node.process_mode     # 决定节点何时处理。可选值：
                       #   PROCESS_MODE_INHERIT     —— 继承父节点（默认）
                       #   PROCESS_MODE_PAUSABLE    —— 永远处理，即使游戏暂停
                       #   PROCESS_MODE_WHEN_PAUSED —— 只在游戏暂停时处理
                       #   PROCESS_MODE_ALWAYS      —— 永远处理
                       #   PROCESS_MODE_DISABLED    —— 永远不处理

# 编辑器描述（在编辑器中作为注释显示）
node.editor_description   # 给节点写一段注释，在编辑器中可见
```

### 1.2 核心方法

```gdscript
# ===== 生命周期方法（你覆写这些）=====
func _init() -> void:
    # 对象构造时调用。此时节点还没进入场景树，不能访问其他节点
    pass

func _enter_tree() -> void:
    # 节点进入场景树时调用。子节点可能还没准备好
    pass

func _ready() -> void:
    # 节点及其所有子节点都准备好时调用。初始化逻辑放这里
    pass

func _process(delta: float) -> void:
    # 每帧调用。delta = 上一帧到当前帧的时间（秒），帧率不固定
    # 适合：游戏逻辑、输入检测、动画更新
    pass

func _physics_process(delta: float) -> void:
    # 每个物理帧调用。delta 固定（默认 1/60 秒）
    # 适合：物理相关代码
    pass

func _exit_tree() -> void:
    # 节点从场景树中移除时调用。清理资源、断开信号的好时机
    pass

func _input(event: InputEvent) -> void:
    # 接收到输入事件时调用。在 _process 之前调用
    pass

func _unhandled_input(event: InputEvent) -> void:
    # 输入事件没有被 GUI 或 _input 消费时调用
    # 适合：快捷键、全局操作
    pass

# ===== 场景树操作 =====
node.add_child(new_child, force_readable_name: bool = false, internal: InternalMode = 0)
# 添加子节点。force_readable_name 强制使用可读名称

node.remove_child(child_node)
# 移除子节点（不销毁，只是断开关系）

node.get_child(index: int, include_internal: bool = false) -> Node
# 按索引获取子节点。内部节点默认不返回

node.get_child_count(include_internal: bool = false) -> int
# 获取子节点数量

node.get_children(include_internal: bool = false) -> Array[Node]
# 获取所有子节点数组

node.get_parent() -> Node
# 获取父节点

node.get_node(path: NodePath) -> Node
# 通过路径获取节点。$ 语法糖等价于 get_node()

node.get_tree() -> SceneTree
# 获取场景树对象

node.get_window() -> Window
# 获取当前所在的窗口

# ===== 节点操作 =====
node.queue_free()
# 安全地标记节点为销毁。在当前帧结束后统一清理
# 注意：queue_free() 之后不要再使用该节点！

node.free()
# 立即销毁节点（危险！可能导致正在执行的代码崩溃）
# 绝大多数情况用 queue_free()

node.reparent(new_parent: Node, keep_global_transform: bool = true)
# 转移节点的父节点。keep_global_transform 保持世界位置不变

node.duplicate(flags: int = 15) -> Node
# 复制节点（深拷贝）。flags 控制复制什么（信号、分组、脚本等）

node.is_inside_tree() -> bool
# 检查节点是否在场景树中

node.is_ancestor_of(node: Node) -> bool
# 检查当前节点是否是目标节点的祖先

# ===== 分组管理 =====
node.add_to_group("enemies")
node.remove_from_group("enemies")
node.is_in_group("enemies") -> bool

# ===== 定时器快捷方法 =====
node.create_timer(time_sec: float, process_always: bool = true, ...) -> SceneTreeTimer
# 创建一个定时器，通常配合 await 使用

# ===== Tween =====
node.create_tween() -> Tween
# 创建并返回一个 Tween 对象

# ===== 过程开关（手动控制 _process / _physics_process）=====
node.set_process(enable: bool)
# 切换 _process(delta) 是否被调用

node.set_physics_process(enable: bool)
# 切换 _physics_process(delta) 是否被调用

node.set_process_input(enable: bool)
# 切换 _input(event) 是否被调用
```

### 1.3 核心信号

```gdscript
tree_entered          # 节点进入场景树时发射
tree_exited           # 节点退出场景树时发射
ready                 # 节点准备完成（_ready 被调用后）发射
renamed               # 节点被重命名时发射
child_entered_tree(child_node: Node)   # 子节点进入场景树
child_exiting_tree(child_node: Node)   # 子节点即将退出场景树
```

---

## 二、Node2D——2D 世界的基石

所有 2D 游戏对象都继承自 `Node2D`。它定义了 2D 空间中的位置、旋转和缩放。

### 2.1 核心属性

```gdscript
# 变换三要素
node_2d.position          # Vector2 —— 位置（相对于父节点）
node_2d.rotation          # float   —— 旋转角度（弧度）← 注意是弧度不是度！
node_2d.scale             # Vector2 —— 缩放（1.0 是原始大小）

# 全局变换（只读，考虑所有父节点的变换叠加）
node_2d.global_position   # Vector2 —— 在世界空间中的位置
node_2d.global_rotation   # float   —— 在世界空间中的旋转
node_2d.global_scale      # Vector2 —— 在世界空间中的缩放

# 变换矩阵（底层表示）
node_2d.transform         # Transform2D —— 局部变换矩阵
node_2d.global_transform  # Transform2D —— 全局变换矩阵

# 可见性
node_2d.visible           # bool —— 设为 false 隐藏节点（不渲染，但仍处理逻辑）
node_2d.z_index           # int  —— 渲染顺序（越大越在前面，类似 CSS z-index）
node_2d.z_as_relative     # bool —— z_index 是否相对于父节点

# 其他
node_2d.top_level         # bool —— 设为 true 使节点脱离父变换，直接用全局坐标
```

### 2.2 核心方法

```gdscript
# ===== 坐标变换 =====
node_2d.to_global(local_point: Vector2) -> Vector2
# 将局部坐标转换为全局坐标

node_2d.to_local(global_point: Vector2) -> Vector2
# 将全局坐标转换为局部坐标

# ===== 旋转相关（注意：都是弧度！）=====
node_2d.rotate(angle: float)  # 在当前旋转基础上再旋转 angle 弧度

# 角度转换
var rad := deg_to_rad(90.0)   # 度 → 弧度
var deg := rad_to_deg(PI)     # 弧度 → 度

# ===== 移动相关 =====
node_2d.translate(offset: Vector2)
# 在当前基础上平移

node_2d.look_at(point: Vector2)
# 让节点朝向某个点（适用于 Sprite2D 等有朝向需求的节点）

# ===== 获取屏幕尺寸 =====
var viewport_size := get_viewport_rect().size
var viewport_center := viewport_size / 2.0
```

### 2.3 常用技巧

```gdscript
# 让一个节点始终朝向鼠标
func _process(_delta: float) -> void:
    look_at(get_global_mouse_position())

# 让一个节点移动到父节点的指定位置
func move_to(x: float, y: float) -> void:
    position = Vector2(x, y)

# 平滑移动
func smooth_move_to(target: Vector2, speed: float) -> void:
    position = position.move_toward(target, speed * get_process_delta_time())

# 注意：改变 rotation 是绕原点旋转的
# 如果要让精灵绕自身中心旋转，确保精灵的 offset 正确
@onready var sprite: Sprite2D = $Sprite2D
sprite.offset = Vector2(0, 0)  # 默认 offset 可能让精灵偏离中心
```

---

## 三、Sprite2D——显示一张图片

### 3.1 核心属性

```gdscript
sprite.texture            # Texture2D —— 要显示的贴图
sprite.offset             # Vector2 —— 贴图的偏移（改变旋转中心、绘制位置）
sprite.centered           # bool —— 是否居中显示（设为 true 让贴图中心在节点位置）
sprite.flip_h             # bool —— 水平翻转
sprite.flip_v             # bool —— 垂直翻转
sprite.region_enabled     # bool —— 是否启用区域裁剪（只显示贴图的一部分）
sprite.region_rect        # Rect2 —— 裁剪区域（在贴图中的坐标和大小）
sprite.modulate           # Color —— 颜色调制（默认白色 = 原图，半透明 = 降低 alpha）
sprite.self_modulate      # Color —— 自身颜色调制（不影响子节点）

# 帧坐标（用于精灵表 / spritesheet）
sprite.frame              # int —— 当前帧索引
sprite.frame_coords       # Vector2i —— 帧在网格中的坐标
sprite.hframes            # int —— 水平帧数（精灵表中有几列）
sprite.vframes            # int —— 垂直帧数（精灵表中有几行）
```

### 3.2 核心方法

```gdscript
# 动态加载贴图
func load_texture() -> void:
    $Sprite2D.texture = load("res://assets/player.png") as Texture2D

# 颜色调制（制作受伤闪红效果）
func flash_red() -> void:
    $Sprite2D.modulate = Color.RED
    await get_tree().create_timer(0.1).timeout
    $Sprite2D.modulate = Color.WHITE

# 区域裁剪（从大贴图中裁出一部分显示）
func setup_region() -> void:
    $Sprite2D.region_enabled = true
    $Sprite2D.region_rect = Rect2(0, 0, 32, 32)  # (x, y, width, height)

# 精灵表帧切换
func setup_spritesheet() -> void:
    $Sprite2D.hframes = 8    # 8 列
    $Sprite2D.vframes = 2    # 2 行
    $Sprite2D.frame = 3      # 显示第 4 帧（从 0 开始索引）
    # frame = y * hframes + x
```

---

## 四、AnimatedSprite2D——精灵帧动画

### 4.1 核心属性

```gdscript
animated.sprite_frames  # SpriteFrames 资源 —— 动画帧数据
animated.animation      # String —— 当前正在播放的动画名称
animated.frame          # int —— 当前帧索引
animated.speed_scale    # float —— 播放速度倍率（1.0 = 正常速度）
animated.playing        # bool —— 是否正在播放（只读）
```

### 4.2 核心方法

```gdscript
# 播放动画
animated.play("walk")
animated.play("idle")
animated.play("attack")

# 带参数的播放
animated.play("walk", custom_speed: 2.0, from_end: false)
# custom_speed: 自定义速度倍率
# from_end: true = 从最后一帧倒着播

# 控制播放
animated.stop()            # 停止播放
animated.pause()           # 暂停
animated.play_backwards()  # 倒放

# 设置动画
animated.set_animation("walk")  # 切换动画但不自动播放
animated.set_frame(3)           # 跳到指定帧

# 获取信息
var has_anim := animated.has_animation("walk")  # 检查是否有这个动画
var total_frames := animated.sprite_frames.get_frame_count("walk")

# 在编辑器中创建 SpriteFrames 资源：
# 选择 AnimatedSprite2D → 在底部 Animation 面板 → 新建动画 → 添加帧图片
```

### 4.3 信号

```gdscript
animation_finished   # 动画播放完毕时发射
frame_changed        # 帧切换时发射
animation_looped     # 动画循环一次时发射（循环动画在每次循环结束时触发）
```

### 4.4 使用示例

```gdscript
extends CharacterBody2D

@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D

func _physics_process(_delta: float) -> void:
    if velocity.x != 0:
        animated_sprite.play("walk")
        animated_sprite.flip_h = velocity.x < 0  # 向左走时翻转
    else:
        animated_sprite.play("idle")

# 播放一次性动画（如攻击），播完后回到 idle
func attack() -> void:
    animated_sprite.play("attack")
    await animated_sprite.animation_finished
    animated_sprite.play("idle")
```

---

## 五、CollisionShape2D / CollisionPolygon2D——碰撞形状

这两个节点本身不产生碰撞，它们必须作为物理节点（`CharacterBody2D`、`RigidBody2D`、`StaticBody2D`、`Area2D`）的子节点来定义碰撞区域。

### 5.1 核心属性

```gdscript
collision.shape         # Shape2D —— 碰撞形状资源
collision.disabled      # bool —— 是否禁用此碰撞体
collision.one_way_collision  # bool —— 单向碰撞（只从特定方向碰撞，适合平台）
collision.one_way_collision_margin  # float —— 单向碰撞的容差
```

### 5.2 Shape2D 的子类型

```gdscript
# CircleShape2D —— 圆形碰撞
var circle := CircleShape2D.new()
circle.radius = 30.0
$CollisionShape2D.shape = circle

# RectangleShape2D —— 矩形碰撞
var rect := RectangleShape2D.new()
rect.size = Vector2(64, 64)
$CollisionShape2D.shape = rect

# CapsuleShape2D —— 胶囊形碰撞（圆角矩形）
var capsule := CapsuleShape2D.new()
capsule.radius = 20.0
capsule.height = 60.0
$CollisionShape2D.shape = capsule

# WorldBoundaryShape2D —— 无限长的直线边界（用于地板/天花板）
var boundary := WorldBoundaryShape2D.new()
boundary.normal = Vector2.UP    # 法线朝上 = 地板
boundary.distance = 500.0       # 距离原点的距离

# SegmentShape2D —— 线段碰撞
var segment := SegmentShape2D.new()
segment.a = Vector2(0, 0)
segment.b = Vector2(100, 0)

# ConcavePolygonShape2D —— 凹多边形碰撞（性能开销大，尽量用凸多边形组合替代）
```

### 5.3 CollisionPolygon2D

```gdscript
# 使用多边形定义碰撞（适合非矩形物体）
collision_polygon.polygon = PackedVector2Array([
    Vector2(0, -30),
    Vector2(25, 15),
    Vector2(-25, 15)
])
# Godot 会自动将凹多边形分解为多个凸多边形
```

### 5.4 代码中动态创建碰撞体

```gdscript
func create_collision() -> void:
    var shape := CollisionShape2D.new()
    var circle := CircleShape2D.new()
    circle.radius = 32.0
    shape.shape = circle
    add_child(shape)
```

---

## 六、CharacterBody2D——你代码控制的角色

这是 2D 游戏中使用最多的物理节点——人物的移动由你的代码完全控制，但仍能检测碰撞、沿墙滑行、站在地板上。

### 6.1 核心属性

```gdscript
character.velocity                # Vector2 —— 当前速度（你设置，move_and_slide 读取）
character.motion_mode             # 运动模式：
                                   #   MOTION_MODE_GROUNDED  —— 地面模式（默认，有重力）
                                   #   MOTION_MODE_FLOATING   —— 漂浮模式（无重力，太空/水中）

# 地板/天花板/墙壁检测结果（move_and_slide 调用后更新）
character.is_on_floor()           # bool —— 是否站在地板上
character.is_on_ceiling()         # bool —— 是否碰到天花板
character.is_on_wall()            # bool —— 是否碰到墙壁
character.is_on_wall_only()       # bool —— 是否只碰到了墙壁（没碰到地板）

# 地面和墙壁设置
character.floor_stop_on_slope     # bool —— 在斜坡上是否停止下滑（默认 true）
character.floor_snap_length       # float —— 地板吸附距离（下坡时贴在坡面上，默认 1）
character.floor_max_angle         # float —— 能站的最大地面角度（弧度，默认 45°）
character.wall_min_slide_angle    # float —— 沿墙滑行的最小角度（弧度）

# 碰撞响应
character.up_direction            # Vector2 —— 向上方向（默认 Vector2.UP = (0, -1)）
character.safe_margin             # float —— 安全边距（默认 0.08，太小可能穿墙）

# 平台下落
character.platform_on_leave       # 离开平台时的行为
character.platform_floor_layers   # 哪些层被视为"地板"平台
character.platform_wall_layers    # 哪些层被视为"墙壁"
```

### 6.2 核心方法

```gdscript
# ===== 最重要的方法：move_and_slide() =====
character.move_and_slide()
# 根据 velocity 移动角色，处理碰撞，更新 is_on_floor() 等状态
# 必须在 _physics_process() 中调用，不要在 _process() 中调用

# ===== 获取地板/墙壁/天花板的碰撞法线 =====
character.get_floor_normal()     # 地板的法线方向
character.get_wall_normal()      # 墙壁的法线方向
character.get_ceiling_normal()   # 天花板的法线方向

# ===== 获取实际的移动距离 =====
character.get_last_motion()      # 上一次 move_and_slide() 实际移动的距离向量
character.get_position_delta()   # 与上一帧的位置差值

# ===== 获取碰撞信息 =====
character.get_last_slide_collision()  # 最后一次滑动碰撞的详细信息
var count := character.get_slide_collision_count()  # 本帧碰撞次数
var collision := character.get_slide_collision(index)  # 第 index 次碰撞
# 返回 KinematicCollision2D，包含：
#   .get_collider()         —— 碰到的物体
#   .get_position()         —— 碰撞位置
#   .get_normal()           —— 碰撞法线
#   .get_travel()           —— 碰撞前的移动距离
#   .get_remainder()        —— 碰撞后剩余的移动距离
#   .get_angle()            —— 碰撞角度

# ===== 测试移动（不实际移动，只返回碰撞结果）=====
character.test_move(from: Transform2D, motion: Vector2, collision: KinematicCollision2D = null) -> bool
```

### 6.3 完整使用模板

```gdscript
extends CharacterBody2D

@export var speed: float = 300.0
@export var jump_velocity: float = -400.0
@export var acceleration: float = 1500.0
@export var friction: float = 1000.0

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")

func _physics_process(delta: float) -> void:
    # 1. 施加重力
    if not is_on_floor():
        velocity.y += gravity * delta

    # 2. 处理跳跃
    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    # 3. 处理水平移动（带加速度和摩擦力）
    var direction := Input.get_axis("move_left", "move_right")

    if direction != 0:
        velocity.x = move_toward(velocity.x, direction * speed, acceleration * delta)
    else:
        velocity.x = move_toward(velocity.x, 0, friction * delta)

    # 4. 执行移动
    move_and_slide()

    # 5. 处理碰撞（可选）
    for i in get_slide_collision_count():
        var collision := get_slide_collision(i)
        var collider := collision.get_collider()
        # 检查是否推到了 RigidBody2D
        if collider is RigidBody2D:
            collider.apply_central_impulse(-collision.get_normal() * push_force)
```

---

## 七、RigidBody2D——物理模拟的刚体

受重力影响、能被推动、会自然旋转——完全交给物理引擎管理。

### 7.1 核心属性

```gdscript
rigid.mass                   # float —— 质量（影响碰撞时的动量传递）
rigid.inertia                # float —— 转动惯量（影响旋转惯性，0 表示不旋转）
rigid.gravity_scale          # float —— 重力倍率（1.0 = 正常重力，0 = 无重力）
rigid.linear_velocity        # Vector2 —— 线速度
rigid.angular_velocity       # float —— 角速度（弧度/秒）

# 模式
rigid.freeze_mode            # 冻结模式（对象停止移动后自动冻结以节省性能）
rigid.freeze                 # bool —— 冻结刚体（不计算物理）
rigid.freeze_enabled         # bool —— 是否启用冻结模式
rigid.sleeping               # bool —— 刚体是否处于休眠状态（只读，一段时间不用力后自动休眠）

# 物理行为
rigid.linear_damp            # float —— 线性阻尼（模拟空气阻力，默认 0）
rigid.angular_damp           # float —— 角速度阻尼
rigid.can_sleep              # bool —— 是否允许休眠（默认 true）
rigid.lock_rotation          # bool —— 禁止旋转
rigid.continuous_cd          # 连续碰撞检测模式（高速物体防穿透）：
                              #   CCD_MODE_DISABLED       —— 禁用（默认）
                              #   CCD_MODE_CAST_RAY       —— 射线检测
                              #   CCD_MODE_CAST_SHAPE     —— 形状扫描（最精确，开销最大）

# 自定义积分器
rigid.custom_integrator      # bool —— 是否使用自定义物理积分（进阶用法）

# 接触监测
rigid.contact_monitor        # bool —— 是否监控接触点
rigid.max_contacts_reported  # int —— 最多报告多少个接触点
```

### 7.2 核心方法

```gdscript
# ===== 施加力 =====
rigid.apply_force(force: Vector2, position: Vector2 = Vector2.ZERO)
# 在指定位置施加力（持续力，每物理帧都要调用）

rigid.apply_central_force(force: Vector2)
# 在刚体中心施加力（等同于 apply_force(force, Vector2.ZERO)）

rigid.apply_impulse(impulse: Vector2, position: Vector2 = Vector2.ZERO)
# 施加瞬时冲量（打一拳、爆炸冲击）

rigid.apply_central_impulse(impulse: Vector2)
# 在中心施加瞬时冲量

rigid.apply_torque(torque: float)
# 施加扭矩（旋转力）

rigid.apply_torque_impulse(torque: float)
# 施加瞬时扭矩冲量

# ===== 速度控制 =====
rigid.set_linear_velocity(velocity: Vector2)   # 直接设置线速度
rigid.set_angular_velocity(velocity: float)     # 直接设置角速度

# ===== 状态控制 =====
rigid.set_axis_velocity(axis_velocity: Vector2)
# 设置某一轴上的速度分量

rigid.set_freeze_enabled(enabled: bool)
# 启用/禁用冻结模式

# ===== 获取碰撞信息 =====
var contacts := rigid.get_contact_count()
var contact_position := rigid.get_contact_local_position(index)
var contact_normal := rigid.get_contact_local_normal(index)
var contact_velocity := rigid.get_contact_local_velocity_at_position(index)
var contact_collider := rigid.get_contact_collider_object(index: int)
```

### 7.3 信号

```gdscript
body_entered(body: Node)   # 有物体进入此刚体
body_exited(body: Node)    # 有物体离开此刚体
body_shape_entered(body_rid: RID, body: Node, body_shape: int, local_shape: int)
body_shape_exited(body_rid: RID, body: Node, body_shape: int, local_shape: int)
sleeping_state_changed()   # 休眠状态改变
```

### 7.4 使用示例

```gdscript
# 一个可以被推动的木箱
extends RigidBody2D

@export var push_force: float = 80.0

func _integrate_forces(state: PhysicsDirectBodyState2D) -> void:
    # _integrate_forces 在物理步进之前调用，可以在这里精确控制物理
    # state 提供了比属性和方法更底层的访问
    pass

# 击飞物体
func knock_back(direction: Vector2, strength: float) -> void:
    apply_central_impulse(direction * strength)

# 让刚体朝某个方向匀速移动（不受重力影响时）
func move_constant(velocity: Vector2) -> void:
    gravity_scale = 0.0
    linear_damp = 0.0
    set_linear_velocity(velocity)
```

---

## 八、StaticBody2D——不动的障碍物

墙壁、地板、平台——完全不动的物理物体。

### 8.1 核心属性

```gdscript
static_body.constant_linear_velocity   # Vector2 —— 恒定线速度（用于移动平台）
static_body.constant_angular_velocity  # float —— 恒定角速度
static_body.physics_material_override  # PhysicsMaterial —— 物理材质覆盖
```

### 8.2 使用要点

```gdscript
# StaticBody2D 本身很简单——它不移动。但可以通过代码移动它：
# 适用场景：移动平台、升降梯

extends StaticBody2D

func _physics_process(delta: float) -> void:
    # 移动平台
    constant_linear_velocity = Vector2(100.0, 0.0)
    # 站在上面的 CharacterBody2D 会自动跟着移动
```

---

## 九、Area2D——检测区域

不产生物理碰撞，但能在物体进入/离开时通知你。用途极广：拾取道具、攻击判定、视野范围、传送门、伤害区域等。

### 9.1 核心属性

```gdscript
area.monitoring           # bool —— 是否检测其他物体进入/离开（默认 true）
area.monitorable          # bool —— 是否可被其他 Area2D 检测到（默认 true）
area.priority             # int —— 多个重叠 Area 的优先级（用于事件分发）
area.space_override       # 空间状态覆盖模式
area.gravity_space_override  # 重力覆盖模式
area.gravity_point        # bool —— 重力是点重力还是方向重力
area.gravity_direction    # Vector2 —— 重力方向
area.gravity              # float —— 重力大小
area.linear_damp_space_override  # 线性阻尼覆盖
area.linear_damp          # float —— 线性阻尼
area.angular_damp_space_override # 角速度阻尼覆盖
area.angular_damp         # float —— 角速度阻尼
area.angular_damp         # float —— 角速度阻尼

# 碰撞层和掩码（与物理节点一样）
area.collision_layer      # int —— 我属于哪些层
area.collision_mask       # int —— 我检测哪些层
```

### 9.2 核心方法

```gdscript
# 获取重叠的物体
var bodies := area.get_overlapping_bodies()   # 所有物理身体
var areas := area.get_overlapping_areas()     # 所有检测区域
var has_body := area.has_overlapping_bodies() # 是否有重叠的物理身体
var has_area := area.has_overlapping_areas()  # 是否有重叠的检测区域
```

### 9.3 信号

```gdscript
body_entered(body: Node2D)        # 物理身体进入
body_exited(body: Node2D)         # 物理身体离开
area_entered(area: Area2D)        # 另一个 Area2D 进入
area_exited(area: Area2D)         # 另一个 Area2D 离开
body_shape_entered(body_rid: RID, body: Node2D, body_shape_index: int, local_shape_index: int)
body_shape_exited(body_rid: RID, body: Node2D, body_shape_index: int, local_shape_index: int)
area_shape_entered(area_rid: RID, area: Area2D, area_shape_index: int, local_shape_index: int)
area_shape_exited(area_rid: RID, area: Area2D, area_shape_index: int, local_shape_index: int)
```

### 9.4 使用示例

```gdscript
# 金币拾取区域
extends Area2D

func _ready() -> void:
    body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
    if body is Player:
        collect()

func collect() -> void:
    # 播放拾取动画
    var tween := create_tween()
    tween.tween_property(self, "scale", Vector2(1.5, 1.5), 0.1)
    tween.tween_property(self, "scale", Vector2(0.0, 0.0), 0.2)
    tween.tween_callback(queue_free)

    # 通知全局
    SignalBus.coin_collected.emit(1)

# 伤害区域（火焰、尖刺等）
extends Area2D

@export var damage: int = 10
@export var damage_interval: float = 0.5

var _bodies_in_area: Array[Node2D] = []

func _ready() -> void:
    body_entered.connect(func(b): _bodies_in_area.append(b))
    body_exited.connect(func(b): _bodies_in_area.erase(b))
    # 定时伤害
    var timer := Timer.new()
    timer.wait_time = damage_interval
    timer.timeout.connect(_deal_damage)
    add_child(timer)
    timer.start()

func _deal_damage() -> void:
    for body in _bodies_in_area:
        if body.has_method("take_damage"):
            body.take_damage(damage)
```

---

## 十、RayCast2D——射线检测

沿一条直线检测是否碰到了东西。比 Area2D 更轻量，适合检测"面前是什么"、"脚下有没有地面"。

### 10.1 核心属性

```gdscript
ray.target_position        # Vector2 —— 射线终点（相对于节点位置）
ray.enabled                # bool —— 是否启用检测
ray.exclude_parent         # bool —— 是否排除父节点（默认 true）
ray.collision_mask         # int —— 只检测这些层的物体
ray.hit_from_inside        # bool —— 当射线在碰撞体内部时是否也检测（默认 false）

# 碰撞结果（每次物理帧更新）
ray.is_colliding()         # bool —— 是否碰到了东西
ray.get_collision_point()  # Vector2 —— 碰撞点的全局坐标
ray.get_collision_normal() # Vector2 —— 碰撞面的法线
ray.get_collider()         # Object —— 碰到的物体
```

### 10.2 核心方法

```gdscript
# 强制更新（在 _process 中手动触发检测）
ray.force_raycast_update()

# 获取碰撞物体的详细信息
ray.get_collider_shape()   # 碰到的碰撞体形状索引
ray.get_collider_rid()     # 碰到的碰撞体 RID
```

### 10.3 使用示例

```gdscript
# 地面检测（比 CharacterBody2D.is_on_floor() 更灵活）
extends CharacterBody2D

@onready var ground_ray: RayCast2D = $GroundRay

func is_grounded() -> bool:
    return ground_ray.is_colliding()

# 悬崖检测（防止 AI 走出平台边缘）
@onready var cliff_ray: RayCast2D = $CliffRay

func has_cliff_ahead() -> bool:
    return not cliff_ray.is_colliding()

# 检测前方墙壁
@onready var wall_ray: RayCast2D = $WallRay

func is_wall_ahead() -> bool:
    return wall_ray.is_colliding()
```

---

## 十一、Timer——计时器

### 11.1 核心属性

```gdscript
timer.wait_time          # float —— 等待时间（秒）
timer.one_shot           # bool —— 是否只触发一次（false = 循环触发）
timer.autostart          # bool —— 进入场景树时自动开始
timer.time_left          # float —— 剩余时间（只读）
timer.paused             # bool —— 是否暂停计时
```

### 11.2 核心方法

```gdscript
timer.start(time_sec: float = -1)
# 开始计时。如果传入 time_sec，会覆盖 wait_time

timer.stop()
# 停止计时（不重置 time_left）

timer.is_stopped() -> bool
# 是否已停止
```

### 11.3 信号

```gdscript
timeout   # 计时时间到达时发射
```

### 11.4 使用示例

```gdscript
# 一次性延迟
func delayed_action() -> void:
    var timer := Timer.new()
    timer.wait_time = 2.0
    timer.one_shot = true
    timer.timeout.connect(_do_something)
    add_child(timer)
    timer.start()

# 循环执行
func _ready() -> void:
    $EnemySpawnTimer.wait_time = 3.0
    $EnemySpawnTimer.timeout.connect(_spawn_enemy)
    $EnemySpawnTimer.start()

# await 方式（无需 Timer 节点）
func wait_and_do() -> void:
    await get_tree().create_timer(1.5).timeout
    print("1.5 秒后执行")
```

---

## 十二、Camera2D——2D 相机

### 12.1 核心属性

```gdscript
camera.zoom                   # Vector2 —— 缩放（1,1 是默认，2,2 放大两倍）
camera.offset                 # Vector2 —— 偏移量（相机位置 = 节点位置 + offset）
camera.anchor_mode            # 锚点模式：
                               #   ANCHOR_MODE_FIXED_TOP_LEFT  —— 固定左上角
                               #   ANCHOR_MODE_DRAG_CENTER     —— 拖动中心（默认）
camera.limit_left             # int —— 相机左边界
camera.limit_right            # int —— 相机右边界
camera.limit_top              # int —— 相机上边界
camera.limit_bottom           # int —— 相机下边界

# 平滑跟随（不用写代码的相机平滑！）
camera.position_smoothing_enabled    # bool —— 启用位置平滑
camera.position_smoothing_speed      # float —— 平滑速度（像素/秒，默认 5）

# 拖拽边距（角色走到屏幕边缘一定范围时相机才开始跟随）
camera.drag_left_margin       # float —— 左拖拽边距（从左边比例 0.0-1.0）
camera.drag_right_margin      # float —— 右拖拽边距
camera.drag_top_margin        # float —— 上拖拽边距
camera.drag_bottom_margin     # float —— 下拖拽边距
camera.drag_horizontal_enabled  # bool —— 启用水平拖拽
camera.drag_vertical_enabled    # bool —— 启用垂直拖拽

# 其他
camera.enabled                # bool —— 相机是否启用（设为当前相机）
camera.ignore_rotation        # bool —— 忽略旋转（默认 true）
camera.rotation_smoothing_enabled  # bool —— 启用旋转平滑
camera.rotation_smoothing_speed    # float —— 旋转平滑速度
```

### 12.2 核心方法

```gdscript
camera.make_current()
# 将此相机设为当前活跃相机

camera.is_current() -> bool
# 检查是否是当前活跃相机

camera.align()
# 强制相机立即对齐到目标位置（一次性，绕过平滑）

camera.get_screen_center_position() -> Vector2
# 获取屏幕中心的世界坐标

camera.get_camera_screen_center() -> Vector2
# 获取相机在屏幕上的中心位置

camera.reset_smoothing()
# 重置平滑（立即跳到目标位置）

# 屏幕坐标 ↔ 世界坐标转换
camera.get_camera_rect() -> Rect2
# 获取相机能看到的世界矩形区域
```

### 12.3 使用示例

```gdscript
# 最简单的跟随：把 Camera2D 作为 Player 的子节点
# 不需要写任何代码，调整 drag_margin 即可

# 平滑跟随 + 限制范围
extends Camera2D

func _ready() -> void:
    position_smoothing_enabled = true
    position_smoothing_speed = 8.0

    # 设置相机边界（不让相机看到关卡外面的区域）
    limit_left = 0
    limit_right = 1920
    limit_top = 0
    limit_bottom = 1080

# 震屏效果
func shake(intensity: float, duration: float) -> void:
    var original_offset := offset
    var elapsed := 0.0

    while elapsed < duration:
        offset = original_offset + Vector2(
            randf_range(-intensity, intensity),
            randf_range(-intensity, intensity)
        )
        intensity *= 0.9  # 震动逐渐减弱
        elapsed += get_process_delta_time()
        await get_tree().process_frame

    offset = original_offset
```

---

## 十三、AudioStreamPlayer / AudioStreamPlayer2D——音频

### 13.1 AudioStreamPlayer（全局音频）

适合：背景音乐、UI 音效（不受空间位置影响）

```gdscript
audio.stream                # AudioStream —— 音频流资源
audio.volume_db             # float —— 音量（分贝，0 是原始音量，负数降低，正数增大）
audio.pitch_scale           # float —— 音高倍率（1.0 原始，2.0 高八度）
audio.playing               # bool —— 是否正在播放（只读）
audio.autoplay              # bool —— 进入场景树时自动播放
audio.bus                   # String —— 音频总线名称（默认 "Master"）
audio.max_polyphony         # int —— 最大同时播放数（默认 1，多个声音会互相打断）
```

```gdscript
# 核心方法
audio.play(from_position: float = 0.0)
# 开始播放。from_position 指定从第几秒开始

audio.stop()
# 停止播放（重置播放位置）

audio.seek(to_position: float)
# 跳转到指定播放位置

audio.get_playback_position() -> float
# 获取当前播放位置（秒）

audio.stream_paused         # bool —— 暂停/恢复。设置 true 暂停
```

```gdscript
# 信号
finished   # 音频播放完毕时发射
```

### 13.2 AudioStreamPlayer2D（空间化音频）

继承自 `Node2D`，音量和左右声道会根据听者位置自动调整：

```gdscript
audio_2d.max_distance      # float —— 最大听音距离（超过此距离声音听不到）
audio_2d.attenuation       # float —— 衰减系数
# 衰减模型：声音在 max_distance 内逐渐变小
```

---

## 十四、AnimationPlayer——动画播放器

### 14.1 核心属性

```gdscript
anim_player.current_animation         # String —— 当前动画名称
anim_player.current_animation_position  # float —— 当前播放位置（秒）
anim_player.current_animation_length    # float —— 当前动画总长度（秒）
anim_player.speed_scale               # float —— 播放速度倍率
anim_player.assigned_animation        # String —— 使用 AnimationTree 时指定动画名
anim_player.autoplay                  # String —— 进入场景时自动播放的动画名
anim_player.root_node                 # NodePath —— 动画根节点（默认是 AnimationPlayer 的父节点）
anim_player.playback_active           # bool —— 是否正在播放（只读）
anim_player.playback_default_blend_time  # float —— 默认混合时间
```

### 14.2 核心方法

```gdscript
# 播放控制
anim_player.play(name: String, custom_blend: float = -1, custom_speed: float = 1.0, from_end: bool = false)
# 播放指定动画

anim_player.stop(keep_state: bool = false)
# 停止播放。keep_state 为 true 时保持停止时的状态（不重置）

anim_player.pause()
# 暂停播放

anim_player.play_backwards(name: String, custom_blend: float = -1)
# 倒放动画

anim_player.queue(name: String)
# 队列播放（当前动画播完后自动播下一个）

anim_player.seek(seconds: float, update: bool = false)
# 跳转到指定位置。update 为 true 时更新动画状态

# 动画编辑
anim_player.get_animation(name: String) -> Animation
# 获取指定动画对象（可以修改其属性）

anim_player.rename_animation(old_name: String, new_name: String)
anim_player.remove_animation(name: String)
anim_player.has_animation(name: String) -> bool
anim_player.get_animation_list() -> PackedStringArray

# 混合
anim_player.set_blend_time(animation_from: String, animation_to: String, time: float)
anim_player.get_blend_time(animation_from: String, animation_to: String) -> float

# 方法调用轨道（在动画中调用代码）
anim_player.play("attack")
# 在动画编辑器中可以添加 "Call Method" 轨道
# 在特定帧自动调用节点的指定方法
```

### 14.3 信号

```gdscript
animation_started(anim_name: String)
animation_finished(anim_name: String)
animation_changed(old_name: String, new_name: String)
animation_list_changed()
caches_cleared()
```

### 14.4 AnimationTree 相关

```gdscript
# AnimationTree 是 AnimationPlayer 的升级版
# 使用 AnimationNodeStateMachine 管理复杂的状态切换
# 这里展示代码层面如何配合使用

@onready var anim_tree: AnimationTree = $AnimationTree
@onready var state_machine: AnimationNodeStateMachinePlayback = anim_tree["parameters/playback"]

func update_animation() -> void:
    if not is_on_floor():
        if velocity.y < 0:
            state_machine.travel("jump")
        else:
            state_machine.travel("fall")
    elif velocity.length() > 0.1:
        state_machine.travel("walk")
    else:
        state_machine.travel("idle")

# 混合树参数
anim_tree.set("parameters/Idle/blend_position", direction)
anim_tree.set("parameters/conditions/is_running", true)
```

---

## 十五、TileMap——瓦片地图

### 15.1 核心属性

```gdscript
tile_map.tile_set                      # TileSet —— 瓦片集资源
tile_map.rendering_quadrant_size       # int —— 渲染象限大小（默认 16）

# 图层相关
tile_map.get_layers_count() -> int     # 图层数量
tile_map.add_layer(index: int)         # 添加图层
tile_map.remove_layer(index: int)      # 移除图层
tile_map.set_layer_name(layer: int, name: String)
tile_map.get_layer_name(layer: int) -> String
tile_map.set_layer_enabled(layer: int, enabled: bool)
tile_map.is_layer_enabled(layer: int) -> bool
```

### 15.2 核心方法

```gdscript
# ===== 设置单元格 =====
tile_map.set_cell(layer: int, coords: Vector2i, source_id: int = -1,
                  atlas_coords: Vector2i = Vector2i(-1, -1),
                  alternative_tile: int = 0)
# 在指定位置设置瓦片
# source_id: 瓦片集中的源 ID（-1 表示清空该格）
# atlas_coords: 在图集中的坐标
# 简化版：
tile_map.set_cell(layer, Vector2i(3, 5), 0, Vector2i(1, 2))

# ===== 获取单元格 =====
tile_map.get_cell_source_id(layer: int, coords: Vector2i) -> int
# 获取指定位置的 source_id（-1 表示空格）

tile_map.get_cell_atlas_coords(layer: int, coords: Vector2i) -> Vector2i
# 获取图集坐标

tile_map.get_cell_alternative_tile(layer: int, coords: Vector2i) -> int

# ===== 批量操作 =====
tile_map.set_cells_terrain_connect(layer: int, cells: Array[Vector2i],
                                    terrain_set: int, terrain: int,
                                    ignore_empty_terrains: bool = true)
# 设置地形连接（自动拼接）

tile_map.set_cells_terrain_path(layer: int, path: Array[Vector2i],
                                 terrain_set: int, terrain: int,
                                 ignore_empty_terrains: bool = true)
# 沿路径设置地形

# ===== 坐标转换 =====
tile_map.local_to_map(local_position: Vector2) -> Vector2i
# 世界坐标 → 瓦片坐标

tile_map.map_to_local(map_position: Vector2i) -> Vector2
# 瓦片坐标 → 世界坐标（返回该瓦片中心的位置）

tile_map.get_cell_tile_data(layer: int, coords: Vector2i) -> TileData
# 获取指定瓦片的数据（自定义数据、碰撞形状等）

# ===== 常用砖块地图 =====
tile_map.get_used_rect() -> Rect2i
# 获取所有已使用瓦片的包围矩形

tile_map.get_used_cells(layer: int) -> Array[Vector2i]
# 获取该层所有已设置瓦片的坐标

tile_map.clear_layer(layer: int)
# 清空某一层
```

### 15.3 使用示例

```gdscript
# 生成随机地形
func generate_terrain() -> void:
    for x in range(50):
        for y in range(30):
            if y > 20:
                tile_map.set_cell(0, Vector2i(x, y), 0, Vector2i(0, 0))  # 地面
            elif y > 15:
                tile_map.set_cell(0, Vector2i(x, y), 0, Vector2i(1, 0))  # 泥土

# 点击地图获取瓦片位置
func _input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed:
        var map_coords := tile_map.local_to_map(get_global_mouse_position())
        var source_id := tile_map.get_cell_source_id(0, map_coords)
        if source_id != -1:
            print("点击的瓦片：", map_coords, " 来源：", source_id)
```

---

## 十六、Control——UI 控件基类

### 16.1 锚点和边距

这是理解 Godot UI 系统的关键：

```gdscript
# 锚点：相对于父容器比例，0.0-1.0
control.anchor_left     # 左锚点（默认 0）
control.anchor_top      # 上锚点（默认 0）
control.anchor_right    # 右锚点（默认 0）
control.anchor_bottom   # 下锚点（默认 0）

# 边距：相对于锚点的像素偏移
control.offset_left     # 左偏移
control.offset_top      # 上偏移
control.offset_right    # 右偏移
control.offset_bottom   # 下偏移

# 预设锚点（在代码中设置）
control.set_anchors_preset(Control.PRESET_FULL_RECT)  # 全屏拉伸
control.set_anchors_preset(Control.PRESET_CENTER)      # 居中
control.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)  # 底部居中宽条

# 位置和大小（自动根据锚点和边距计算）
control.position        # Vector2 —— 左上角位置
control.size            # Vector2 —— 大小
control.global_position # Vector2 —— 在屏幕上的绝对位置

# 最小尺寸约束
control.custom_minimum_size  # Vector2 —— 控件不能比这个更小
```

### 16.2 核心属性

```gdscript
control.mouse_filter     # 鼠标过滤模式：
                          #   MOUSE_FILTER_STOP    —— 接收鼠标事件并阻止传递
                          #   MOUSE_FILTER_PASS    —— 接收鼠标事件并允许传递给下方控件
                          #   MOUSE_FILTER_IGNORE  —— 完全忽略鼠标事件

control.mouse_default_cursor_shape  # 鼠标悬停时的光标形状
# Control.CURSOR_ARROW / CURSOR_IBEAM / CURSOR_POINTING_HAND / CURSOR_CROSS / ...

control.focus_mode       # 焦点模式：
                          #   FOCUS_NONE  —— 不可获取焦点
                          #   FOCUS_CLICK —— 点击获取焦点
                          #   FOCUS_ALL   —— 点击和 Tab 键获取焦点

control.theme            # Theme —— 自定义主题资源
control.tooltip_text     # String —— 鼠标悬停时显示的提示文字

control.size_flags_horizontal  # 水平拉伸标志（在容器中使用）
control.size_flags_vertical    # 垂直拉伸标志
# SIZE_SHRINK_BEGIN / SIZE_FILL / SIZE_EXPAND / SIZE_SHRINK_END / SIZE_SHRINK_CENTER
```

### 16.3 核心方法

```gdscript
# 获取矩形
control.get_rect() -> Rect2
# 返回控件的矩形区域（位置、大小）

# 设置位置和大小
control.set_position(pos: Vector2)
control.set_size(size: Vector2)

# 锚点批量设置
control.set_anchor(anchor: Side, anchor_value: float, keep_offset: bool = true, push_opposite_anchor: bool = true)
# 设置某一个锚点。Side: SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM

# 边距批量设置
control.set_offset(side: Side, offset: float)

# 强制重新排列（容器中）
control.reset_size()

# 抓取/释放焦点
control.grab_focus()
control.release_focus()
control.has_focus() -> bool

# 拖拽
control.set_drag_forwarding(drag_func: Callable, can_drop_func: Callable, drop_func: Callable)
# 设置拖拽行为的回调

# 强制刷新
control.queue_redraw()
# 请求重绘（在下一帧调用 _draw()）
```

### 16.4 信号

```gdscript
gui_input(event: InputEvent)     # GUI 输入事件
mouse_entered()                  # 鼠标进入
mouse_exited()                   # 鼠标离开
focus_entered()                 # 获得焦点
focus_exited()                  # 失去焦点
resized()                       # 大小改变
minimum_size_changed()          # 最小尺寸改变
```

---

## 十七、Label——文本标签

### 17.1 核心属性

```gdscript
label.text                    # String —— 显示的文本
label.label_settings          # LabelSettings —— 标签设置资源（统一管理字体、颜色等）
label.horizontal_alignment    # 水平对齐：HORIZONTAL_ALIGNMENT_LEFT/CENTER/RIGHT/FILL
label.vertical_alignment      # 垂直对齐：VERTICAL_ALIGNMENT_TOP/CENTER/BOTTOM/FILL
label.autowrap_mode           # 自动换行模式：
                               #   TextServer.AUTOWRAP_OFF    —— 不换行
                               #   TextServer.AUTOWRAP_ARBITER —— 在任意字符处换行
                               #   TextServer.AUTOWRAP_WORD    —— 在单词边界换行
                               #   TextServer.AUTOWRAP_WORD_SMART —— 智能单词换行
label.clip_text               # bool —— 文本超出时裁剪（加省略号）
label.text_overrun_behavior   # 溢出行为
label.uppercase               # bool —— 强制大写
label.visible_characters      # int —— 可见字符数（-1 显示全部，打字机效果）
label.visible_ratio           # float —— 可见比例（-1.0 显示全部）
label.lines_skipped           # int —— 跳过前 N 行
label.max_lines_visible       # int —— 最大可见行数（-1 不限制）
```

### 17.2 核心方法

```gdscript
label.get_total_character_count() -> int   # 总字符数
label.get_visible_line_count() -> int       # 可见行数
label.get_character_bounds(char_pos: int) -> Rect2  # 某个字符的包围矩形
```

### 17.3 使用示例

```gdscript
# 打字机效果
func typewriter_effect(full_text: String, duration: float) -> void:
    $Label.text = full_text
    $Label.visible_characters = 0

    var tween := create_tween()
    tween.tween_property($Label, "visible_characters",
        full_text.length(), duration).set_ease(Tween.EASE_IN_OUT)

# BBCode 富文本（Godot 支持 BBCode 标记）
func setup_rich_text() -> void:
    var label: Label = $Label
    label.text = "[center][color=red]警告！[/color][/center]\n[font_size=24]大标题[/font_size]"

# 动态更新分数
func update_score(new_score: int) -> void:
    $ScoreLabel.text = "分数：%d" % new_score

# 带格式的文本（数字颜色等）
func update_hp(current: int, max_hp: int) -> void:
    var color := "green" if current > max_hp * 0.5 else ("yellow" if current > max_hp * 0.25 else "red")
    $HPLabel.text = "[color=%s]%d[/color] / %d" % [color, current, max_hp]
```

---

## 十八、Button——按钮

### 18.1 核心属性

```gdscript
button.text                   # String —— 按钮文字
button.disabled               # bool —— 禁用按钮（灰色，不可点击）
button.toggle_mode            # bool —— 切换模式（按下保持按下状态，再按弹起）
button.button_pressed         # bool —— 按钮是否按下（toggle_mode 时有用）
button.button_mask            # 响应的鼠标按键
button.icon                   # Texture2D —— 按钮图标
button.icon_alignment         # 图标对齐方式
button.expand_icon            # bool —— 拉伸图标填满按钮
button.flat                   # bool —— 扁平样式（默认只显示文字不显示背景）
button.alignment              # 文字对齐
button.clip_text              # bool —— 裁剪溢出文字
button.shortcut               # Shortcut —— 快捷键

# 按钮组（单选按钮）
button.button_group           # ButtonGroup —— 加入同一组的按钮只有一个能被按下
```

### 18.2 核心方法

```gdscript
button.pressed.emit()         # 程序触发点击（Godot 4.3+）
button.set_pressed_no_signal(pressed: bool)  # 设置按下状态但不发射信号
```

### 18.3 信号

```gdscript
pressed               # 按钮被按下
button_down           # 按钮按下（物理按下）
button_up             # 按钮弹起
toggled(toggled_on: bool)  # 切换模式时的状态改变
```

### 18.4 使用示例

```gdscript
# 基础连接
func _ready() -> void:
    $StartButton.pressed.connect(_on_start_game)
    $QuitButton.pressed.connect(_on_quit_game)

# 带参数的连接
func _ready() -> void:
    $Level1Button.pressed.connect(_on_level_selected.bind(1))
    $Level2Button.pressed.connect(_on_level_selected.bind(2))

func _on_level_selected(level: int) -> void:
    print("选择了关卡：", level)

# 单选按钮组
func setup_radio_buttons() -> void:
    var group := ButtonGroup.new()
    $OptionA.button_group = group
    $OptionB.button_group = group
    $OptionC.button_group = group
    # 同一时间只有一个能被选中
```

---

## 十九、LineEdit——单行文本输入

### 19.1 核心属性

```gdscript
line_edit.text                # String —— 当前文本
line_edit.placeholder_text    # String —— 占位文字（灰色提示，输入内容后消失）
line_edit.secret              # bool —— 密码模式（显示为 * 号）
line_edit.secret_character    # String —— 密码模式下的替代字符（默认 "*"）
line_edit.max_length          # int —— 最大字符数（0 不限制）
line_edit.editable            # bool —— 是否可编辑
line_edit.caret_column        # int —— 光标位置
line_edit.clear_button_enabled  # bool —— 显示清除按钮
line_edit.expand_to_text_length  # bool —— 自动扩展宽度适应文本
line_edit.virtual_keyboard_enabled  # bool —— 移动端弹出虚拟键盘
```

### 19.2 核心方法

```gdscript
line_edit.clear()             # 清空文本
line_edit.select_all()        # 全选
line_edit.select(from: int, to: int)  # 选择指定范围
line_edit.deselect()          # 取消选择
line_edit.delete_char_at_caret()      # 删除光标处字符
line_edit.delete_text(from: int, to: int)  # 删除指定范围
line_edit.insert_text_at_caret(text: String)  # 在光标处插入文本
line_edit.has_undo() -> bool  # 是否有可撤销操作
line_edit.has_redo() -> bool  # 是否有可重做操作
line_edit.undo() / line_edit.redo()
line_edit.menu_option(option: int)  # 执行右键菜单选项（复制、粘贴等）
```

### 19.3 信号

```gdscript
text_changed(new_text: String)       # 文本改变
text_submitted(new_text: String)     # 按下 Enter 提交
```

---

## 二十、ProgressBar——进度条

### 20.1 核心属性

```gdscript
progress_bar.value            # float —— 当前值
progress_bar.min_value        # float —— 最小值
progress_bar.max_value        # float —— 最大值
progress_bar.step             # float —— 步进值
progress_bar.ratio            # float —— 比例（只读，= (value - min) / (max - min)）
progress_bar.percent_visible  # bool —— 是否显示百分比文字
progress_bar.show_percentage  # bool —— 是否在进度条上显示百分比
```

### 20.2 使用示例

```gdscript
# 血条
func _ready() -> void:
    $HealthBar.min_value = 0
    $HealthBar.max_value = 100
    $HealthBar.value = 100

func take_damage(amount: int) -> void:
    var hp := $ProgressBar as ProgressBar
    hp.value -= amount

# 带动画的血条变化
func update_health(new_hp: float) -> void:
    var tween := create_tween()
    tween.tween_property($HealthBar, "value", new_hp, 0.3)
```

---

## 二十一、Panel / ColorRect / TextureRect

### 21.1 Panel

带样式面板，适合做背景、对话框背景：

```gdscript
panel.add_theme_stylebox_override("panel", some_stylebox)
```

### 21.2 ColorRect

纯色矩形——最简单的可视化调试工具，也适合做遮罩、过渡：

```gdscript
color_rect.color = Color(0, 0, 0, 0.5)  # 半透明黑色矩形
color_rect.size = get_viewport_rect().size  # 全屏遮罩

# 淡入淡出过渡
func fade_in(duration: float) -> void:
    $FadeRect.color = Color.BLACK
    var tween := create_tween()
    tween.tween_property($FadeRect, "color:a", 0.0, duration)

func fade_out(duration: float) -> void:
    $FadeRect.color = Color(0, 0, 0, 0)
    var tween := create_tween()
    tween.tween_property($FadeRect, "color:a", 1.0, duration)
```

### 21.3 TextureRect

显示一张纹理，可以控制拉伸方式：

```gdscript
texture_rect.texture          # Texture2D —— 贴图
texture_rect.expand_mode      # 缩放模式：
                               #   EXPAND_KEEP_SIZE       —— 保持原始大小
                               #   EXPAND_IGNORE_SIZE      —— 忽略原始大小，拉伸填满
                               #   EXPAND_FIT_WIDTH        —— 适应宽度
                               #   EXPAND_FIT_WIDTH_PROPORTIONAL —— 适应宽度并保持比例
                               #   EXPAND_FIT_HEIGHT       —— 适应高度
                               #   EXPAND_FIT_HEIGHT_PROPORTIONAL —— 适应高度并保持比例
texture_rect.stretch_mode     # 拉伸模式（平铺、缩放等）
texture_rect.flip_h / flip_v  # 翻转
texture_rect.modulate         # 颜色调制
```

---

## 二十二、Container 系列——自动布局

### 22.1 HBoxContainer / VBoxContainer

```gdscript
# 水平排列
var hbox := HBoxContainer.new()
hbox.add_theme_constant_override("separation", 10)  # 控件间距 10px

# 垂直排列
var vbox := VBoxContainer.new()
vbox.add_theme_constant_override("separation", 5)

# 在容器中添加控件
vbox.add_child(Label.new())
vbox.add_child(Button.new())

# 子控件的 size_flags 控制拉伸行为
var button := Button.new()
button.size_flags_horizontal = Control.SIZE_EXPAND | Control.SIZE_FILL
# SIZE_EXPAND: 尽可能占满可用空间
# SIZE_FILL: 强制填满分得的空间
```

### 22.2 GridContainer

```gdscript
var grid := GridContainer.new()
grid.columns = 3          # 3 列
# 子控件从左到右、从上到下排列
for i in range(9):
    var btn := Button.new()
    btn.text = str(i + 1)
    grid.add_child(btn)
```

### 22.3 MarginContainer / CenterContainer

```gdscript
# MarginContainer —— 添加内边距
var margin := MarginContainer.new()
margin.add_theme_constant_override("margin_left", 20)
margin.add_theme_constant_override("margin_top", 10)
margin.add_theme_constant_override("margin_right", 20)
margin.add_theme_constant_override("margin_bottom", 10)

# CenterContainer —— 居中
var center := CenterContainer.new()
center.add_child(some_control)  # some_control 会居中显示
```

### 22.4 ScrollContainer

```gdscript
# 当内容超出容器大小时自动出现滚动条
var scroll := ScrollContainer.new()
scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED  # 禁止水平滚动
scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO        # 自动显示垂直滚动条

scroll.follow_focus = true  # 自动滚动到聚焦的控件

# 代码控制滚动
scroll.scroll_vertical = 100  # 滚动到垂直 100px 位置
scroll.scroll_horizontal = 0
```

---

## 二十三、CanvasLayer——独立的渲染层

### 23.1 用途

`CanvasLayer` 创建一个独立的 2D 渲染层，不受相机移动影响。游戏 UI 的最佳容器。

```gdscript
canvas_layer.layer          # int —— 层级编号（越大越在上层）
canvas_layer.offset         # Vector2 —— 偏移
canvas_layer.rotation       # float —— 旋转
canvas_layer.scale          # Vector2 —— 缩放
canvas_layer.follow_viewport_enabled  # bool —— 是否跟随视口
```

### 23.2 使用示例

```gdscript
# UI 层的标准设置：
# 创建一个 CanvasLayer 节点，把所有 UI 放里面
# CanvasLayer 内部的东西不受 Camera2D 影响
# layer 数值：
#   -1 = 在所有内容下面
#   0 = 默认，和游戏内容同层
#   1 = 在游戏内容上面（UI 通常用这个）
#   更高值 = 更上层

# 暂停菜单（渲染在游戏画面上面）
# PauseMenu (CanvasLayer, layer = 128)
#   └── ColorRect (半透明黑色背景)
#       └── Panel (菜单面板)
```

---

## 二十四、Path2D + PathFollow2D——路径系统

### 24.1 Path2D

```gdscript
path.curve                    # Curve2D —— 路径曲线
# 在编辑器中可以直接用鼠标画出路径
```

### 24.2 PathFollow2D

作为 `Path2D` 的子节点，自动沿路径移动：

```gdscript
path_follow.progress          # float —— 沿路径的距离
path_follow.progress_ratio    # float —— 沿路径的比例（0.0-1.0）
path_follow.h_offset          # float —— 偏离路径的水平偏移
path_follow.v_offset          # float —— 偏离路径的垂直偏移
path_follow.rotates           # bool —— 是否随路径旋转
path_follow.loop              # bool —— 是否循环
```

### 24.3 使用示例

```gdscript
# 让一个物体沿路径移动
extends Path2D

func _ready() -> void:
    var follower := $PathFollow2D
    follower.loop = false

# 在另一个脚本中控制
func move_along_path(speed: float) -> void:
    $Path2D/PathFollow2D.progress += speed * get_process_delta_time()

# 把敌人放在 PathFollow2D 下，它们就会自动沿路径走
```

---

## 二十五、Parallax2D / ParallaxBackground——视差滚动

让远景比近景移动得更慢，营造深度感：

```gdscript
# ParallaxBackground (Node2D)
#   ├── ParallaxLayer (scroll_scale = 0.2) ← 远景（移动最慢）
#   │   └── Sprite2D (远山贴图)
#   ├── ParallaxLayer (scroll_scale = 0.5) ← 中景
#   │   └── Sprite2D (树木贴图)
#   └── ParallaxLayer (scroll_scale = 1.0) ← 近景（跟随相机正常移动）

parallax_layer.scroll_scale   # Vector2 —— 滚动比例（0 = 不动，1 = 正常速度）
parallax_layer.motion_mirroring  # Vector2 —— 运动镜像（用于无缝循环）
```

---

## 二十六、NavigationAgent2D——自动寻路

### 26.1 使用前提

需要配合 `NavigationRegion2D` 定义导航区域：

```gdscript
# 1. 在场景中添加 NavigationRegion2D
# 2. 给它设置一个 NavigationPolygon（定义可行走区域）
# 3. 给需要进行寻路的角色添加 NavigationAgent2D
```

### 26.2 核心属性

```gdscript
agent.target_position          # Vector2 —— 目标位置（设置后自动计算路径）
agent.path_desired_distance    # float —— 距离路径点多远视为到达
agent.target_desired_distance  # float —— 距离目标点多远视为到达
agent.path_max_distance        # float —— 最大寻路距离
agent.navigation_layers        # int —— 使用哪些导航层
agent.avoidance_enabled        # bool —— 是否启用避让（多个单位不会互相重叠）
agent.max_speed                # float —— 最大移动速度
agent.radius                   # float —— 寻路半径
agent.neighbor_distance        # float —— 避让检测距离
agent.time_horizon_agents      # float —— 对其他代理的预测时间（秒）
agent.time_horizon_obstacles   # float —— 对静态障碍物的预测时间（秒）
```

### 26.3 核心方法

```gdscript
agent.get_next_path_position() -> Vector2    # 下一个路径点
agent.is_navigation_finished() -> bool       # 是否到达目标
agent.is_target_reachable() -> bool          # 目标是否可达
agent.distance_to_target() -> float          # 到目标的距离
agent.get_final_position() -> Vector2        # 最终目标位置
agent.set_velocity(velocity: Vector2)        # 设置当前速度（用于避让计算）
```

### 26.4 使用示例

```gdscript
extends CharacterBody2D

@onready var agent: NavigationAgent2D = $NavigationAgent2D

func _ready() -> void:
    # 首次设置目标后需要等一帧让服务器计算路径
    actor_setup.call_deferred()

func actor_setup() -> void:
    await get_tree().physics_frame
    agent.target_position = target_global_position

func _physics_process(_delta: float) -> void:
    if agent.is_navigation_finished():
        return

    var next_point := agent.get_next_path_position()
    var direction := global_position.direction_to(next_point)
    velocity = direction * move_speed
    agent.set_velocity(velocity)  # 通知避让系统
    move_and_slide()

# 更新目标
func set_target(target: Vector2) -> void:
    agent.target_position = target
```

---

## 二十七、PackedScene——场景的加载与实例化

### 27.1 核心方法

```gdscript
# 加载场景资源
var scene: PackedScene = load("res://scenes/enemy.tscn") as PackedScene

# 实例化
var instance: Node = scene.instantiate()
# 或指定泛型类型
var enemy: Enemy = scene.instantiate() as Enemy

# 设置实例的属性后加入场景
enemy.position = Vector2(100, 200)
add_child(enemy)

# 切换场景
func change_scene(path: String) -> void:
    get_tree().change_scene_to_file(path)
    # 或者
    get_tree().change_scene_to_packed(scene)

# 重新加载当前场景
func reload_scene() -> void:
    get_tree().reload_current_scene()
```

### 27.2 场景打包状态

```gdscript
var state := scene.get_state()
# PackedScene.GenEditState —— 可以获取场景打包时的节点属性
```

---

## 二十八、Input——输入处理

### 28.1 Input 单例的常用方法

```gdscript
# ===== 持续输入检测（在 _process / _physics_process 中使用）=====
Input.is_action_pressed("jump")          # 是否持续按住
Input.is_action_just_pressed("jump")     # 是否刚按下（仅本帧为 true）
Input.is_action_just_released("jump")    # 是否刚松开（仅本帧为 true）
Input.get_action_strength("move_right")  # 获取动作强度（0.0-1.0，手柄扳机键等）

# ===== 轴向输入 =====
var horizontal := Input.get_axis("move_left", "move_right")
# 返回 -1.0（左）到 1.0（右），自动处理 deadzone
var vertical := Input.get_axis("move_up", "move_down")
# 返回 -1.0（上）到 1.0（下）

var input_vector := Input.get_vector("move_left", "move_right", "move_up", "move_down")
# 返回归一化的 Vector2

# ===== 键鼠状态 =====
Input.is_key_pressed(KEY_SPACE)              # 键是否按住
Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)  # 鼠标按键
Input.get_last_mouse_velocity()              # 鼠标移动速度

# ===== 鼠标位置 =====
var mouse_pos := get_global_mouse_position()  # 全局鼠标位置
var local_pos := get_local_mouse_position()    # 相对于当前节点的鼠标位置

# ===== 输入模式 =====
Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)  # 捕获鼠标（FPS 游戏）
Input.set_mouse_mode(Input.MOUSE_MODE_HIDDEN)    # 隐藏鼠标
Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)   # 显示鼠标（默认）
Input.set_mouse_mode(Input.MOUSE_MODE_CONFINED)  # 限制鼠标在窗口内

# ===== 震动（手柄）=====
Input.start_joy_vibration(device: int, weak_magnitude: float, strong_magnitude: float, duration: float)
Input.stop_joy_vibration(device: int)
```

### 28.2 输入事件处理

```gdscript
func _input(event: InputEvent) -> void:
    # 键盘
    if event is InputEventKey:
        if event.keycode == KEY_ESCAPE and event.pressed:
            _on_escape_pressed()

    # 鼠标按键
    if event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
            _on_click(event.position)

    # 鼠标移动
    if event is InputEventMouseMotion:
        _on_mouse_move(event.relative)  # relative = 移动增量

    # 手柄
    if event is InputEventJoypadButton:
        if event.button_index == JOY_BUTTON_A and event.pressed:
            _on_joy_a_pressed()

    # 手柄摇杆
    if event is InputEventJoypadMotion:
        if event.axis == JOY_AXIS_LEFT_X:
            pass
```

---

## 二十九、FileAccess——文件读写

### 29.1 核心方法

```gdscript
# ===== 写入文件 =====
func save_data(data: Dictionary) -> void:
    var file := FileAccess.open("user://savegame.json", FileAccess.WRITE)
    if file == null:
        printerr("无法打开文件进行写入：", FileAccess.get_open_error())
        return

    file.store_string(JSON.stringify(data, "\t"))
    file.close()

# ===== 读取文件 =====
func load_data() -> Variant:
    if not FileAccess.file_exists("user://savegame.json"):
        return null

    var file := FileAccess.open("user://savegame.json", FileAccess.READ)
    if file == null:
        return null

    var content := file.get_as_text()
    file.close()

    var json := JSON.new()
    var error := json.parse(content)
    if error != OK:
        printerr("JSON 解析失败")
        return null

    return json.data

# ===== 文件操作 =====
FileAccess.file_exists(path)           # 文件是否存在
FileAccess.get_modified_time(path)     # 最后修改时间
DirAccess.dir_exists_absolute(path)    # 目录是否存在

# 使用 DirAccess 操作目录
var dir := DirAccess.open("user://")
if dir:
    dir.make_dir("saves")              # 创建目录
    var files := dir.get_files()       # 获取文件列表
    for f in files:
        print(f)
```

---

## 三十、常用全局单例一览

这些是引擎预置的全局单例，任何地方都可以直接使用：

```gdscript
# 场景树
get_tree()            # SceneTree —— 获取场景树
                      #   .root —— 根节点
                      #   .current_scene —— 当前场景
                      #   .paused —— 设置 true 暂停整个游戏
                      #   .change_scene_to_file("res://...tscn")
                      #   .quit() —— 退出游戏

# 输入
Input                 # 输入单例。见第二十八章

# 显示
DisplayServer         # 显示服务器
                      #   .window_set_title("我的游戏")
                      #   .window_set_size(Vector2i(1280, 720))
                      #   .window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
                      #   .get_screen_count()
                      #   .screen_get_size()

# 操作系统
OS                    # 操作系统接口
                      #   .get_name() —— "Windows" / "Linux" / "macOS" / "Android" / "iOS"
                      #   .get_executable_path()
                      #   .get_cmdline_args() —— 命令行参数
                      #   .get_ticks_msec() —— 启动以来的毫秒数
                      #   .get_static_memory_usage()
                      #   .alert("消息", "标题") —— 弹出系统对话框

# 时间
Time                  # 时间工具
                      #   .get_datetime_dict_from_system() —— 当前日期时间字典
                      #   .get_unix_time_from_system() —— Unix 时间戳

# 数学
@GDScript             # 全局数学函数
                      #   randf() —— 0-1 随机浮点数
                      #   randf_range(0.0, 100.0) —— 范围内随机浮点数
                      #   randi() % 100 —— 0-99 随机整数
                      #   randi_range(1, 10) —— 1-10 随机整数
                      #   wrapf(value, 0.0, 360.0) —— 循环包裹
                      #   lerp(a, b, t) —— 线性插值
                      #   lerpf(a, b, t) —— float 专门版本
                      #   inverse_lerp(a, b, value) —— 反插值
                      #   remap(value, from1, from2, to1, to2) —— 重新映射
                      #   smoothstep(from, to, x) —— 平滑步进
                      #   snapped(value, step) —— 对齐到步长
                      #   move_toward(from, to, delta) —— 向目标移动

# 数学常量
PI                     # 3.14159...
TAU                    # 2 * PI = 6.28318...
INF                    # 无穷大
NAN                    # 非数值

# 物理服务器
PhysicsServer2D        # 2D 物理服务器（底层 API）
PhysicsServer3D        # 3D 物理服务器（底层 API）

# 渲染服务器
RenderingServer        # 渲染服务器（底层 API）

# 项目设置
ProjectSettings        # 项目设置
                       #   .get_setting("physics/2d/default_gravity")
                       #   .set_setting("display/window/size/viewport_width", 1920)

# 翻译
TranslationServer      # 翻译服务器

# 资源
ResourceLoader         # 资源加载器
                       #   .load("res://...") —— 等同于 load()
                       #   .exists("res://...")

# 引擎
Engine                 # 引擎信息
                       #   .get_version_info() —— 版本信息字典
                       #   .get_frames_per_second() —— 当前 FPS
                       #   .get_physics_frames_per_second() —— 物理 FPS
                       #   .max_fps —— 设置最大帧率
```

---

## 三十一、实用代码模板合集

### 31.1 完整的 2D 平台跳跃角色

```gdscript
class_name PlatformerPlayer
extends CharacterBody2D

@export var speed: float = 300.0
@export var jump_velocity: float = -400.0
@export var acceleration: float = 1500.0
@export var friction: float = 1000.0
@export var coyote_time: float = 0.1       # 土狼时间（离开边缘后仍可跳跃）
@export var jump_buffer_time: float = 0.1   # 跳跃缓冲（落地前按跳也有效）

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")
var coyote_timer: float = 0.0
var jump_buffer_timer: float = 0.0

@onready var sprite: AnimatedSprite2D = $AnimatedSprite2D

func _physics_process(delta: float) -> void:
    # 重力
    if not is_on_floor():
        velocity.y += gravity * delta
        coyote_timer -= delta
    else:
        coyote_timer = coyote_time

    # 跳跃缓冲
    if Input.is_action_just_pressed("jump"):
        jump_buffer_timer = jump_buffer_time
    else:
        jump_buffer_timer -= delta

    # 跳跃
    if jump_buffer_timer > 0.0 and coyote_timer > 0.0:
        velocity.y = jump_velocity
        jump_buffer_timer = 0.0
        coyote_timer = 0.0

    # 可变跳跃高度（松开跳跃键时减少上升速度）
    if Input.is_action_just_released("jump") and velocity.y < 0:
        velocity.y *= 0.5

    # 水平移动
    var direction := Input.get_axis("move_left", "move_right")
    if direction != 0:
        velocity.x = move_toward(velocity.x, direction * speed, acceleration * delta)
    else:
        velocity.x = move_toward(velocity.x, 0, friction * delta)

    # 动画
    if not is_on_floor():
        sprite.play("jump" if velocity.y < 0 else "fall")
    elif abs(velocity.x) > 10:
        sprite.play("walk")
        sprite.flip_h = velocity.x < 0
    else:
        sprite.play("idle")

    move_and_slide()
```

### 31.2 单例管理器模板

```gdscript
# game_manager.gd（设置为 Autoload）
extends Node

var score: int = 0
var high_score: int = 0
var current_level: int = 1
var is_game_paused: bool = false

func _ready() -> void:
    load_high_score()

func add_score(points: int) -> void:
    score += points
    if score > high_score:
        high_score = score
        save_high_score()

func reset_score() -> void:
    score = 0

func load_high_score() -> void:
    if FileAccess.file_exists("user://highscore.save"):
        var file := FileAccess.open("user://highscore.save", FileAccess.READ)
        high_score = file.get_32()
        file.close()

func save_high_score() -> void:
    var file := FileAccess.open("user://highscore.save", FileAccess.WRITE)
    file.store_32(high_score)
    file.close()

func pause_game() -> void:
    is_game_paused = true
    get_tree().paused = true

func resume_game() -> void:
    is_game_paused = false
    get_tree().paused = false
```

### 31.3 对象池模板

```gdscript
# object_pool.gd
class_name ObjectPool
extends Node

@export var prefab: PackedScene
@export var pool_size: int = 20

var _pool: Array[Node] = []
var _next_available: int = 0

func _ready() -> void:
    _pool.resize(pool_size)
    for i in pool_size:
        var obj := prefab.instantiate()
        obj.set_process(false)
        obj.set_physics_process(false)
        obj.hide()
        add_child(obj)
        _pool[i] = obj

func get_object() -> Node:
    # 检查是否有空闲对象
    for i in range(_pool.size()):
        var idx := (_next_available + i) % _pool.size()
        if not _pool[idx].visible:
            _next_available = (idx + 1) % _pool.size()
            var obj := _pool[idx]
            obj.show()
            obj.set_process(true)
            obj.set_physics_process(true)
            return obj

    # 池耗尽——扩容
    printerr("对象池耗尽，扩容中...")
    var obj := prefab.instantiate()
    _pool.append(obj)
    add_child(obj)
    return obj

func return_object(obj: Node) -> void:
    obj.hide()
    obj.set_process(false)
    obj.set_physics_process(false)
```

---

## 三十二、常用 GDScript 速查

### 32.1 字符串操作

```gdscript
var s: String = "Hello, Godot!"
var len := s.length()                     # 长度
var upper := s.to_upper()                 # 全大写
var lower := s.to_lower()                 # 全小写
var sub := s.substr(0, 5)                 # 子串 "Hello"
var has := s.contains("Godot")            # 是否包含
var idx := s.find("Godot")                # 查找位置
var replaced := s.replace("Godot", "World")  # 替换
var split := s.split(", ")                # 分割成数组 ["Hello", "Godot!"]
var joined := ", ".join(["a", "b", "c"])  # 连接 "a, b, c"
var formatted := "分数：%d，名字：%s" % [100, "Player"]  # 格式化
var trimmed := s.strip_edges()            # 去除首尾空白
```

### 32.2 数学函数

```gdscript
# 从 GDScript 全局作用域直接调用
abs(-5)                   # 绝对值 → 5
ceil(3.2)                 # 向上取整 → 4
floor(3.8)                # 向下取整 → 3
round(3.5)                # 四舍五入 → 4
clamp(value, 0, 100)      # 限制在范围内
clampf(value, 0.0, 1.0)   # float 版本
sign(-5)                  # 符号 → -1
lerp(0, 100, 0.3)         # 线性插值 → 30
lerpf(0.0, 100.0, 0.3)    # float 版本
inverse_lerp(0, 100, 30)  # 反插值 → 0.3
remap(0.5, 0, 1, 0, 360)  # 重新映射 → 180
smoothstep(0, 1, 0.3)     # 平滑步进
move_toward(0, 100, 30)   # 渐变移动 → 30
snapped(3.7, 0.5)          # 对齐到步长 → 3.5
wrapf(370, 0, 360)         # 循环包裹 → 10
lerp_angle(0, PI * 1.5, 0.5)  # 角度插值（处理环绕）
angle_difference(a, b)     # 两角度的最短差值
is_equal_approx(0.1 + 0.2, 0.3)  # 浮点数近似相等

# 指数
pow(2, 8)                  # 2^8 = 256
sqrt(9)                    # 平方根 → 3
exp(1)                     # e^1
log(2.718)                 # 自然对数
sin(angle) / cos(angle) / tan(angle)  # 三角函数（弧度）
asin(x) / acos(x) / atan(x)           # 反三角函数
atan2(y, x)                # 从 (x, y) 计算角度
```

### 32.3 随机数

```gdscript
# 设置种子（用于可重现的随机）
seed(42)

# 初始化随机数生成器
var rng := RandomNumberGenerator.new()
rng.randomize()  # 用当前时间作为种子

# 生成随机数
var f: float = randf()               # 0.0 到 1.0
var f2: float = randf_range(0, 100)  # 指定范围
var i: int = randi() % 100           # 0 到 99
var i2: int = randi_range(1, 10)     # 1 到 10

# 使用 RNG 对象（推荐，可控制种子）
rng.randf()                           # 0.0 到 1.0
rng.randf_range(0.0, 100.0)           # 指定范围
rng.randi_range(1, 6)                 # 整数范围（骰子）
rng.randfn(mean, deviation)           # 正态分布（高斯分布）
rng.rand_weighted([0.5, 0.3, 0.2])    # 加权随机（返回索引）
```

---

## 总结

这篇手册覆盖了 Godot 4 中最核心的节点类型，从基类 `Node` 到 2D 物理、UI、音频、动画、TileMap、文件操作等方方面面。

**阅读建议**：

- **第 1-7 章**（Node / Node2D / Sprite / Collision / CharacterBody / RigidBody / StaticBody）是 2D 游戏的基础，务必掌握
- **第 8 章**（Area2D）极其常用，拾取、伤害、触发器都靠它
- **第 9-11 章**（RayCast / Timer / Camera）频率高，是解决具体问题的利器
- **第 12-13 章**（音频）相对独立，用到时查阅即可
- **第 14 章**（AnimationPlayer）是动画系统的核心，掌握它就能让游戏活起来
- **第 15-25 章**是进阶内容，按需学习
- **第 26-27 章**（Navigation / PackedScene）是中大型项目必备
- **第 28-31 章**是日常开发中频繁查阅的参考

搭配《Godot 引擎完全入门指南》阅读效果最佳。祝你在 Godot 的世界里做出属于自己的游戏！

---

*本文基于 Godot 4.X 系列撰写。如有疑问或发现错误，欢迎通过评论区交流。*
