---
title: 'Kubernetes详解：从架构原理到生产配置与日常使用'
date: 2026-07-10T17:00:00+08:00
draft: false
tags: ["Kubernetes", "K8s", "容器编排", "云原生", "Docker", "DevOps", "部署"]
---

Kubernetes（K8s）是目前容器编排的事实标准。本文从三个方面讲解：架构原理（理解各组件的职责和交互）、配置（编写生产可用的 YAML）、日常使用（kubectl 操作和调试）。

## 第一部分：架构原理

### 一、全局视角：K8s 在解决什么问题

假设你有 20 台服务器，要部署 10 个微服务，每个微服务 3 个实例。手动操作的话：

- 选择哪台机器跑哪个实例 → 需要调度器
- 某个实例挂了 → 需要自动重启
- 机器宕机了 → 需要把上面的实例迁移到其他机器
- 微服务之间怎么发现对方 → 需要服务发现
- 怎么控制外部流量进来 → 需要负载均衡
- 配置更新了怎么推给所有实例 → 需要配置管理

K8s 把这些全部自动化。它的设计思想是：你描述**期望状态**（我要 3 个 nginx 实例），K8s 的控制循环持续把**实际状态**调整到**期望状态**。这个过程叫 **Reconciliation Loop**。

```text
期望状态: 3 个 nginx Pod 都在 Running
实际状态: 只有 2 个在 Running（第三个节点挂了）

→ K8s 调度器检测到差异
→ 在健康的节点上启动第 3 个 Pod
→ 实际状态 = 期望状态
→ 循环继续监控
```

### 二、集群架构

```text
┌───────────────────── Control Plane (Master) ─────────────────────┐
│                                                                    │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │   API    │  │ Controller│  │   Scheduler  │  │   etcd      │  │
│  │  Server  │  │  Manager  │  │              │  │  (数据库)    │  │
│  │  (kube-  │  │ (kube-    │  │ (kube-       │  │             │  │
│  │  apiserver)│ │ controller│  │  scheduler) │  │             │  │
│  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  └──────┬──────┘  │
│       │              │               │                  │        │
│       └──────────────┼───────────────┼──────────────────┘        │
│                      │               │                            │
└──────────────────────┼───────────────┼────────────────────────────┘
                       │               │
                       ▼               ▼
┌───────────────────── Worker Node 1 ──────────────────────────────┐
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                        │
│  │  kubelet │  │ kube-proxy│  │ Container │                       │
│  │          │  │          │  │  Runtime  │                       │
│  └──────────┘  └──────────┘  │(containerd│                       │
│                               │ / cri-o)  │                       │
│                               └──────────┘                       │
│  ┌────────┐  ┌────────┐  ┌────────┐                              │
│  │  Pod A │  │  Pod B │  │  Pod C │                              │
│  └────────┘  └────────┘  └────────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

#### 2.1 Control Plane 组件

**kube-apiserver**：K8s 的"前门"。所有操作（kubectl、控制器、调度器）都通过 API Server 的 REST API 进行。它是唯一直接读写 etcd 的组件。设计成无状态的，可以水平扩展，前面放 LB。

一个请求的典型处理流程：
1. 认证（Authentication）：你是谁？证书/Token/OpenID
2. 授权（Authorization）：你能做什么？RBAC 策略
3. 准入控制（Admission Control）：这个请求合规吗？资源配额、安全策略
4. 写入 etcd

**etcd**：分布式 KV 存储，保存 K8s 集群的所有状态（Pod 定义、Service 定义、ConfigMap、Secrets 等）。所有组件不直接通信——它们在 etcd 中读写对象，通过 API Server 的 watch 机制获取变更通知。etcd 是 K8s 的单一致命点，生产环境必须 3 节点或 5 节点（奇数个，满足 Raft 多数派）。

> ⚠️ etcd 对磁盘延迟极其敏感。用 SSD，不要用机械硬盘，不要和日志/监控共用磁盘。etcd 的 fsync 延迟直接决定 API Server 的响应延迟。

**kube-scheduler**：监听 API Server 中 `spec.nodeName` 为空的 Pod，为它选择一个合适的 Node，然后把 `spec.nodeName` 写回去。调度分两个阶段：

1. **过滤**（Filtering）：排除不满足条件的 Node（资源不够、有 taint 不匹配 toleration、nodeSelector 不匹配等）
2. **打分**（Scoring）：对剩余 Node 打分，选最高分（LeastAllocated 优先资源利用率低的、BalancedResourceAllocation 优先 CPU/Mem 均衡的等）

```text
10 个 Node
    → Filter: 去掉 3 个资源不足的，剩 7 个
    → Score: 对 7 个打分
        Node A: 85分（CPU/Mem 都很充裕）
        Node B: 72分
        ...
    → 选 Node A，把它写到 Pod.spec.nodeName
```

**kube-controller-manager**：运行各种控制器，每个控制器是一个独立的 Reconciliation Loop。常见的：

| 控制器 | 职责 |
|--------|------|
| Node Controller | 监控节点状态，节点不可达时驱逐 Pod |
| ReplicaSet Controller | 保证 Pod 数量 = replicas |
| Deployment Controller | 管理滚动更新（创建新的 ReplicaSet，扩缩） |
| Service Controller | 为 Service 分配 ClusterIP |
| EndpointSlice Controller | 跟踪 Service 后端 Pod 的 IP |
| Job Controller | 管理一次性任务 |

#### 2.2 Worker Node 组件

**kubelet**：每个 Node 上的"工头"。接收 API Server 分配给本 Node 的 Pod 规格，调用 Container Runtime 启动容器，然后持续监控容器状态并上报给 API Server。kubelet 还负责容器的健康检查（liveness/readiness/startup probe）。

**kube-proxy**：每个 Node 上运行，实现 Service 的网络代理。监听 API Server 中 Service 和 EndpointSlice 的变化，更新本机的 iptables/IPVS 规则。当一个 Pod 访问 Service 的 ClusterIP 时，实际上是本机的 iptables 规则把流量 DNAT 到某个后端 Pod。

**Container Runtime**：实际跑容器的软件。K8s 定义了 CRI（Container Runtime Interface）接口，任何实现 CRI 的运行时都可以接入。
- containerd（Docker 的底层运行时，目前最常用）
- CRI-O（Red Hat 主导）
- Docker Engine（K8s 1.24 起需要额外安装 cri-dockerd 适配器）

#### 2.3 一个 Pod 的创建全流程

```text
1. kubectl apply 发送 YAML 到 API Server
2. API Server 认证、授权、准入控制 → 写入 etcd
3. Scheduler watch 到新 Pod（nodeName 为空）
    → 选择 Node N → 更新 Pod.spec.nodeName = N → 写回 etcd
4. Node N 的 kubelet watch 到分配给自己的 Pod
    → 调用 CRI 创建容器
    → 调用 CNI 插件分配网络
    → 调用 CSI 插件挂载存储
    → 更新 Pod status 到 API Server（ContainerCreating → Running）
5. kube-proxy watch 到 Pod IP → 更新 iptables/IPVS 规则
```

每个步骤都是独立组件通过 watch + reconcile 完成的，组件间不直接调用，全部经过 API Server/etcd。

---

## 第二部分：核心资源对象

### 三、Pod — 最小调度单元

Pod 是 K8s 调度的原子单位。一个 Pod 可以包含 1 个或多个容器，这些容器共享网络命名空间（同一个 IP）、IPC 命名空间、以及可选的共享存储卷。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 80
    resources:
      requests:          # 调度时的最低保证
        cpu: "100m"      # 0.1 核
        memory: "128Mi"  # 128 MiB
      limits:            # 运行时上限
        cpu: "500m"      # 0.5 核
        memory: "256Mi"
```

> ⚠️ `requests` 和 `limits` 的区别经常被误解。`requests` 用于调度决策（Scheduler 根据 `requests` 计算 Node 剩余资源），`limits` 是容器能使用的上限。如果 `requests=100m, limits=500m`，Node 上其他 Pod 空闲时这个 Pod 可以用到 500m，但调度时只按 100m 计算。

#### 3.1 多容器 Pod（Sidecar 模式）

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-sidecar
spec:
  containers:
  - name: app           # 主容器
    image: myapp:latest
    volumeMounts:
    - name: logs
      mountPath: /var/log/app
  - name: log-shipper   # Sidecar：收集日志
    image: fluentd:latest
    volumeMounts:
    - name: logs
      mountPath: /var/log/app
      readOnly: true
  volumes:
  - name: logs
    emptyDir: {}        # Pod 生命周期内的临时存储
```

Sidecar 模式的关键：两个容器通过共享 Volume 或 `localhost` 网络通信。log-shipper 从 shared volume 读取 app 的日志文件发送到日志系统。

#### 3.2 Init Containers

```yaml
spec:
  initContainers:
  - name: wait-for-db
    image: busybox:1.36
    command: ['sh', '-c', 'until nc -z db 5432; do sleep 2; done']
  - name: run-migration
    image: myapp:latest
    command: ['./migrate']
  containers:
  - name: app
    image: myapp:latest
```

Init Container 按顺序执行，每个完成（exit 0）后才执行下一个，全部完成后才启动主容器。如果 Init Container 失败，Pod 会重启它（根据 `restartPolicy`）。用于数据库等待、迁移、初始化配置等场景。

### 四、Deployment — 无状态应用的管理器

Deployment 是实际工作中最常用的资源。它管理 ReplicaSet，ReplicaSet 管理 Pod：

```text
Deployment → ReplicaSet → Pod
   (滚动更新)  (副本保证)   (运行容器)
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  labels:
    app: api-server
spec:
  replicas: 3                    # 期望 3 个 Pod
  selector:
    matchLabels:
      app: api-server            # 匹配这些标签的 Pod
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1                # 更新期间允许超出 replicas 的数量
      maxUnavailable: 0          # 更新期间允许不可用的数量
  template:                      # Pod 模板
    metadata:
      labels:
        app: api-server
        version: v2
    spec:
      containers:
      - name: app
        image: myapp:v2
        ports:
        - containerPort: 8080
        env:
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: host
        livenessProbe:           # 存活探针
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        readinessProbe:          # 就绪探针
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 3
```

滚动更新过程（replicas=3, maxSurge=1, maxUnavailable=0）：

```text
初始: [v1] [v1] [v1]
    → 创建 1 个新 Pod（maxSurge=1 允许 4 个 Pod）: [v1] [v1] [v1] [v2]
    → 新 Pod Ready 后，停掉 1 个旧 Pod: [v1] [v1] [v2]
    → 创建下一个新 Pod: [v1] [v1] [v2] [v2]
    → Ready 后停掉旧 Pod: [v1] [v2] [v2]
    → 重复直到全部为 v2
```

> ⚠️ Deployment 的 `selector.matchLabels` 必须是 Pod 模板 labels 的子集。如果 selector 选不中模板创建的 Pod，会不停地创建新 Pod（控制器以为 replicas 不够），最终触发 `kubectl describe` 里看到的 "ScalingReplicaSet" 循环。

#### 4.1 回滚

```bash
kubectl rollout undo deployment/api-server         # 回滚到上一个版本
kubectl rollout undo deployment/api-server --to-revision=2  # 回滚到指定版本
kubectl rollout history deployment/api-server      # 查看版本历史
```

Deployment 每次更新都会创建新的 ReplicaSet，旧 ReplicaSet 不会被删除（保留历史版本）。`rollout undo` 本质上就是把旧 ReplicaSet 重新 scale up，新 ReplicaSet scale down。

### 五、Service — 服务发现与负载均衡

Pod 的 IP 是临时的（Pod 重启 IP 会变）。Service 提供一个稳定的虚拟 IP（ClusterIP）和一个 DNS 名称：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-server
spec:
  type: ClusterIP        # 仅集群内部可访问
  selector:
    app: api-server      # 选择后端的 Pod
  ports:
  - name: http
    port: 80             # Service 暴露的端口
    targetPort: 8080     # Pod 上容器的端口
    protocol: TCP
```

Service 的工作原理：
1. EndpointSlice Controller watch Service 和 Pod，找到 selector 匹配的 Pod
2. 为 Service 分配一个 ClusterIP（默认为 10.x.x.x 段）
3. kube-proxy 在每个 Node 上写 iptables/IPVS 规则：`dest=ClusterIP:80 → DNAT 到某个 Pod:8080（随机/轮询）`

```text
Pod A → 访问 api-server:80 (DNS 解析 → ClusterIP 10.96.100.1)
     → 本机 iptables:
          -A KUBE-SERVICES -d 10.96.100.1 -p tcp --dport 80 -j KUBE-SVC-XXX
          -A KUBE-SVC-XXX -m statistic --mode random --probability 0.333 -j KUBE-SEP-A
          -A KUBE-SVC-XXX -m statistic --mode random --probability 0.500 -j KUBE-SEP-B
          -A KUBE-SVC-XXX -j KUBE-SEP-C
     → 最终 DNAT 到某个后端 Pod 的 IP:8080
```

#### 5.1 Service 类型

| 类型 | 用途 | 访问方式 |
|------|------|---------|
| ClusterIP | 集群内部通信 | `svc-name.namespace.svc.cluster.local` |
| NodePort | 从 Node IP 暴露端口 | `NodeIP:30000-32767` |
| LoadBalancer | 云厂商 LB 暴露 | 外部 LB IP → NodePort → Pod |
| ExternalName | 外部服务别名 | CNAME 到外部 DNS |

```yaml
# LoadBalancer 类型（云环境）
spec:
  type: LoadBalancer
  # 云厂商自动创建外部 LB 并把流量转到各 Node 的 NodePort上

# Headless Service（无 ClusterIP，直接返回 Pod IP）
spec:
  clusterIP: None       # DNS 查询返回所有后端 Pod 的 IP，而不是 Service IP
  # 用于 StatefulSet（需要 Pod 间直接通信的场景）
```

#### 5.2 服务发现

K8s 内置 DNS（CoreDNS），每个 Service 自动获得 DNS 记录：

```text
<service-name>.<namespace>.svc.cluster.local

# 例子：
api-server.default.svc.cluster.local      # 完整域名
api-server.default                        # 同 namespace 内可以省略后缀
api-server                                # 同 namespace 内
```

Pod 内的 `/etc/resolv.conf` 配置了 DNS 搜索域，所以 `api-server` 请求会自动被补全。

### 六、ConfigMap 和 Secret — 配置注入

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  app.yaml: |
    server:
      port: 8080
      read_timeout: 30s
    database:
      max_connections: 100
  log_level: "debug"
---
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
stringData:              # stringData 会自动 base64 编码到 data
  host: "db.internal:5432"
  password: "s3cr3t!"
  # 等价于手动 base64 编码后写入 data:
  # data:
  #   host: ZGIuaW50ZXJuYWw6NTQzMg==
```

在 Pod 中使用：

```yaml
spec:
  containers:
  - name: app
    # 方式 1: 整个 ConfigMap 挂载为文件（可以热更新）
    volumeMounts:
    - name: config
      mountPath: /etc/app/config.yaml
      subPath: app.yaml          # 只挂载 app.yaml 这个 key
    # 方式 2: 单个 key 注入为环境变量
    env:
    - name: LOG_LEVEL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: log_level
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: password
  volumes:
  - name: config
    configMap:
      name: app-config
```

> ⚠️ ConfigMap 作为 Volume 挂载时，更新 ConfigMap 后 kubelet 会定期同步文件（默认 ~1 分钟）。进程如果缓存了配置文件内容，需要监听文件变化或重启才能生效。环境变量方式的注入只在 Pod 启动时设置，ConfigMap 更新后环境变量不会改变——需要重启 Pod。

Secret 默认只做 base64 编码，不是加密。任何有 `get secret` RBAC 权限的用户都能读到明文。生产环境应该：
- 开启 etcd 静态加密（encryption at rest）
- 或使用外部密钥管理（Vault、AWS Secrets Manager、Azure Key Vault），通过 External Secrets Operator 同步

### 七、Ingress — HTTP/HTTPS 路由

Ingress 把外部 HTTP 流量路由到集群内的 Service：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls              # TLS 证书
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /users
        pathType: Prefix
        backend:
          service:
            name: user-service
            port:
              number: 80
      - path: /orders
        pathType: Prefix
        backend:
          service:
            name: order-service
            port:
              number: 80
```

> ⚠️ Ingress 只是一个定义 HTTP 路由规则的资源对象。它需要 **Ingress Controller**（如 nginx-ingress、traefik、contour）来实际执行。如果你 `kubectl apply` 了一个 Ingress 但没有安装 Ingress Controller，不会有任何效果。检查方式：`kubectl get pods -n ingress-nginx` 看看 Controller 是否在运行。

#### 7.1 Ingress Controller 工作原理

```text
                                             ┌──────────────┐
Internet → LB → Ingress Controller Pod →    │ user-service  │
               (nginx/haproxy/traefik)  →    │ order-service │
               watch Ingress 资源变化    →    │ auth-service  │
               动态生成 nginx.conf       →    └──────────────┘
```

Ingress Controller 是一个反向代理（nginx/haproxy），它 watch K8s API 的 Ingress 资源，把规则翻译成 nginx 配置并动态 reload。所以配置 Ingress 不用手动写 nginx.conf。

### 八、Namespace — 资源隔离

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
```

Namespace 是 K8s 中的虚拟集群。不同 Namespace 内的资源相互隔离（默认情况下网络不隔离，但可以用 NetworkPolicy 隔离）。常用场景：

```bash
kubectl get pods -n production
kubectl get pods -n staging
kubectl get pods -A  # 所有 namespace
```

```yaml
# 在每个 namespace 中设置资源配额
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: production
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
    persistentvolumeclaims: "10"
```

---

## 第三部分：日常使用（kubectl）

### 九、常用命令速查

```bash
# 查看资源
kubectl get pods                          # 列出 Pod
kubectl get pods -o wide                  # 增加 Node、IP 信息
kubectl get pods -w                       # watch 模式，持续监控变化
kubectl get all                           # 列出所有常用资源
kubectl get deploy,svc,cm,secret,ingress  # 列出指定类型

# 详情
kubectl describe pod <pod-name>           # 事件日志 + 详细状态
kubectl describe node <node-name>         # 节点资源和条件
kubectl get pod <pod-name> -o yaml        # 完整 YAML 输出
kubectl get events --sort-by='.lastTimestamp' # 最近事件

# 日志
kubectl logs <pod-name>                   # 标准输出日志
kubectl logs <pod-name> -c <container>    # 多容器 Pod 指定容器
kubectl logs <pod-name> --tail=100 -f     # 实时跟踪最后 100 行
kubectl logs <pod-name> --since=5m        # 最近 5 分钟
kubectl logs -l app=nginx --all-containers # 所有匹配 label 的 Pod 日志

# 进入容器
kubectl exec -it <pod-name> -- /bin/sh    # 进入容器 shell
kubectl exec <pod-name> -- ls /app        # 执行单条命令

# 端口转发（调试利器）
kubectl port-forward <pod-name> 8080:8080  # localhost:8080 → Pod:8080
kubectl port-forward svc/my-service 9090:80 # localhost:9090 → Service:80

# 资源操作
kubectl apply -f deployment.yaml          # 创建或更新
kubectl delete -f deployment.yaml         # 删除
kubectl delete pod <pod-name>             # 删除 Pod（Deployment 会自动重建）
kubectl scale deployment/app --replicas=5 # 手动扩缩容
kubectl rollout restart deployment/app    # 滚动重启（逐个重建 Pod）

# 调试
kubectl run debug --rm -it --image=busybox -- /bin/sh  # 临时 Pod 调试
kubectl top pods                           # Pod 资源使用
kubectl top nodes                          # Node 资源使用
kubectl api-resources                      # 列出所有 API 资源类型
```

### 十、调试 Pod 异常的流程

Pod 起不来是最常见的故障。调试的固定流程：

```bash
# 1. 看 Pod 状态
kubectl get pods
# NAME       READY   STATUS             RESTARTS   AGE
# my-app     0/1     CrashLoopBackOff   5          3m
# my-app     0/1     ImagePullBackOff   0          30s
# my-app     0/1     Pending            0          10s
# my-app     1/1     Running            0          5m    (正常情况)

# 2. describe 看 Events
kubectl describe pod my-app
# Events:
#   Type     Reason     Message
#   ----     ------     -------
#   Warning  Failed     Error: ImagePullBackOff
#   Normal   Pulling    Pulling image "myapp:v2"

# 3. 看日志
kubectl logs my-app
kubectl logs my-app --previous  # 上次容器的日志（CrashLoopBackOff 时很有用）
```

常见异常状态及含义：

| 状态 | 原因 | 排查方向 |
|------|------|---------|
| `Pending` | 调度失败 / 镜像拉取中 | describe 看 Events |
| `CrashLoopBackOff` | 容器启动后立即退出 | logs --previous 看退出原因；检查 command 是否正确 |
| `ImagePullBackOff` | 镜像拉取失败 | 检查 image 名称/标签；检查 imagePullSecrets |
| `ErrImagePull` | 同上（初始阶段） | 同上 |
| `Evicted` | Node 资源不足被驱逐 | 检查 Node 的 memory/disk pressure |
| `Terminating` 卡住 | 容器不响应 SIGTERM | 检查 preStop hook 或容器是否忽略了 SIGTERM |
| `OOMKilled` | 内存超限被内核杀死 | 增大 memory limits 或排查内存泄漏 |

### 十一、kubectl 高级技巧

```bash
# JSONPath 输出
kubectl get pods -o jsonpath='{.items[*].status.podIP}'

# 自定义列
kubectl get pods -o custom-columns=NAME:.metadata.name,IP:.status.podIP,NODE:.spec.nodeName

# 按 label 筛选
kubectl get pods -l 'app in (nginx, redis),tier=frontend'

# 按 field 筛选
kubectl get pods --field-selector=status.phase=Running

# 查看资源使用
kubectl describe node <node> | grep -A5 "Allocated resources"

# 删除 Evicted/Failed 的 Pod
kubectl delete pod --field-selector=status.phase=Failed -A

# 复制文件
kubectl cp <pod-name>:/path/to/file ./local-file    # 从 Pod 复制出来
kubectl cp ./local-file <pod-name>:/path/to/file    # 复制进 Pod

# 查看 API 资源的字段文档
kubectl explain deployment.spec.template.spec.containers
kubectl explain deployment.spec.strategy.rollingUpdate --recursive

# 模拟 apply（dry-run）
kubectl apply -f deployment.yaml --dry-run=client
kubectl apply -f deployment.yaml --dry-run=server  # K8s 1.18+
```

### 十二、上下文和配置管理

```bash
# 查看当前 context
kubectl config current-context

# 列出所有 context
kubectl config get-contexts

# 切换 context
kubectl config use-context prod-cluster

# 切换 namespace
kubectl config set-context --current --namespace=production

# 用 kubectx / kubens 更便捷
kubectx prod-cluster      # 切换集群
kubens kube-system        # 切换 namespace
```

`~/.kube/config` 是 kubectl 的配置文件，包含集群、用户和 context 的定义。context 绑定了一个集群 + 一个用户 + 一个 namespace：

```yaml
# ~/.kube/config 结构
apiVersion: v1
kind: Config
clusters:
- name: prod
  cluster:
    server: https://prod-api.example.com:6443
    certificate-authority-data: <base64>
users:
- name: prod-admin
  user:
    client-certificate-data: <base64>
    client-key-data: <base64>
contexts:
- name: prod-admin@prod
  context:
    cluster: prod
    user: prod-admin
    namespace: default
current-context: prod-admin@prod
```

> ⚠️ `~/.kube/config` 包含私钥（client-key-data）和证书。不要提交到 Git，不要分享给他人。用 RBAC 为每个用户/CI 生成独立的证书而不是共用 admin 证书。

---

## 第四部分：生产配置清单

### 十三、生产 Deployment 必须包含的配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
        version: "v1.2.3"         # ← 用于版本标记
      annotations:
        prometheus.io/scrape: "true"   # ← Prometheus 自动发现
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      terminationGracePeriodSeconds: 30  # ← 优雅关停时间

      # 亲和性和反亲和性
      affinity:
        podAntiAffinity:             # ← 避免所有副本都在同一个 Node
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: api-server
              topologyKey: kubernetes.io/hostname

      containers:
      - name: app
        image: registry.example.com/api-server:v1.2.3
        imagePullPolicy: IfNotPresent

        ports:
        - name: http
          containerPort: 8080
          protocol: TCP

        # 资源限制（生产必须设置！）
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "1000m"
            memory: "512Mi"

        # 探针（生产必须设置！）
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3       # 连续 3 次失败才 kill

        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2       # 连续 2 次失败就摘除流量

        # 环境变量
        env:
        - name: APP_ENV
          value: "production"
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password

        # 生命周期钩子
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"] # 等待 LB 摘除流量

        # 安全上下文
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true

        volumeMounts:
        - name: tmp
          mountPath: /tmp          # 只挂载可写目录
        - name: config
          mountPath: /etc/app
          readOnly: true

      # Node 选择
      nodeSelector:
        workload: application      # 只在标记了此标签的 Node 上调度

      # 容忍度
      tolerations:
      - key: "dedicated"
        operator: "Equal"
        value: "application"
        effect: NoSchedule

      volumes:
      - name: tmp
        emptyDir: {}
      - name: config
        configMap:
          name: api-server-config

      # 镜像拉取凭证（私有仓库需要）
      imagePullSecrets:
      - name: registry-credentials

      # 服务账户
      serviceAccountName: api-server-sa
```

### 十四、liveness 和 readiness 的使用误区

```text
livenessProbe 失败 → kubelet 杀掉容器并重建
readinessProbe 失败 → Service 摘除流量，但不杀容器
```

最常见的设计错误：

**错误 1**：liveness 依赖外部服务

```yaml
# 错误：数据库挂了会导致所有 Pod 被循环重启，加重故障
livenessProbe:
  exec:
    command: ["check_db_connection.sh"]
```

正确做法：liveness 只检查进程本身是否健康（能不能响应请求），不依赖外部。外部依赖放在 readiness 中。

**错误 2**：`initialDelaySeconds` 太短

如果你的应用启动需要 30 秒，但 `initialDelaySeconds: 5`，容器启动 5 秒后 liveness 开始检查→检查失败→容器被杀→再次启动→死循环。

正确：`initialDelaySeconds` > 应用启动时间。

**错误 3**：不给 liveness 和 readiness 设置 `failureThreshold`

默认 `failureThreshold: 3`。如果你的负载偶尔抖动 2 秒，没到 3 次失败就不会被杀。但如果某条链路持续失败，3 次探针（3 × periodSeconds = 30 秒）后容器会被重启。这个 30 秒是你自己控制的。

### 十五、优雅关停

K8s 删除 Pod 的流程：

```text
1. Pod 状态设为 Terminating → 从 Service Endpoints 摘除
2. kubelet 收到 SIGTERM → 发送给容器主进程（PID 1）
3. 等待 terminationGracePeriodSeconds（默认 30 秒）
4. 超时后发送 SIGKILL 强杀
```

你的应用需要：
- 监听 SIGTERM，收到后停止接收新请求
- 等待已接收的请求完成
- 关闭数据库连接、刷新日志缓冲
- exit 0

```go
// Go 程序监听 SIGTERM 的典型写法
quit := make(chan os.Signal, 1)
signal.Notify(quit, syscall.SIGTERM, syscall.SIGINT)

server := &http.Server{Addr: ":8080"}

go func() {
    <-quit
    log.Println("shutting down...")

    ctx, cancel := context.WithTimeout(context.Background(), 25*time.Second)
    defer cancel()

    server.Shutdown(ctx) // 停止接收新请求，等待现有请求完成
}()

server.ListenAndServe()
```

配合 Pod 的 `preStop` hook：

```yaml
lifecycle:
  preStop:
    exec:
      command: ["sleep", "5"]  # 给 LB/Ingress 5 秒时间摘除流量
```

`terminationGracePeriodSeconds` 必须满足：`preStop 时间 + 应用程序 shutdown 时间 < terminationGracePeriodSeconds`。如果这个不等式不成立，Pod 会被 SIGKILL 强杀。

---

## 第五部分：命令式 vs 声明式

K8s 有两种操作模式：

```bash
# 命令式（Imperative）：告诉 K8s "做什么"
kubectl run nginx --image=nginx
kubectl scale deployment/app --replicas=5
kubectl expose deployment/app --port=80 --target-port=8080

# 声明式（Declarative）：告诉 K8s "期望状态是什么"
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -k ./kustomize/overlays/production
```

命令式适合快速实验和调试。声明式适合正式环境：你的 YAML 文件就是基础设施文档，Git 仓库就是配置的版本历史。

生产环境的标准做法：

```text
项目仓库/
├── k8s/
│   ├── base/                    # 基础配置
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   └── kustomization.yaml
│   └── overlays/
│       ├── staging/             # Staging 覆盖
│       │   ├── deployment-patch.yaml
│       │   └── kustomization.yaml
│       └── production/          # Prod 覆盖
│           ├── deployment-patch.yaml
│           ├── ingress-patch.yaml
│           └── kustomization.yaml
```

用 Kustomize（`kubectl apply -k`）管理多环境的配置覆盖，不同环境共享 base 配置，差异部分用 patch 或 overlay 覆盖。

---

## 第六部分：网络模型

K8s 网络的核心假设（CNI 规范）：

1. 每个 Pod 有唯一的 IP 地址
2. Pod 之间可以**直接**通信（不需要 NAT）
3. Node 上的进程可以和同 Node 上的 Pod 通信

实现这个模型的是 CNI 插件（Calico、Flannel、Cilium 等）。它们为每个 Pod 创建网络接口、分配 IP、配置路由。

```text
Node A: 10.0.1.0/24              Node B: 10.0.2.0/24
┌──────────────────┐              ┌──────────────────┐
│ Pod X: 10.0.1.10 │              │ Pod Y: 10.0.2.20 │
└────────┬─────────┘              └────────┬─────────┘
         │ veth pair                       │ veth pair
         │                                 │
    ┌────┴────┐                       ┌────┴────┐
    │ bridge  │ (cni0)                │ bridge  │ (cni0)
    └────┬────┘                       └────┬────┘
         │                                 │
    ┌────┴────┐  route: 10.0.2.0/24   ┌───┴──────┐
    │ eth0    │◄─────────────────────►│ eth0     │
    │ Node A  │   via Node B          │ Node B   │
    └─────────┘                       └──────────┘
```

Pod X (10.0.1.10) 访问 Pod Y (10.0.2.20)：
1. 包从 Pod X → veth pair → Node A 的 bridge cni0
2. Node A 查路由表：`10.0.2.0/24 via Node B` → 把包通过 Node A eth0 发到 Node B
3. Node B 收到包 → 查路由表 → 发现 10.0.2.20 在本地 cni0 → 转发到 Pod Y

不同 CNI 插件的实现差异：
- **Flannel**：用 VXLAN 或 host-gw 封装跨 Node 流量
- **Calico**：用 BGP 协议在 Node 间同步路由，纯三层
- **Cilium**：用 eBPF 替代 iptables，性能更好且可观测性强

---

## 第七部分：存储

K8s 的存储模型通过三个抽象解耦：

```text
PersistentVolumeClaim (PVC)  ← 用户申请的存储（我要 10GB 的存储）
PersistentVolume (PV)        ← 管理员提供的存储（这是 NFS 上的 100GB 卷）
StorageClass                 ← 自动创建的模板（按此规格自动创建 PV）
```

```yaml
# PVC — 申请存储
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  accessModes:
  - ReadWriteOnce       # 只能被一个 Node 上的 Pod 以读写方式挂载
  resources:
    requests:
      storage: 10Gi
  storageClassName: ssd # 指定使用哪个 StorageClass
---
# 在 Pod 中使用
spec:
  containers:
  - name: app
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: app-data
```

`accessModes` 的三种模式：

| 模式 | 含义 | 典型后端 |
|------|------|---------|
| ReadWriteOnce (RWO) | 单 Node 读写 | 块存储（云盘、local PV） |
| ReadOnlyMany (ROX) | 多 Node 只读 | NFS |
| ReadWriteMany (RWX) | 多 Node 读写 | NFS、CephFS、GlusterFS |

> ⚠️ `ReadWriteOnce` 指的是**同一个 Node** 上可以有多个 Pod 同时挂载和写入，不是只能有一个 Pod。需要多个 Pod 跨 Node 访问同一卷，必须用 `ReadWriteMany`。

---

## 第八部分：调试清单

当线上 Pod 出问题时，按以下顺序排查：

```bash
# 1. 看 Pod 总体状态
kubectl get pods -o wide

# 2. 看 Events（最近发生了什么）
kubectl describe pod <name> | tail -30

# 3. 看日志
kubectl logs <name> --tail=200
kubectl logs <name> --previous  # CrashLoopBackOff 时必查

# 4. 看 Pod 资源使用
kubectl top pod <name>

# 5. 进入容器检查
kubectl exec -it <name> -- /bin/sh
# 进去后检查: 进程是否在跑 (ps aux)、端口是否监听 (netstat -tlnp)、
# 配置文件是否正确 (cat /etc/app/...)、依赖服务是否可达 (nc -zv db 5432)

# 6. 检查 Node 状态（如果 Pod 一直是 Pending）
kubectl describe node <node-name>
kubectl top node

# 7. 检查网络
kubectl run debug --rm -it --image=nicolaka/netshoot -- /bin/bash
# 在 netshoot Pod 里: curl svc-name.namespace:port, nslookup svc-name, tcpdump 等

# 8. 检查 DNS
kubectl run dns-debug --rm -it --image=busybox -- nslookup kubernetes.default
```

---

K8s 的概念很多，但核心思路是统一的：声明式配置 + 控制器和解循环 + API Server 作为唯一通信枢纽。掌握了这个思路，每个新资源（StatefulSet、DaemonSet、Job、CronJob、HPAs、NetworkPolicy）都可以通过 `kubectl explain` 和阅读 API 文档来理解，不需要死记硬背。
