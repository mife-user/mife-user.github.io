---
title: 'C++ 数据结构完全指南：从新手到上手'
date: 2026-06-24T15:00:00+08:00
draft: false
tags: ["C++", "数据结构", "数组", "链表", "栈", "队列", "二叉树", "哈希表", "堆", "图", "STL"]
---

## 前言：为什么学数据结构？

打个比方：你要搬家，东西散落一地。如果你**随手塞进箱子**，到了新家想找一把剪刀，得把所有箱子翻个遍。但如果你**按类别装箱**——厨具一箱、衣物一箱、书籍一箱——到了新家，你直奔"厨具箱"就能找到剪刀。

**数据结构就是数据的"装箱方式"。** 同样的数据，用不同的结构组织，查找、插入、删除的效率可能差出几百倍。

> 本文面向 C++ 新手。我会带你从零开始，把每种数据结构**画出来、讲明白、写成能跑的代码**。每个结构都配完整 C++ 代码，你复制到本地就能编译运行。

读完本文你将能够：

- 理解 8 种核心数据结构的原理和适用场景
- 手写数组、链表、栈、队列、二叉树、哈希表、堆、图的 C++ 实现
- 学会用 C++ STL 标准库中的数据结构，快速应用到项目中
- 掌握每种结构的**时间复杂度**，能判断"为什么我的程序这么慢"
- 看懂面试中常见的数据结构问题

---

## 一、核心概念：数据结构的两个维度

在学习具体结构之前，先理解两个贯穿全文的概念：

### 1.1 逻辑结构 vs 物理结构

| | 逻辑结构 | 物理结构 |
|---|---|---|
| **含义** | 数据之间**看上去**是什么关系 | 数据在**内存中**怎么存放 |
| **举例** | "排队"是一个线性结构 | 内存可以是连续的一排，也可以是散落的 |
| **类比** | 地铁线路图（逻辑上各站有先后） | 实际地理坐标（物理上各站间距不同） |

**同一个逻辑结构，可以有不同的物理实现。** 比如"列表"这种逻辑结构，物理上既可以用**数组**（连续内存）实现，也可以用**链表**（散落内存）实现。

### 1.2 判断数据结构好坏的标尺：时间复杂度

所有数据结构的操作都可以归结为四种：**增、删、查、改**。我们用**大 O 符号**来衡量速度：

| 复杂度 | 通俗说法 | 100 万数据 |
|--------|----------|------------|
| O(1) | 瞬间完成 | 1 步 |
| O(log n) | 非常快 | ~20 步 |
| O(n) | 线性，还行 | 100 万步 |
| O(n log n) | 中等偏慢 | ~2000 万步 |
| O(n²) | 很慢 | 1 万亿步 |

> 关键直觉：O(n) 意味着数据量翻 10 倍，操作时间也翻 10 倍。O(log n) 意味着数据量翻 1000 倍，操作时间只多几十步。

---

## 二、数组（Array）—— 一切的基础

### 2.1 是什么

内存中**连续**的一排位置，每个位置放一个数据。就像电影院的一排座位，1 号座、2 号座、3 号座紧挨着。

```
内存地址： 1000  1004  1008  1012  1016
           ↓     ↓     ↓     ↓     ↓
数据：    [ 5 ] [ 3 ] [ 8 ] [ 1 ] [ 7 ]
索引：      0     1     2     3     4
```

每个元素占用固定字节（比如 `int` 占 4 字节）。知道第 0 个元素的地址，就能**瞬间算出**任意元素的地址：

```
第 i 个元素的地址 = 起始地址 + i × 每个元素的字节数
第 3 个元素的地址 = 1000 + 3 × 4 = 1012  ← 一次乘法，O(1) 时间
```

### 2.2 核心操作

```cpp
#include <iostream>
using namespace std;

// ---------- 手动实现动态数组 ----------
class MyArray {
private:
    int* data;      // 指向堆上分配的内存
    int capacity;   // 当前最多能放几个元素
    int length;     // 当前实际放了几个元素

public:
    // 构造函数：初始分配 4 个位置
    MyArray() {
        capacity = 4;
        length = 0;
        data = new int[capacity];
    }

    // 析构函数：归还内存
    ~MyArray() {
        delete[] data;
    }

    // ---------- 1. 随机访问 O(1) ----------
    int get(int index) {
        if (index < 0 || index >= length) {
            cout << "越界！index=" << index << ", 当前长度=" << length << endl;
            return -1;
        }
        return data[index];  // 一次乘法 + 一次内存读取
    }

    // ---------- 2. 末尾追加 O(1) ----------
    void push_back(int value) {
        if (length >= capacity) {
            expand();  // 满了就扩容
        }
        data[length] = value;
        length++;
    }

    // ---------- 3. 中间插入 O(n) ----------
    void insert(int index, int value) {
        if (index < 0 || index > length) {
            cout << "插入位置越界！" << endl;
            return;
        }
        if (length >= capacity) {
            expand();
        }
        // 从后往前，每个元素后移一位
        for (int i = length; i > index; i--) {
            data[i] = data[i - 1];
        }
        data[index] = value;
        length++;
    }

    // ---------- 4. 中间删除 O(n) ----------
    void remove(int index) {
        if (index < 0 || index >= length) {
            cout << "删除位置越界！" << endl;
            return;
        }
        // 从删除位置开始，每个元素前移一位
        for (int i = index; i < length - 1; i++) {
            data[i] = data[i + 1];
        }
        length--;
    }

    // ---------- 扩容（实现动态增长）----------
    void expand() {
        int newCapacity = capacity * 2;
        int* newData = new int[newCapacity];
        // 把旧数据拷贝到新空间
        for (int i = 0; i < length; i++) {
            newData[i] = data[i];
        }
        delete[] data;
        data = newData;
        capacity = newCapacity;
        cout << "   [扩容] 容量: " << capacity / 2
             << " → " << capacity << endl;
    }

    // ---------- 查找 O(n) ----------
    int find(int value) {
        for (int i = 0; i < length; i++) {
            if (data[i] == value) return i;
        }
        return -1;  // 没找到
    }

    void print() {
        cout << "[";
        for (int i = 0; i < length; i++) {
            cout << data[i];
            if (i < length - 1) cout << ", ";
        }
        cout << "] 容量=" << capacity << " 长度=" << length << endl;
    }
};

// ---------- STL 中的数组 ----------
#include <vector>
#include <array>

void stl_array_demo() {
    cout << "\n--- STL 数组 ---" << endl;

    // 静态数组：编译时确定大小，栈上分配
    int raw[5] = {1, 2, 3, 4, 5};
    cout << "原始数组 raw[2] = " << raw[2] << endl;

    // std::array：封装版静态数组，带边界检查
    array<int, 5> arr = {1, 2, 3, 4, 5};
    cout << "std::array arr[2] = " << arr[2] << endl;
    cout << "std::array 大小 = " << arr.size() << endl;

    // std::vector：动态数组
    vector<int> vec;
    vec.push_back(10);
    vec.push_back(20);
    vec.push_back(30);
    cout << "vector: ";
    for (int v : vec) cout << v << " ";
    cout << endl;
    cout << "vector 大小 = " << vec.size() << endl;
    cout << "vector 容量 = " << vec.capacity() << endl;

    // 用 at() 代替 []，越界会抛异常而不是默默出错
    try {
        cout << "vec.at(5) = " << vec.at(5) << endl;
    } catch (const out_of_range& e) {
        cout << "捕获异常: " << e.what() << endl;
    }
}

int main() {
    cout << "========== 手动实现动态数组 ==========" << endl;
    MyArray arr;
    arr.print();

    arr.push_back(10);
    arr.push_back(20);
    arr.push_back(30);
    arr.push_back(40);
    arr.print();

    arr.push_back(50);  // 触发扩容
    arr.print();

    arr.insert(2, 99);  // 索引 2 处插入 99
    cout << "插入后: ";
    arr.print();

    arr.remove(1);      // 删除索引 1
    cout << "删除后: ";
    arr.print();

    cout << "查找 99 的位置: " << arr.find(99) << endl;
    cout << "查找 999 的位置: " << arr.find(999) << endl;

    stl_array_demo();
    return 0;
}
```

### 2.3 性能总结

| 操作 | 时间 | 原因 |
|------|------|------|
| 按下标访问 a[i] | O(1) | 公式 `起始地址 + i × 元素大小` |
| 末尾插入 push_back | **均摊** O(1) | 偶尔扩容，但平均下来很快 |
| 中间插入 | O(n) | 插入点后面所有元素都得后移 |
| 中间删除 | O(n) | 删除点后面所有元素都得前移 |
| 查找某个值 | O(n) | 一个个比较，最坏找到末尾 |

### 2.4 一句话决策

> **需要频繁按下标访问 → 用数组。需要频繁从中间插入删除 → 用链表。**

---

## 三、链表（Linked List）—— 插入删除的王者

### 3.1 是什么

数据散落在内存各处，每个数据节点里存一个**指针**指向下一个节点。就像寻宝游戏——每找到一个线索，上面写着下一个线索的地址。

```
数组（内存连续）：                   链表（内存散落）：
[10] → [20] → [30]                  [10|地址B]       [30|地址D]
地址连续：1000, 1004, 1008          地址A: 0x5000  → 地址C: 0x7000
                                                     ↓
                                    [20|地址C]       [40|null]
                                    地址B: 0x6000    地址D: 0x8000
```

### 3.2 单向链表完整实现

```cpp
#include <iostream>
using namespace std;

// ---------- 节点结构 ----------
struct Node {
    int data;       // 存的数据
    Node* next;     // 指向下一个节点的指针

    Node(int val) : data(val), next(nullptr) {}
};

// ---------- 单向链表 ----------
class LinkedList {
private:
    Node* head;     // 头节点指针（链表的入口）

public:
    LinkedList() : head(nullptr) {}

    ~LinkedList() {
        // 销毁所有节点，避免内存泄漏
        Node* current = head;
        while (current != nullptr) {
            Node* next = current->next;
            delete current;
            current = next;
        }
    }

    // ---------- 1. 头插 O(1) ----------
    void push_front(int value) {
        Node* newNode = new Node(value);
        newNode->next = head;   // 新节点指向原来的头
        head = newNode;         // 头指针改为新节点
    }

    // ---------- 2. 尾插 O(n) ----------
    void push_back(int value) {
        Node* newNode = new Node(value);

        if (head == nullptr) {
            head = newNode;
            return;
        }

        // 走到最后一个节点
        Node* current = head;
        while (current->next != nullptr) {
            current = current->next;
        }
        current->next = newNode;
    }

    // ---------- 3. 任意位置插入 O(n) ----------
    // 在索引 index 处插入（索引从 0 开始）
    void insert(int index, int value) {
        if (index == 0) {
            push_front(value);
            return;
        }

        Node* current = head;
        // 走到 index-1 的位置
        for (int i = 0; i < index - 1 && current != nullptr; i++) {
            current = current->next;
        }

        if (current == nullptr) {
            cout << "插入位置越界！" << endl;
            return;
        }

        Node* newNode = new Node(value);
        newNode->next = current->next;  // 新节点先接上后面
        current->next = newNode;        // 前面的节点再接上新节点
    }

    // ---------- 4. 删除 O(n) ----------
    void remove(int value) {
        if (head == nullptr) return;

        // 特殊情况：删除头节点
        if (head->data == value) {
            Node* temp = head;
            head = head->next;
            delete temp;
            return;
        }

        // 找到目标节点的前一个节点
        Node* current = head;
        while (current->next != nullptr && current->next->data != value) {
            current = current->next;
        }

        if (current->next == nullptr) {
            cout << "未找到值 " << value << endl;
            return;
        }

        Node* temp = current->next;
        current->next = temp->next;  // 跳过要删除的节点
        delete temp;
    }

    // ---------- 5. 查找 O(n) ----------
    bool contains(int value) {
        Node* current = head;
        while (current != nullptr) {
            if (current->data == value) return true;
            current = current->next;
        }
        return false;
    }

    // ---------- 6. 反转链表 O(n)（经典面试题）----------
    void reverse() {
        Node* prev = nullptr;
        Node* current = head;
        Node* next = nullptr;

        while (current != nullptr) {
            next = current->next;     // 记住下一个
            current->next = prev;     // 当前节点转向
            prev = current;           // prev 前进
            current = next;           // current 前进
        }
        head = prev;  // 原来的尾巴变成新的头
    }

    void print() {
        Node* current = head;
        while (current != nullptr) {
            cout << current->data;
            if (current->next != nullptr) cout << " → ";
            current = current->next;
        }
        cout << endl;
    }
};

// ---------- 双向链表（带尾指针，尾插 O(1)）----------
struct DNode {
    int data;
    DNode* prev;
    DNode* next;
    DNode(int val) : data(val), prev(nullptr), next(nullptr) {}
};

class DoublyLinkedList {
private:
    DNode* head;
    DNode* tail;  // 尾指针，尾插变 O(1)

public:
    DoublyLinkedList() : head(nullptr), tail(nullptr) {}

    void push_back(int value) {
        DNode* newNode = new DNode(value);
        if (tail == nullptr) {
            head = tail = newNode;
        } else {
            tail->next = newNode;
            newNode->prev = tail;
            tail = newNode;
        }
    }

    void push_front(int value) {
        DNode* newNode = new DNode(value);
        if (head == nullptr) {
            head = tail = newNode;
        } else {
            newNode->next = head;
            head->prev = newNode;
            head = newNode;
        }
    }

    void print_forward() {
        DNode* cur = head;
        while (cur) {
            cout << cur->data;
            if (cur->next) cout << " ⇄ ";
            cur = cur->next;
        }
        cout << endl;
    }

    // 反向遍历（单向链表做不到这个）
    void print_backward() {
        DNode* cur = tail;
        while (cur) {
            cout << cur->data;
            if (cur->prev) cout << " ⇄ ";
            cur = cur->prev;
        }
        cout << endl;
    }
};

// ---------- STL 中的链表 ----------
#include <list>
#include <forward_list>

void stl_list_demo() {
    cout << "\n--- STL 链表 ---" << endl;

    // std::list：双向链表
    list<int> lst;
    lst.push_back(100);
    lst.push_front(200);
    lst.push_back(300);
    cout << "list: ";
    for (int v : lst) cout << v << " ";
    cout << endl;

    // 在任意位置插入非常快
    auto it = lst.begin();
    it++;  // 指向第二个元素
    lst.insert(it, 999);
    cout << "插入后: ";
    for (int v : lst) cout << v << " ";
    cout << endl;

    // forward_list：单向链表（省内存）
    forward_list<int> flist = {1, 2, 3, 4, 5};
    cout << "forward_list: ";
    for (int v : flist) cout << v << " ";
    cout << endl;
}

int main() {
    cout << "========== 单向链表 ==========" << endl;
    LinkedList ll;

    ll.push_front(30);
    ll.push_front(20);
    ll.push_front(10);
    cout << "头插三次: "; ll.print();

    ll.push_back(40);
    ll.push_back(50);
    cout << "尾插两次: "; ll.print();

    ll.insert(2, 99);
    cout << "索引2插入99: "; ll.print();

    ll.remove(30);
    cout << "删除30: "; ll.print();

    cout << "查找99: " << (ll.contains(99) ? "存在" : "不存在") << endl;
    cout << "查找999: " << (ll.contains(999) ? "存在" : "不存在") << endl;

    ll.reverse();
    cout << "反转后: "; ll.print();

    cout << "\n========== 双向链表（反向遍历）==========" << endl;
    DoublyLinkedList dll;
    dll.push_back(1);
    dll.push_back(2);
    dll.push_back(3);
    cout << "正向: "; dll.print_forward();
    cout << "反向: "; dll.print_backward();

    stl_list_demo();
    return 0;
}
```

### 3.3 数组 vs 链表终极对比

| 场景 | 数组 | 链表 |
|------|------|------|
| 随机访问 a[i] | **O(1)** 极快 | O(n) 要从头走 |
| 尾部插入 | **O(1)** | O(n) 单向 / **O(1)** 双向带尾指针 |
| 头部插入 | O(n) 全后移 | **O(1)** |
| 中间插入/删除 | O(n) 元素移动 | **O(1)** 改指针即可（假设已定位） |
| 内存占用 | 紧凑，无额外开销 | 每个节点多存一个指针 |
| 缓存友好 | **好**——连续内存一次加载 | 差——散落各处 |

### 3.4 一句话决策

> **数组 = 读取快，改结构慢。链表 = 改结构快，读取慢。选哪个看你的程序更多在"读"还是"改"。**

---

## 四、栈（Stack）—— 后进先出

### 4.1 是什么

只能从**一端**插入和删除的线性结构。就像一摞盘子——你只能从最上面拿、也只能往最上面放。

```
push(1)  push(2)  push(3)  pop()→3  top()→2
↓        ↓        ↓        ↓         ↓
[1]     [2]      [3]      [2]       [2]
         [1]      [2]      [1]       [1]
                  [1]
```

> 核心规则：**Last In, First Out（LIFO）**——最后放进去的，最先拿出来。

### 4.2 完整实现（基于数组 + 基于链表）

```cpp
#include <iostream>
using namespace std;

// ========== 基于数组的栈 ==========
class ArrayStack {
private:
    int* data;
    int capacity;
    int topIndex;  // 栈顶索引，-1 表示空

public:
    ArrayStack(int cap = 100) {
        capacity = cap;
        data = new int[capacity];
        topIndex = -1;
    }

    ~ArrayStack() { delete[] data; }

    // 压栈 O(1)
    void push(int value) {
        if (topIndex >= capacity - 1) {
            cout << "栈满了！无法压入 " << value << endl;
            return;
        }
        data[++topIndex] = value;
    }

    // 弹栈 O(1)
    int pop() {
        if (topIndex < 0) {
            cout << "栈空了！" << endl;
            return -1;
        }
        return data[topIndex--];
    }

    // 查看栈顶但不取出 O(1)
    int top() {
        if (topIndex < 0) {
            cout << "栈空了！" << endl;
            return -1;
        }
        return data[topIndex];
    }

    bool empty() { return topIndex == -1; }
    int size() { return topIndex + 1; }
};

// ========== 基于链表的栈 ==========
struct StackNode {
    int data;
    StackNode* next;
    StackNode(int v) : data(v), next(nullptr) {}
};

class LinkedStack {
private:
    StackNode* topNode;  // 栈顶就是链表的头

public:
    LinkedStack() : topNode(nullptr) {}

    ~LinkedStack() {
        while (topNode != nullptr) {
            StackNode* temp = topNode;
            topNode = topNode->next;
            delete temp;
        }
    }

    void push(int value) {
        StackNode* newNode = new StackNode(value);
        newNode->next = topNode;
        topNode = newNode;
    }

    int pop() {
        if (topNode == nullptr) {
            cout << "栈空了！" << endl;
            return -1;
        }
        StackNode* temp = topNode;
        int value = temp->data;
        topNode = topNode->next;
        delete temp;
        return value;
    }

    int top() {
        if (topNode == nullptr) return -1;
        return topNode->data;
    }

    bool empty() { return topNode == nullptr; }
};

// ========== 经典应用：括号匹配 ==========
#include <string>
bool isBalanced(const string& expr) {
    LinkedStack stk;
    for (char ch : expr) {
        if (ch == '(' || ch == '[' || ch == '{') {
            stk.push(ch);
        } else if (ch == ')' || ch == ']' || ch == '}') {
            if (stk.empty()) return false;  // 多了右括号
            char top = stk.pop();
            if ((ch == ')' && top != '(') ||
                (ch == ']' && top != '[') ||
                (ch == '}' && top != '{')) {
                return false;  // 不匹配
            }
        }
    }
    return stk.empty();  // 栈空了才算完全匹配
}

// ========== STL 的栈 ==========
#include <stack>
void stl_stack_demo() {
    cout << "\n--- STL stack ---" << endl;
    stack<int> stk;
    stk.push(1);
    stk.push(2);
    stk.push(3);
    cout << "栈顶: " << stk.top() << endl;
    stk.pop();
    cout << "弹出后栈顶: " << stk.top() << endl;
    cout << "大小: " << stk.size() << endl;
}

int main() {
    cout << "========== 数组栈 ==========" << endl;
    ArrayStack arrStk(5);
    arrStk.push(10); arrStk.push(20); arrStk.push(30);
    cout << "栈顶: " << arrStk.top() << endl;
    cout << "弹出: " << arrStk.pop() << endl;
    cout << "弹出: " << arrStk.pop() << endl;
    cout << "栈大小: " << arrStk.size() << endl;
    cout << "栈空了? " << (arrStk.empty() ? "是" : "否") << endl;

    cout << "\n========== 括号匹配测试 ==========" << endl;
    cout << "([]){} : " << (isBalanced("([]){}") ? "匹配 ✓" : "不匹配 ✗") << endl;
    cout << "([)]   : " << (isBalanced("([)]") ? "匹配 ✓" : "不匹配 ✗") << endl;
    cout << "((())  : " << (isBalanced("((())") ? "匹配 ✓" : "不匹配 ✗") << endl;

    stl_stack_demo();
    return 0;
}
```

### 4.3 栈的经典应用

| 场景 | 原理 |
|------|------|
| 括号匹配 | 遇左括号入栈，遇右括号弹出匹配 |
| 浏览器的"后退" | 每访问一页入栈，点后退弹出 |
| 函数调用 | 每调用一个函数入栈，返回时弹出（递归太深会"栈溢出"） |
| 撤销（Ctrl+Z） | 每次操作入栈，撤销时弹出 |
| 表达式求值 | 运算符栈 + 操作数栈 |

---

## 五、队列（Queue）—— 先进先出

### 5.1 是什么

只能从**队尾**插入、从**队头**删除的线性结构。就像排队买票——先来的先服务。

```
enqueue(1)  enqueue(2)  enqueue(3)  dequeue()→1  front()→2
队尾←1      队尾←2      队尾←3      队头出队      队头是2
队头=1      队头=1      队头=1      队头=2        队头=2
```

> 核心规则：**First In, First Out（FIFO）**——先进来的，先出去。

### 5.2 循环队列（节省空间的巧妙设计）

普通队列用数组实现有个问题：队头出队后，前面的空间就浪费了。**循环队列**把数组当成一个环，队头和队尾绕回来继续用。

```
想象一个长度为 5 的环：
        [0]
    [4]     [1]
    [3]     [2]

rear=2, front=1 → 环形队列中有 [1], [2] 两个元素，还剩 3 个空位
```

```cpp
#include <iostream>
using namespace std;

// ========== 循环队列 ==========
class CircularQueue {
private:
    int* data;
    int capacity;
    int front;  // 队头索引
    int rear;   // 队尾索引（指向下一个空位）
    int count;  // 当前元素数

public:
    CircularQueue(int cap = 5) {
        capacity = cap;
        data = new int[capacity];
        front = 0;
        rear = 0;
        count = 0;
    }

    ~CircularQueue() { delete[] data; }

    bool empty() { return count == 0; }
    bool full() { return count == capacity; }

    // 入队 O(1)
    void enqueue(int value) {
        if (full()) {
            cout << "队列满了！无法入队 " << value << endl;
            return;
        }
        data[rear] = value;
        rear = (rear + 1) % capacity;  // 取模实现循环
        count++;
    }

    // 出队 O(1)
    int dequeue() {
        if (empty()) {
            cout << "队列空了！" << endl;
            return -1;
        }
        int value = data[front];
        front = (front + 1) % capacity;
        count--;
        return value;
    }

    int getFront() {
        if (empty()) return -1;
        return data[front];
    }

    int size() { return count; }

    void print() {
        if (empty()) {
            cout << "[空队列]" << endl;
            return;
        }
        cout << "队头→ [";
        for (int i = 0; i < count; i++) {
            int idx = (front + i) % capacity;
            cout << data[idx];
            if (i < count - 1) cout << ", ";
        }
        cout << "] ←队尾 (front=" << front << ", rear=" << rear
             << ")" << endl;
    }
};

// ========== 链式队列（基于链表，不会满）==========
struct QNode {
    int data;
    QNode* next;
    QNode(int v) : data(v), next(nullptr) {}
};

class LinkedQueue {
private:
    QNode* frontNode;  // 队头
    QNode* rearNode;   // 队尾

public:
    LinkedQueue() : frontNode(nullptr), rearNode(nullptr) {}

    ~LinkedQueue() {
        while (frontNode != nullptr) {
            QNode* temp = frontNode;
            frontNode = frontNode->next;
            delete temp;
        }
    }

    void enqueue(int value) {
        QNode* newNode = new QNode(value);
        if (rearNode == nullptr) {
            frontNode = rearNode = newNode;
        } else {
            rearNode->next = newNode;
            rearNode = newNode;
        }
    }

    int dequeue() {
        if (frontNode == nullptr) {
            cout << "队列空了！" << endl;
            return -1;
        }
        QNode* temp = frontNode;
        int value = temp->data;
        frontNode = frontNode->next;
        if (frontNode == nullptr) rearNode = nullptr;
        delete temp;
        return value;
    }

    int front() {
        return frontNode ? frontNode->data : -1;
    }

    bool empty() { return frontNode == nullptr; }
};

// ========== STL 的队列 ==========
#include <queue>
#include <deque>
void stl_queue_demo() {
    cout << "\n--- STL queue ---" << endl;

    queue<int> q;
    q.push(1); q.push(2); q.push(3);
    cout << "队头: " << q.front() << " 队尾: " << q.back() << endl;
    q.pop();
    cout << "出队后队头: " << q.front() << endl;

    // deque：双端队列，两端都能进出
    deque<int> dq;
    dq.push_back(1);
    dq.push_front(2);
    dq.push_back(3);
    cout << "deque: ";
    for (int v : dq) cout << v << " ";
    cout << endl;

    // 优先队列（后面堆的章节详细讲）
    priority_queue<int> pq;
    pq.push(30); pq.push(10); pq.push(50);
    cout << "优先队列最大值: " << pq.top() << endl;
}

int main() {
    cout << "========== 循环队列 ==========" << endl;
    CircularQueue cq(5);
    cq.enqueue(10); cq.enqueue(20); cq.enqueue(30);
    cq.print();

    cout << "出队: " << cq.dequeue() << endl;
    cq.print();

    cq.enqueue(40); cq.enqueue(50); cq.enqueue(60);
    cq.print();  // 60 触发"队列满了"

    cout << "\n========== 链式队列 ==========" << endl;
    LinkedQueue lq;
    lq.enqueue(100); lq.enqueue(200); lq.enqueue(300);
    cout << "出队: " << lq.dequeue() << endl;
    cout << "出队: " << lq.dequeue() << endl;

    stl_queue_demo();
    return 0;
}
```

### 5.3 队列的经典应用

| 场景 | 原理 |
|------|------|
| 打印机任务 | 先提交的任务先打印 |
| 消息队列（Kafka/RabbitMQ） | 生产者入队，消费者出队 |
| BFS（广度优先搜索） | 逐层遍历 |
| CPU 任务调度 | 时间片轮转 |
| 线程池任务队列 | 任务排队等待执行 |

---

## 六、哈希表（Hash Table）—— O(1) 的查找魔法

### 6.1 是什么

前面看到的数组按下标访问是 O(1)，但你要先用 O(n) 找到下标。**哈希表直接用一个公式把"键"算出"下标"，跳过了查找这一步。**

```
                    ┌─── 哈希函数 ───┐
键 "张三"  ─────────→  f("张三") = 3  ─────────→  下标 3，直接取值
键 "李四"  ─────────→  f("李四") = 0  ─────────→  下标 0，直接取值
键 "王五"  ─────────→  f("王五") = 3  ─────────→  冲突！张三已经占了 3
                                                      ↓
                                              用链表挂在后面（拉链法）
```

### 6.2 核心问题：哈希冲突

两个不同的键算出同一个下标 → **冲突**。解决办法主要有两种：

```
拉链法（Chaining）：每个桶存一个链表
┌───┐
│ 0 │ → [李四|25]
├───┤
│ 1 │ → [赵六|22] → [孙七|21]
├───┤
│ 2 │ → (空)
├───┤
│ 3 │ → [张三|23] → [王五|24]
└───┘

开放寻址法（Open Addressing）：冲突了就找下一个空位
[0] 李四  [1] 赵六  [2] 孙七  [3] 张三  [4] 王五
                                           ↑
                              王五本来算到 3，但 3 被占了
                              就往后找，找到 4 是空的
```

### 6.3 完整实现（拉链法）

```cpp
#include <iostream>
#include <string>
using namespace std;

// ========== 哈希表节点（拉链法）==========
struct HashNode {
    string key;
    int value;
    HashNode* next;

    HashNode(string k, int v) : key(k), value(v), next(nullptr) {}
};

class HashMap {
private:
    static const int CAPACITY = 10;  // 桶的数量
    HashNode* buckets[CAPACITY];     // 每个桶是一个链表头

    // 哈希函数：把字符串转换成一个 0~CAPACITY-1 的整数
    int hash(const string& key) {
        // 方法：每个字符的 ASCII 码累加，再取模
        // 实际项目会用地更复杂的算法（如 MurmurHash）
        int hashValue = 0;
        for (char ch : key) {
            hashValue += ch;
        }
        return hashValue % CAPACITY;
    }

public:
    HashMap() {
        for (int i = 0; i < CAPACITY; i++) {
            buckets[i] = nullptr;
        }
    }

    ~HashMap() {
        for (int i = 0; i < CAPACITY; i++) {
            HashNode* cur = buckets[i];
            while (cur != nullptr) {
                HashNode* temp = cur;
                cur = cur->next;
                delete temp;
            }
        }
    }

    // ---------- 插入 / 更新 O(1) 均摊 ----------
    void put(const string& key, int value) {
        int index = hash(key);

        // 先检查这个 key 是否已经存在
        HashNode* cur = buckets[index];
        while (cur != nullptr) {
            if (cur->key == key) {
                cur->value = value;  // 更新
                return;
            }
            cur = cur->next;
        }

        // key 不存在，插入到链表头部（头插法最快）
        HashNode* newNode = new HashNode(key, value);
        newNode->next = buckets[index];
        buckets[index] = newNode;
    }

    // ---------- 查找 O(1) 均摊 ----------
    // 返回 -1 表示不存在
    int get(const string& key) {
        int index = hash(key);

        HashNode* cur = buckets[index];
        while (cur != nullptr) {
            if (cur->key == key) {
                return cur->value;
            }
            cur = cur->next;
        }
        return -1;  // 没找到
    }

    // ---------- 删除 O(1) 均摊 ----------
    void remove(const string& key) {
        int index = hash(key);
        HashNode* cur = buckets[index];
        HashNode* prev = nullptr;

        while (cur != nullptr) {
            if (cur->key == key) {
                if (prev == nullptr) {
                    buckets[index] = cur->next;  // 删的是第一个
                } else {
                    prev->next = cur->next;      // 跳过 cur
                }
                delete cur;
                cout << "删除: " << key << endl;
                return;
            }
            prev = cur;
            cur = cur->next;
        }
        cout << "未找到: " << key << endl;
    }

    void print() {
        cout << "\n========== 哈希表 ==========" << endl;
        for (int i = 0; i < CAPACITY; i++) {
            cout << "桶[" << i << "]: ";
            HashNode* cur = buckets[i];
            if (cur == nullptr) {
                cout << "(空)";
            }
            while (cur != nullptr) {
                cout << "{" << cur->key << ": " << cur->value << "}";
                if (cur->next) cout << " → ";
                cur = cur->next;
            }
            cout << endl;
        }
    }
};

// ========== STL 中的哈希表 ==========
#include <unordered_map>
#include <unordered_set>
void stl_hash_demo() {
    cout << "\n--- STL 哈希表 ---" << endl;

    // unordered_map：键值对
    unordered_map<string, int> umap;
    umap["apple"] = 5;
    umap["banana"] = 3;
    umap["orange"] = 8;
    cout << "apple: " << umap["apple"] << endl;

    // 安全的查找方式
    auto it = umap.find("grape");
    if (it != umap.end()) {
        cout << "grape: " << it->second << endl;
    } else {
        cout << "grape 不存在" << endl;
    }

    // map（红黑树，有序）vs unordered_map（哈希表，更快）
    /*
    | 特性         | map              | unordered_map    |
    |-------------|------------------|------------------|
    | 底层实现     | 红黑树（有序）    | 哈希表（无序）     |
    | 插入/查找/删除| O(log n)         | O(1) 均摊        |
    | 遍历顺序     | 按键升序          | 随意              |
    | 内存占用     | 较小              | 较大              |
    */

    // unordered_set：只存键，不存值（去重用）
    unordered_set<int> uset = {1, 2, 3, 2, 5, 3};
    cout << "unordered_set (自动去重): ";
    for (int v : uset) cout << v << " ";
    cout << endl;
}

int main() {
    HashMap map;
    map.put("张三", 23);
    map.put("李四", 25);
    map.put("王五", 24);
    map.put("赵六", 22);
    map.put("孙七", 21);
    map.print();

    cout << "\n张三的年龄: " << map.get("张三") << endl;
    cout << "王五的年龄: " << map.get("王五") << endl;
    cout << "不存在的马八: " << map.get("马八") << endl;

    map.put("张三", 30);  // 更新张三
    cout << "更新后张三: " << map.get("张三") << endl;

    map.remove("李四");
    map.print();

    stl_hash_demo();
    return 0;
}
```

### 6.4 哈希表的灵魂：好的哈希函数

一个好的哈希函数要做到两点：

1. **快** —— O(1) 算完，不能比遍历还慢
2. **散** —— 把键均匀撒到各个桶，避免热点桶

```cpp
// 差的哈希函数：所有以 'a' 开头的键都掉进同一个桶
int badHash(const string& key) {
    return key[0] % CAPACITY;
}

// 好的哈希函数：每个字符都参与计算
int goodHash(const string& key) {
    int h = 0;
    for (char ch : key) {
        h = (h * 31 + ch) % CAPACITY;  // 31 是质数，减少规律性冲突
    }
    return h;
}
```

---

## 七、二叉树（Binary Tree）—— 层次关系的表达

### 7.1 是什么

每个节点最多有两个子节点（左子和右子）。就像家族族谱——爷爷下面有爸爸和叔叔，爸爸下面有你。

```
        爷爷 (50)
        /      \
    爸爸(30)   叔叔(70)
    /    \      /   \
 你(20) 姐(40) 堂兄(60) 堂弟(80)
       ↖ 这种叫"二叉搜索树"：左子<父<右子
```

### 7.2 为什么是二叉树

二叉搜索树（BST）有一条铁律：**左子树所有节点 < 根节点 < 右子树所有节点**。这条铁律让查找变成 O(log n)：

```
找 60：
从根(50)开始 → 60>50，走右边(70) → 60<70，走左边(60) → 找到了！
                               50
                              /  \
                            30    70
                           /  \  /  \
                         20  40 60  80

查找路径：50 → 70 → 60，3 步找到（总共 7 个节点，查找深度 = log₂7 ≈ 3）
```

### 7.3 完整实现

```cpp
#include <iostream>
#include <queue>
using namespace std;

struct TreeNode {
    int data;
    TreeNode* left;
    TreeNode* right;

    TreeNode(int val) : data(val), left(nullptr), right(nullptr) {}
};

class BinarySearchTree {
private:
    TreeNode* root;

    // ---------- 递归插入 ----------
    TreeNode* insertHelper(TreeNode* node, int value) {
        // 找到空位，创建新节点
        if (node == nullptr) {
            return new TreeNode(value);
        }
        // 比当前节点小 → 去左边
        // 比当前节点大 → 去右边
        if (value < node->data) {
            node->left = insertHelper(node->left, value);
        } else if (value > node->data) {
            node->right = insertHelper(node->right, value);
        }
        // value == node->data：BST 不允许重复，直接忽略
        return node;
    }

    // ---------- 递归查找 ----------
    bool searchHelper(TreeNode* node, int value) {
        if (node == nullptr) return false;
        if (value == node->data) return true;
        if (value < node->data)
            return searchHelper(node->left, value);
        else
            return searchHelper(node->right, value);
    }

    // ---------- 找最小值（最左边的节点）----------
    TreeNode* findMin(TreeNode* node) {
        while (node->left != nullptr) {
            node = node->left;
        }
        return node;
    }

    // ---------- 递归删除 ----------
    TreeNode* removeHelper(TreeNode* node, int value) {
        if (node == nullptr) return nullptr;

        if (value < node->data) {
            node->left = removeHelper(node->left, value);
        } else if (value > node->data) {
            node->right = removeHelper(node->right, value);
        } else {
            // 找到了！分三种情况：

            // 情况1：没有左子 → 直接用右子替换
            if (node->left == nullptr) {
                TreeNode* temp = node->right;
                delete node;
                return temp;
            }
            // 情况2：没有右子 → 直接用左子替换
            if (node->right == nullptr) {
                TreeNode* temp = node->left;
                delete node;
                return temp;
            }
            // 情况3：左右都有 → 用右子树的最小节点替换
            TreeNode* successor = findMin(node->right);
            node->data = successor->data;
            node->right = removeHelper(node->right, successor->data);
        }
        return node;
    }

    // ---------- 中序遍历（左 → 根 → 右）：BST 中序遍历 = 升序排列 ----------
    void inorderHelper(TreeNode* node) {
        if (node == nullptr) return;
        inorderHelper(node->left);
        cout << node->data << " ";
        inorderHelper(node->right);
    }

    // ---------- 前序遍历（根 → 左 → 右）：先访问根 ----------
    void preorderHelper(TreeNode* node) {
        if (node == nullptr) return;
        cout << node->data << " ";
        preorderHelper(node->left);
        preorderHelper(node->right);
    }

    // ---------- 后序遍历（左 → 右 → 根）：最后访问根（用于删除整棵树）----------
    void postorderHelper(TreeNode* node) {
        if (node == nullptr) return;
        postorderHelper(node->left);
        postorderHelper(node->right);
        cout << node->data << " ";
    }

    // ---------- 销毁树 ----------
    void destroyTree(TreeNode* node) {
        if (node == nullptr) return;
        destroyTree(node->left);
        destroyTree(node->right);
        delete node;
    }

public:
    BinarySearchTree() : root(nullptr) {}
    ~BinarySearchTree() { destroyTree(root); }

    void insert(int value) {
        root = insertHelper(root, value);
    }

    bool search(int value) {
        return searchHelper(root, value);
    }

    void remove(int value) {
        root = removeHelper(root, value);
    }

    void inorder() {
        cout << "中序（升序）: ";
        inorderHelper(root);
        cout << endl;
    }

    void preorder() {
        cout << "前序: ";
        preorderHelper(root);
        cout << endl;
    }

    void postorder() {
        cout << "后序: ";
        postorderHelper(root);
        cout << endl;
    }

    // ---------- 层序遍历（BFS）----------
    void levelOrder() {
        cout << "层序: ";
        if (root == nullptr) return;
        queue<TreeNode*> q;
        q.push(root);
        while (!q.empty()) {
            TreeNode* cur = q.front();
            q.pop();
            cout << cur->data << " ";
            if (cur->left)  q.push(cur->left);
            if (cur->right) q.push(cur->right);
        }
        cout << endl;
    }

    // ---------- 树的高度 ----------
    int height(TreeNode* node) {
        if (node == nullptr) return 0;
        return 1 + max(height(node->left), height(node->right));
    }
    int getHeight() { return height(root); }
};

// ========== 三种遍历的直观理解 ==========
/*
          1
        /   \
       2     3
      / \
     4   5

前序 (根→左→右):  1 2 4 5 3  —— 先输出自己，再管孩子
中序 (左→根→右):  4 2 5 1 3  —— 先处理完左边，才轮到自己（BST 中序=升序）
后序 (左→右→根):  4 5 2 3 1  —— 把孩子都处理完，最后处理自己（删除文件系统用这个）
层序 (逐层):       1 2 3 4 5  —— 一层一层来
*/

// ========== STL 中的有序容器（红黑树）==========
#include <set>
#include <map>
void stl_tree_demo() {
    cout << "\n--- STL 红黑树容器 ---" << endl;

    // set：自动去重 + 自动排序
    set<int> s = {5, 2, 8, 2, 1, 9};
    cout << "set（自动排序去重）: ";
    for (int v : s) cout << v << " ";

    // map：键值对的 BST（有序）
    map<string, int> mp;
    mp["zebra"] = 1;
    mp["apple"] = 2;
    mp["mango"] = 3;
    cout << "\nmap（按键升序）: ";
    for (auto& [k, v] : mp) {
        cout << "{" << k << ":" << v << "} ";
    }
    cout << endl;
}

int main() {
    cout << "========== 二叉搜索树 ==========" << endl;
    BinarySearchTree bst;

    // 构建树
    bst.insert(50);
    bst.insert(30);
    bst.insert(70);
    bst.insert(20);
    bst.insert(40);
    bst.insert(60);
    bst.insert(80);

    bst.inorder();
    bst.preorder();
    bst.postorder();
    bst.levelOrder();

    cout << "\n查找 60: " << (bst.search(60) ? "存在" : "不存在") << endl;
    cout << "查找 99: " << (bst.search(99) ? "存在" : "不存在") << endl;
    cout << "树的高度: " << bst.getHeight() << endl;

    cout << "\n删除 20（叶节点）:" << endl;
    bst.remove(20);
    bst.inorder();

    cout << "删除 30（有一个子节点）:" << endl;
    bst.remove(30);
    bst.inorder();

    cout << "删除 50（有两个子节点，用后继替换）:" << endl;
    bst.remove(50);
    bst.inorder();
    bst.levelOrder();

    stl_tree_demo();
    return 0;
}
```

### 7.4 二叉树的退化问题

BST 在最坏情况下会退化成链表——如果插入顺序本身就是有序的：

```
插入顺序 1, 2, 3, 4, 5 → 形成一条斜线（退化）:
1
 \
  2
   \
    3
     \
      4
       \
        5
查找从 O(log n) 退化到 O(n)！
```

**解决方法**：平衡二叉树（AVL 树、红黑树）。每次插入/删除后自动调整，保持树的高度约为 log₂n。C++ `std::map` 和 `std::set` 就是用**红黑树**实现的，保证操作始终是 O(log n)。

---

## 八、堆（Heap）—— 快速找到最大/最小值

### 8.1 是什么

堆是一种**特殊的完全二叉树**，满足这一条件：**父节点的值 ≥ 子节点的值（大顶堆）** 或 **父节点的值 ≤ 子节点的值（小顶堆）**。

```
大顶堆（每个父 ≥ 子）：          小顶堆（每个父 ≤ 子）：
        100                           1
      /     \                       /   \
     50      70                    3      5
    /  \    /  \                 / \    / \
   30  20  60  40               7  9   8  10
```

> 关键特性：堆顶就是最大值（大顶堆）或最小值（小顶堆）。取最值 O(1)，插入和删除 O(log n)。

### 8.2 用数组存储堆的巧妙方法

完全二叉树可以用数组紧凑存储（不需要指针！）：

```
父节点在 i → 左子在 2i+1，右子在 2i+2
子在 i → 父在 (i-1)/2

         100(0)
        /      \
     50(1)     70(2)
    /   \      /   \
  30(3) 20(4) 60(5) 40(6)

数组: [100, 50, 70, 30, 20, 60, 40]
       0    1   2   3   4   5   6
```

### 8.3 完整实现

```cpp
#include <iostream>
#include <vector>
using namespace std;

// ========== 大顶堆 ==========
class MaxHeap {
private:
    vector<int> heap;  // 用 vector 存储

    // 上浮：新元素从底部不断往上冒，直到合适位置
    void siftUp(int index) {
        while (index > 0) {
            int parent = (index - 1) / 2;
            if (heap[index] <= heap[parent]) break;  // 满足堆条件
            swap(heap[index], heap[parent]);
            index = parent;
        }
    }

    // 下沉：顶部元素不断往下坠，直到合适位置
    void siftDown(int index) {
        int size = heap.size();
        while (true) {
            int left = 2 * index + 1;
            int right = 2 * index + 2;
            int largest = index;  // 假设自己最大

            if (left < size && heap[left] > heap[largest])
                largest = left;
            if (right < size && heap[right] > heap[largest])
                largest = right;

            if (largest == index) break;  // 已经是最大了
            swap(heap[index], heap[largest]);
            index = largest;
        }
    }

public:
    // 插入 O(log n)
    void push(int value) {
        heap.push_back(value);      // 先放到末尾
        siftUp(heap.size() - 1);    // 然后上浮到正确位置
    }

    // 查看堆顶 O(1)
    int top() {
        if (heap.empty()) {
            cout << "堆空了！" << endl;
            return -1;
        }
        return heap[0];
    }

    // 弹出堆顶 O(log n)
    void pop() {
        if (heap.empty()) {
            cout << "堆空了！" << endl;
            return;
        }
        heap[0] = heap.back();  // 把最后一个元素移到堆顶
        heap.pop_back();        // 删掉最后一个
        if (!heap.empty()) {
            siftDown(0);        // 下沉到正确位置
        }
    }

    bool empty() { return heap.empty(); }
    int size() { return heap.size(); }

    void print() {
        cout << "堆: [";
        for (int i = 0; i < heap.size(); i++) {
            cout << heap[i];
            if (i < heap.size() - 1) cout << ", ";
        }
        cout << "] 堆顶=" << (heap.empty() ? -1 : heap[0]) << endl;
    }
};

// ========== 堆的应用：堆排序 O(n log n) ==========
void heapSort(vector<int>& arr) {
    // 1. 建堆（把所有元素 push 入大顶堆）
    MaxHeap heap;
    for (int v : arr) {
        heap.push(v);
    }
    // 2. 依次弹出堆顶（每次弹出当前最大值），从后往前放
    for (int i = arr.size() - 1; i >= 0; i--) {
        arr[i] = heap.top();
        heap.pop();
    }
    // 结果是从小到大排序
}

// ========== 堆的应用：Top K 问题 ==========
// 从大量数据中找最大的 K 个
vector<int> topK(const vector<int>& data, int k) {
    // 用小顶堆维护当前最大的 K 个
    // priority_queue 默认是大顶堆，用 greater<int> 改成小顶堆
    priority_queue<int, vector<int>, greater<int>> minHeap;

    for (int v : data) {
        if (minHeap.size() < k) {
            minHeap.push(v);
        } else if (v > minHeap.top()) {
            minHeap.pop();
            minHeap.push(v);
        }
    }

    vector<int> result;
    while (!minHeap.empty()) {
        result.push_back(minHeap.top());
        minHeap.pop();
    }
    return result;
}

// ========== STL 中的堆 ==========
void stl_heap_demo() {
    cout << "\n--- STL 堆操作 ---" << endl;

    // priority_queue 默认是大顶堆
    priority_queue<int> maxPQ;
    maxPQ.push(30); maxPQ.push(10); maxPQ.push(50); maxPQ.push(20);
    cout << "大顶堆顶: " << maxPQ.top() << endl;
    maxPQ.pop();
    cout << "弹出后堆顶: " << maxPQ.top() << endl;

    // 小顶堆
    priority_queue<int, vector<int>, greater<int>> minPQ;
    minPQ.push(30); minPQ.push(10); minPQ.push(50);
    cout << "小顶堆顶: " << minPQ.top() << endl;

    // 自定义比较（比如按绝对值排序）
    auto cmp = [](int a, int b) { return abs(a) < abs(b); };
    priority_queue<int, vector<int>, decltype(cmp)> customPQ(cmp);
    customPQ.push(-10); customPQ.push(5); customPQ.push(-3);
    cout << "绝对值最大: " << customPQ.top() << endl;
}

int main() {
    cout << "========== 手动实现大顶堆 ==========" << endl;
    MaxHeap heap;
    heap.push(30); heap.push(10); heap.push(50); heap.push(20); heap.push(40);
    heap.print();

    cout << "弹出堆顶: " << heap.top() << endl;
    heap.pop();
    heap.print();

    cout << "弹出堆顶: " << heap.top() << endl;
    heap.pop();
    heap.print();

    cout << "\n========== 堆排序 ==========" << endl;
    vector<int> arr = {5, 2, 8, 1, 9, 3, 7, 4, 6};
    cout << "排序前: ";
    for (int v : arr) cout << v << " ";
    heapSort(arr);
    cout << "\n排序后: ";
    for (int v : arr) cout << v << " ";
    cout << endl;

    cout << "\n========== Top K ==========" << endl;
    vector<int> data = {3, 7, 1, 9, 2, 8, 5, 6, 4, 1, 9, 8};
    vector<int> top3 = topK(data, 3);
    cout << "最大的 3 个: ";
    for (int v : top3) cout << v << " ";
    cout << endl;

    stl_heap_demo();
    return 0;
}
```

### 8.4 堆 vs 排序

| 需求 | 方法 | 时间 |
|------|------|------|
| 把全部数据排序 | 排序算法 | O(n log n) |
| 只取最大/最小的 K 个 | 堆 | O(n log K) |
| 需要不断插入 + 不断取最值 | 堆 | 每次 O(log n) |

> 如果只需要 K 个最大的，堆就是最优解——它不需要对不关心的数据排序。

---

## 九、图（Graph）—— 万物互联

### 9.1 是什么

图由**顶点**（Vertex，也叫节点）和**边**（Edge）组成。网络、地图、社交关系都是图。

```
朋友圈：
      张三
     /    \
  李四——王五
    |
  赵六

顶点：{张三, 李四, 王五, 赵六}
边：{张三-李四, 张三-王五, 李四-王五, 李四-赵六}
```

### 9.2 图的两种存储方式

**邻接矩阵**：二维数组，`matrix[i][j] = 1` 表示有一条从 i 到 j 的边。

```
    A B C D
A [ 0 1 1 0 ]
B [ 1 0 0 1 ]    A→B, A→C, B→D, C→D
C [ 0 0 0 1 ]
D [ 0 0 0 0 ]

优点：判断两个节点是否相连 O(1)
缺点：占用 O(V²) 空间，节点很多时空得厉害
```

**邻接表**：每个节点挂一个链表，存它的邻居。

```
A → [B, C]
B → [A, D]
C → [D]
D → [A]

优点：节省空间 O(V+E)，常用
缺点：判断两节点是否相连 O(degree(V))
```

### 9.3 BFS 和 DFS

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <stack>
#include <unordered_map>
#include <unordered_set>
using namespace std;

// ========== 邻接表实现的无向图 ==========
class Graph {
private:
    // 每个节点对应一个邻居列表
    unordered_map<int, vector<int>> adjList;

public:
    // 添加边（无向图，双方都加）
    void addEdge(int u, int v) {
        adjList[u].push_back(v);
        adjList[v].push_back(u);
    }

    // 获取所有节点
    vector<int> getVertices() {
        vector<int> vertices;
        for (auto& [v, _] : adjList) {
            vertices.push_back(v);
        }
        return vertices;
    }

    // ========== BFS：广度优先搜索（逐层展开）==========
    // 像水波纹一样从起点一层层扩散
    void BFS(int start) {
        cout << "BFS 从 " << start << " 开始: ";

        unordered_set<int> visited;  // 记录访问过的
        queue<int> q;
        q.push(start);
        visited.insert(start);

        while (!q.empty()) {
            int current = q.front();
            q.pop();
            cout << current << " ";

            // 当前节点的所有邻居中，没访问过的入队
            for (int neighbor : adjList[current]) {
                if (visited.find(neighbor) == visited.end()) {
                    visited.insert(neighbor);
                    q.push(neighbor);
                }
            }
        }
        cout << endl;
    }

    // ========== DFS：深度优先搜索（一条路走到底，没路了再回头）==========
    void DFS(int start) {
        cout << "DFS 从 " << start << " 开始: ";

        unordered_set<int> visited;
        stack<int> stk;  // 用栈模拟递归
        stk.push(start);

        while (!stk.empty()) {
            int current = stk.top();
            stk.pop();

            if (visited.find(current) != visited.end()) continue;

            visited.insert(current);
            cout << current << " ";

            // 把邻居压入栈（先压入的会后访问）
            for (int neighbor : adjList[current]) {
                if (visited.find(neighbor) == visited.end()) {
                    stk.push(neighbor);
                }
            }
        }
        cout << endl;
    }

    // ========== DFS 递归版（更符合直觉）==========
    void DFS_Recursive() {
        cout << "DFS 递归: ";
        unordered_set<int> visited;
        auto vertices = getVertices();
        if (!vertices.empty()) {
            dfsHelper(vertices[0], visited);
        }
        cout << endl;
    }

    void dfsHelper(int node, unordered_set<int>& visited) {
        visited.insert(node);
        cout << node << " ";

        for (int neighbor : adjList[node]) {
            if (visited.find(neighbor) == visited.end()) {
                dfsHelper(neighbor, visited);
            }
        }
    }

    void print() {
        cout << "图的邻接表:" << endl;
        for (auto& [node, neighbors] : adjList) {
            cout << "  " << node << " → [";
            for (int i = 0; i < neighbors.size(); i++) {
                cout << neighbors[i];
                if (i < neighbors.size() - 1) cout << ", ";
            }
            cout << "]" << endl;
        }
    }
};

int main() {
    cout << "========== 图的遍历 ==========" << endl;

    // 构建这个图:
    //    1 —— 3
    //   / \    \
    //  0   2 —— 4
    Graph graph;
    graph.addEdge(0, 1);
    graph.addEdge(1, 3);
    graph.addEdge(1, 2);
    graph.addEdge(2, 4);
    graph.addEdge(3, 4);

    graph.print();
    cout << endl;

    graph.BFS(0);   // 预期: 0 1 2 3 4  （逐层）
    graph.DFS(0);   // 预期: 0 1 2 4 3  （一路到底）
    graph.DFS_Recursive();  // 递归版 DFS

    cout << "\n========== BFS vs DFS 使用场景 ==========" << endl;
    cout << "BFS 找最短路径（没权重时）  —— 朋友圈里找离你最近的人" << endl;
    cout << "DFS 检测环、拓扑排序       —— 课程安排、编译依赖" << endl;
    cout << "DFS 递归版代码简单          —— 面试常用" << endl;

    return 0;
}
```

### 9.4 图的应用场景

| 场景 | 用什么 |
|------|--------|
| 地图导航（最短路径） | Dijkstra（BFS 升级版） |
| 社交网络的"共同好友" | 图遍历 |
| 课程表安排（拓扑排序） | DFS |
| 网络爬虫 | BFS |
| 迷宫求解 | DFS / BFS 回溯 |

---

## 十、数据结构选择速查表

我把这 8 种数据结构的选择逻辑总结成一张表，以后你写代码时对照着看就行：

| 你的需求 | 选这个 | 原因 |
|----------|--------|------|
| 频繁按下标读写 | **数组 (vector)** | O(1) 随机访问 |
| 频繁从头部插入/删除 | **链表 (list)** | O(1) 改指针 |
| 需要"撤销"、"后退"功能 | **栈 (stack)** | LIFO，天然支持 |
| 任务排队处理 | **队列 (queue)** | FIFO，先来先服务 |
| 根据键查值，速度第一 | **哈希表 (unordered_map)** | O(1) 均摊 |
| 需要有序遍历 + 查找 | **红黑树 (map)** | O(log n) 且有序 |
| 不停取最大/最小值 | **堆 (priority_queue)** | 取最值 O(1) |
| 建模网络、地图、关系 | **图 (邻接表)** | 灵活表达关系 |
| 去重 + 检查是否存在 | **哈希集 (unordered_set)** | O(1) 查重 |

---

## 十一、常见面试题速讲

### 11.1 反转链表

上面链表章节的代码已经实现了，核心思路：三个指针 `prev`、`current`、`next`，每次把 `current->next` 指回 `prev`。

### 11.2 有效的括号

上面栈章节的 `isBalanced` 函数就是。用栈：左括号入栈，右括号与栈顶匹配。

### 11.3 数组中的第 K 大元素

上面堆章节的 `topK` 函数。用小顶堆维护最大的 K 个，堆顶就是第 K 大。

### 11.4 二叉树的层序遍历

上面树章节的 `levelOrder` 函数。用队列 BFS：每层出队时把下一层入队。

### 11.5 LRU 缓存

需要同时用**哈希表 + 双向链表**：
- 哈希表实现 O(1) 查找
- 双向链表维护使用顺序，最近使用的移到头部，最少使用的在尾部删除

```cpp
// LRU 缓存的核心思路（伪代码）
// HashMap<key, 链表节点指针>  ← O(1) 查找
// 双向链表头 = 最近使用, 双向链表尾 = 最久未使用
// get(key): 找到节点，移到链表头
// put(key, value): 存在则更新并移头；不存在则建新节点放头，超容量时删尾
```

---

## 十二、C++ STL 容器总览

| STL 容器 | 底层数据结构 | 头文件 |
|----------|-------------|--------|
| `vector` | 动态数组 | `<vector>` |
| `list` | 双向链表 | `<list>` |
| `forward_list` | 单向链表 | `<forward_list>` |
| `stack` | 可配（默认 deque） | `<stack>` |
| `queue` | 可配（默认 deque） | `<queue>` |
| `deque` | 双端队列 | `<deque>` |
| `priority_queue` | 堆（默认大顶堆） | `<queue>` |
| `map` / `set` | 红黑树（O(log n)） | `<map>` / `<set>` |
| `unordered_map` / `unordered_set` | 哈希表（O(1) 均摊） | `<unordered_map>` / `<unordered_set>` |

---

## 总结

读完这篇文章，你应该记住三件事：

1. **没有万能的数据结构。** 每种结构都是在"时间"和"空间"之间做取舍。数组快在读取，链表快在修改，哈希表快在查找，堆快在取最值。

2. **时间复杂度是你的武器。** 遇到程序慢，先算每个操作的时间复杂度：是 O(1)、O(log n) 还是 O(n²)？多数慢程序，换一个合适的数据结构就能快十倍。

3. **STL 是你的朋友。** 90% 的情况直接用 STL 就够了。剩下 10% 需要自己写的时候，本文的手写代码就是你的起点。

> 数据结构不是背下来的，是用出来的。建议你把本文每个结构的代码都跑一遍，修改参数，观察输出。写代码的时候回头看这张速查表，慢慢就内化了。

---

*本文所有代码在 C++17 环境下编译运行通过。复制任意代码块到 `main.cpp`，用 `g++ -std=c++17 main.cpp -o main && ./main` 即可运行。*
