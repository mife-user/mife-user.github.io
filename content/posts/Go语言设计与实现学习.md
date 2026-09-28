---
title: 'Go语言设计与实现学习'
date: 2026-09-17T13:16:18+08:00
lastmod: 2026-09-28T15:33:18+08:00
draft: false
tags: ["go", "八股"]
---

# 前言

希望有一天能够真正有机会和一群志同道合人的人为梦想努力。

哎呀我去，这玩意怎么这么难，我去了。

至于为什么文章这么长，一方面是有些部分写的过于具体了，比如语法分析那里写了个例子，总的来说还是个总结的文章

# 准备工作

## 1.1调试源代码

./src/make.bash脚本会编译 Go 语言的二进制、工具链以及标准库和命令并将源代码和编译好的二进制文件移动到对应的位置上.现在go语言应该是在`$GOROOT/src`下面

Go语言编译过程中需要生成中间代码，中间代码具有 SSA（静态单赋值）的特性

Go编译汇编语法：
```bash
go build -gcflags -S main.go
```
注意go编译的汇编是无法通过GCC汇编器的

Go语言获取汇编指令优化过程：
```bash
GOSSAFUNC=main go build main.go
# runtime
dumped SSA to /usr/local/Cellar/go/1.14.2_1/libexec/src/runtime/ssa.html
# command-line-arguments
dumped SSA to ./ssa.html
```

# 编译原理

## 2.1编译过程

AST（抽象语法树）：

是源代码语法的结构的一种抽象表示，这个抽象语法树会辅助编译器进行语义分析，我们可以用它来确定语法正确的程序是否存在一些类型不匹配的问题。

SSA（静态单赋值）：

静态单赋值（Static Single Assignment、SSA）是中间代码的特性，如果中间代码具有静态单赋值的特性，那么每个变量就只会被赋值一次。SSA 的主要作用是对代码进行优化，所以它是编译器后端的一部分。

指令集：

```bash
uname -m #查看当前电脑硬件信息
```

- 复杂指令集(CISC)
- 精简指令集(RISC)

编译原理：

go的编译器源码在src/cmd/compile，编译器的前端一般承担着词法分析、语法分析、类型检查和中间代码生成几部分工作，而编译器后端主要负责目标代码的生成和优化，也就是将中间代码翻译成目标机器能够运行的二进制机器码。

```mermaid
flowchart LR
    SRC[源代码] --> LEX[词法分析]
    LEX --> PARSE[语法分析]
    PARSE --> AST[抽象语法树 AST]
    AST --> TC[类型检查]
    TC --> IR[中间代码生成]
    IR --> SSA[SSA 中间代码]
    SSA --> OPT[优化<br/>机器无关 + lowering]
    OPT --> MC[机器码生成]
```

各阶段对应的包：

| 阶段 | 包 / 关键类型 | 产物 |
| --- | --- | --- |
| 词法分析 | `internal/syntax`（`scanner`） | `token` 流 |
| 语法分析 | `internal/syntax`（`parser`） | `syntax.Node`（语法树） |
| 类型检查 | `internal/types2`（旧版为 `gc`） | 带类型信息的节点 |
| 中间代码生成 | `internal/walk` + `internal/ssa` | `ir.Node` → SSA 值 |
| 后端优化 | `internal/ssa` 的多轮 pass | 机器相关的 SSA |
| 机器码生成 | `internal/ssa` + `internal/objw` | 汇编码 → 目标文件 |


词法分析会返回一个不包含空格、换行等字符的 Token 序列，例如：package, json, import, (, io, ), …，而语法分析会把 Token 序列转换成有意义的结构体，即语法树

每一个 AST 都对应着一个单独的 Go 语言文件，这个抽象语法树中包括当前文件属于的包名、定义的常量、结构体和函数等。

类型检查阶段不止会对节点的类型进行验证，还会展开和改写一些内建的函数，例如 make 关键字在这个阶段会根据子树的结构被替换成 runtime.makeslice 或者 runtime.makechan 等函数。

在类型检查之后，编译器会通过 cmd/compile/internal/gc.compileFunctions 编译整个 Go 语言项目中的全部函数，这些函数会在一个编译队列中等待几个 Goroutine 的消费，并发执行的 Goroutine 会将所有函数对应的抽象语法树转换成中间代码。

## 2.2 词法与语法分析

### 词法分析：

将源代码拆分为Token序列的过程

lex：用于生成词法分析器的工具，lex 生成的代码能够将一个文件中的字符分解成 Token 序列，lex 作为一个代码生成器，使用了类似 C 语言的语法，我们将 lex 理解为正则匹配的生成器，它会使用正则匹配扫描输入的字符流。但是Go有自己的“lex”，而lex自己的办法是.l文件通过lex生成C语言代码，将 C 语言代码通过 gcc 编译成二进制代码之后，就可以使用管道将上面提到的 Go 语言代码作为输入传递到生成的词法分析器中。

Go 语言的词法解析是通过 src/cmd/compile/internal/syntax/scanner.go6 文件中的 cmd/compile/internal/syntax.scanner 结构体实现的，这个结构体会持有当前扫描的数据源文件、启用的模式和当前被扫描到的 Token。

src/cmd/compile/internal/syntax/tokens.go7 文件中定义了 Go 语言中支持的全部 Token 类型。

### 语法分析：

通过文法确定语法结构，文法用来形式化、精确描述某种编程语言的工具，主要包含一系列用于转换字符串的生产规则（Production rule）。文法都由以下的四个部分组成：

终结符是文法中无法再被展开的符号，而非终结符与之相反，还可以通过生产规则进行展开，例如 “id”、“123” 等标识或者字面量。
- N 有限个非终结符的集合；
- Σ 有限个终结符的集合；
- P 有限个生产规则12的集合；
- S 非终结符集合中唯一的开始符号；

如何理解扇面书N，Σ等呢？很简单，可以将其判断为一个规则P，然后逐渐将其中的N替换为对应的含Σ的另一个P然后继续分，比如：

<details class="fold-container">
<summary class="fold-title"><span data-zh="📖 展开完整推导过程（共 13 步）" data-en="📖 Show full derivation (13 steps)">📖 展开完整推导过程（共 13 步）</span></summary>

*第一步：原始C++代码（源码）*
```cpp
int main()
{
    cout << "hello world" << endl;
    return 0;
}
```
> 词法分析之后，得到**终结符Token序列**（就是$\Sigma$里面的符号，无中文）：
```
int  main  (  )  {  cout  <<  "hello world"  <<  endl  ;  return  0  ;  }
```

我们使用文法：
$$
\begin{align*}
G&=(N,\Sigma,P,S)\\
N&=\{Program,\ FuncDef,\ Type,\ Id,\ StmtList,\ Stmt,\ OutputStmt,\ ReturnStmt,\ Constant\}\\
\Sigma&=\{\texttt{int},\texttt{main},\texttt{cout},\texttt{<<},\texttt{"hello world"},\texttt{endl},\texttt{return},\texttt{0},\texttt{(},\texttt{)},\texttt{\{},\texttt{\}},\texttt{;}\}\\
P&=\begin{cases}
Program \rightarrow FuncDef \\
FuncDef \rightarrow Type\ Id\ (\ )\ \{ \ StmtList\ \} \\
Type \rightarrow int \\
Id \rightarrow main \\
StmtList \rightarrow Stmt\ StmtList \\
StmtList \rightarrow \varepsilon \\
Stmt \rightarrow OutputStmt \\
Stmt \rightarrow ReturnStmt \\
OutputStmt \rightarrow cout\ <<\ Constant\ <<\ endl\ ; \\
ReturnStmt \rightarrow return\ Constant\ ; \\
Constant \rightarrow "hello world" \\
Constant \rightarrow 0
\end{cases}\\
S&=Program
\end{align*}
$$

---

*模拟编译器：自顶向下推导（从开始符号$Program$出发，一步步替换）*
> $\Rightarrow$ 代表：使用一条产生式，替换左边非终结符为右边符号串。

1. 起始：$\boldsymbol{Program}$
$$
Program \Rightarrow FuncDef
$$
> 使用规则：$Program \rightarrow FuncDef$

2.
$$
FuncDef \Rightarrow Type\ Id\ (\ )\ \{ \ StmtList\ \}
$$
> 使用规则：$FuncDef \rightarrow Type\ Id\ (\ )\ \{ \ StmtList\ \}$

3. 替换非终结符 $Type$
$$
Type\ Id\ (\ )\ \{ \ StmtList\ \} \Rightarrow \boldsymbol{int}\ Id\ (\ )\ \{ \ StmtList\ \}
$$
> 使用规则：$Type \rightarrow int$

4. 替换非终结符 $Id$
$$
int\ Id\ (\ )\ \{ \ StmtList\ \} \Rightarrow int\ \boldsymbol{main}\ (\ )\ \{ \ StmtList\ \}
$$
> 使用规则：$Id \rightarrow main$

5. 替换非终结符 $StmtList$，选规则 $StmtList\rightarrow Stmt\ StmtList$
$$
int\ main\ (\ )\ \{ \ StmtList\ \} \Rightarrow int\ main\ (\ )\ \{ \ \boldsymbol{Stmt}\ StmtList\ \}
$$
> 使用规则：$StmtList \rightarrow Stmt\ StmtList$

6. 替换第一个 $Stmt$，选 $Stmt\rightarrow OutputStmt$
$$
int\ main\ (\ )\ \{ \ Stmt\ StmtList\ \} \Rightarrow int\ main\ (\ )\ \{ \ \boldsymbol{OutputStmt}\ StmtList\ \}
$$
> 使用规则：$Stmt \rightarrow OutputStmt$

7. 替换 $OutputStmt$
$$
OutputStmt \Rightarrow cout\ <<\ Constant\ <<\ endl\ ;
$$
$$
int\ main\ (\ )\ \{ \ OutputStmt\ StmtList\ \}
\Rightarrow int\ main\ (\ )\ \{ \ cout\ <<\ \boldsymbol{Constant}\ <<\ endl\ ;\ \ StmtList\ \}
$$
> 使用规则：$OutputStmt \rightarrow cout\ <<\ Constant\ <<\ endl\ ;$

8. 替换 $Constant$，选 $Constant\rightarrow "hello world"$
$$
int\ main\ (\ )\ \{ \ cout\ <<\ Constant\ <<\ endl\ ;\ \ StmtList\ \}
\Rightarrow int\ main\ (\ )\ \{ \ cout\ <<\ \boldsymbol{"hello world"}\ <<\ endl\ ;\ \ StmtList\ \}
$$
> 使用规则：$Constant \rightarrow "hello world"$

9. 现在处理剩下的 $StmtList$，继续展开：$StmtList\rightarrow Stmt\ StmtList$
$$
int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ StmtList\ \}
\Rightarrow int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ \boldsymbol{Stmt}\ StmtList\ \}
$$
> 使用规则：$StmtList \rightarrow Stmt\ StmtList$

10. 替换第二个 $Stmt$，选 $Stmt\rightarrow ReturnStmt$
$$
int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ Stmt\ StmtList\ \}
\Rightarrow int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ \boldsymbol{ReturnStmt}\ StmtList\ \}
$$
> 使用规则：$Stmt \rightarrow ReturnStmt$

11. 替换 $ReturnStmt$
$$
ReturnStmt \Rightarrow return\ Constant\ ;
$$
$$
int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ ReturnStmt\ StmtList\ \}
\Rightarrow int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ return\ \boldsymbol{Constant}\ ;\ \ StmtList\ \}
$$
> 使用规则：$ReturnStmt \rightarrow return\ Constant\ ;$

12. 替换这里的 $Constant$，选 $Constant\rightarrow 0$
$$
int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ return\ Constant\ ;\ \ StmtList\ \}
\Rightarrow int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ return\ \boldsymbol{0}\ ;\ \ StmtList\ \}
$$
> 使用规则：$Constant \rightarrow 0$

13. 最后剩下的 $StmtList$，使用空串规则 $StmtList\rightarrow \varepsilon$（$\varepsilon$代表删掉，什么都不写）
$$
int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ return\ 0\ ;\ \ StmtList\ \}
\Rightarrow int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ return\ 0\ ;\ \ \varepsilon\ \}
$$
> 使用规则：$StmtList \rightarrow \varepsilon$

---

✅ 推导完成
全部非终结符都被替换完毕，只剩下**终结符序列**：
$$
\boldsymbol{int\ main\ (\ )\ \{ \ cout\ <<\ "hello world"\ <<\ endl\ ;\ \ return\ 0\ ;\ \}}
$$
这正好就是我们写的hello world经过词法分析后的Token流。

</details>

---

关键总结：

1. 推导成功 = 语法合法；如果某一步找不到匹配的产生式，就报语法错误。

> 真实编译器是**自底向上归约**（反过来做），上面是自顶向下推导，方便理解。

在这里我们可以从 src/cmd/compile/internal/syntax/parser.go13 文件中摘抄一些 Go 语言文法的生产规则.

自顶向下是先用目标文法来判断当前是否符合，即：你手里只有「目标是 Program」，没有别的信息。于是你猜：Program 大概长成 FuncDef 吧？展开一看，跟输入对上了，继续猜 FuncDef 由 Type Id ( ) { StmtList } 组成……猜错了就退回来换一条规则重猜，这个「退回来」就是回溯。

而自底向上是输入确定，看到栈顶 int 能匹配 Type -> int，就把 int 打包成 Type；看到 return 0 ; 能匹配 ReturnStmt -> return Constant ;而归约成 Program 的那一刻，就等于宣布「语法合法」。

即通过判断Token流是否符合文法来判断是否符合Go语法😢（难难）


Lookahead（向前查看）：

在不同生产规则发生冲突时，当前解析器需要通过预读一些 Token 判断当前应该用什么生产规则对输入流进行展开或者归约。Go语言通过实现即无需额外空间：
```go
if p.tok == tok {   // 先看一眼
    p.next()        // 确认了才消费掉
    return true
  }
```

词法和语法分析一起进行的。

节点：

语法分析器最终会使用不同的结构体来构建抽象语法树中的节点，其中根节点包含了当前文件的包名、所有声明结构的列表和文件的行数。

## 类型检查

强弱类型：大体就是强类型明确定义，弱类型常常隐式转换，Go算强类型语言

静态类型检查：

它能够减少程序在运行时的类型检查，也可以被看作是一种代码优化的方式。

动态类型检查：

动态类型检查是在运行时确定程序类型安全的过程，它需要编程语言在编译时为所有的对象加入类型标签等信息，运行时可以使用这些存储的类型信息来实现动态派发、向下转型、反射以及其他特性6。

执行过程：

Go 语言的编译器不仅使用静态类型检查来保证程序运行的类型安全，还会在编程期间引入类型信息，让工程师能够使用反射来判断参数和变量的类型。

比如切片先检查右侧的类型，然后匹对左侧，而哈希会讲左侧的键加入队列然后在后面才检查，而关键字中make，会在类型检查阶段根据创建的类型讲make替换为特定的函数，然后生成中间代码的过程不会处理OMAKE类型的节点

## 中间代码生成

### 概述

编译过程中，编译器会在将源代码转换到机器码的过程中，先把源代码转换成一种中间的表示形式，即中间代码。Go语言编译器的中间代码具有静态单赋值（SSA）的特性，注意这里的中间代码不是汇编。

### 配置初始化

首先会进行SSA配置初始化。
1. 初始化结构体，缓存指针，优化类型指针的获取效率，一个类型类型指针只有一个，由于类型很大，所以用指针。编译器里每个类型（包括 int、*int、**int）都对应一个 types.Type 对象。指向这些对象的指针叫类型指针。
2. 根据传入的 CPU 架构设置用于生成中间代码和机器码的函数，当前编译器使用的指针、寄存器大小、可用寄存器列表、掩码等编译选项
3. 初始化一些编译器可能用到的 Go 语言运行时的函数

### 遍历与替换

在生成中间代码前还需要替换抽象语法树中节点的一些元素，遍历抽象语法树的函数会将一些关键字和内建函数转换成函数调用。比如： panic、recover 两个内建函数转换成 runtime.gopanic 和 runtime.gorecover 两个真正运行时函数，而关键字 new 也会被转换成调用 runtime.newobject 函数。

### SSA生成

经过 walk 系列函数的处理之后，抽象语法树就不会改变了。通过生成ssa.html文件可以看到其中最左侧就是源代码，中间是源代码生成的抽象语法树，最右侧是生成的第一轮中间代码。其中间代码生成分为二个阶段，一用相关函数将抽象语法树转换为中间代码，二通过多轮迭代更新SSA中间代码。

AST->SSA

在遇到函数调用、方法调用、使用 defer 或者 go 关键字时都会执行cmd/compile/internal/gc.state.callResult 和 cmd/compile/internal/gc.state.call 生成调用函数的 SSA 节点，这些在开发者看来不同的概念在编译器中都会被实现成静态的函数调用，上层的关键字和方法只是语言为我们提供的语法糖.

多轮转换

中间代码需要优化并精简，比如删除打印日志，性能分析的代码

## 机器码生成

机器码的生成过程其实是对 SSA 中间代码的降级（lower）过程，在 SSA 中间代码降级的过程中，编译器将一些值重写成了目标 CPU 架构的特定值

### 指令集架构

作为计算机软件和硬件之间的接口和桥梁，指令集架构定义了支持的数据结构、寄存器、管理主内存的硬件支持，支持的指令集和 IO 模型，建立抽象层

- 复杂指令集：多且复杂，长度不等
- 精简指令集：精简，数量少，使用标准字节长度

### SSA降级

实际上将近 50 轮处理的过程中，lower 以及后面的阶段都属于 SSA 降级这一过程。最后cmd/compile/internal/gc.buildssa 中的 lower 和随后的多个阶段会对 SSA 进行转换、检查和优化，生成机器特定的中间代码，接下来通过 cmd/compile/internal/gc.genssa 将代码输出到 cmd/compile/internal/gc.Progs 对象中，这也是代码进入汇编器前的最后一个步骤。

### 汇编器

汇编器是将汇编语言翻译为机器语言的程序，Go 语言的汇编器是基于 Plan 9 汇编器的输入类型设计的。

## 数据结构

### 数组

计算机为数组分配连续内存保持元素，议案为一维线性数组，也有多维数组。

上限推导

如果为[10]T，其类型在编译进行到类型检查阶段就会被提取出来，随后使用 cmd/compile/internal/types.NewArray创建包含数组大小的 cmd/compile/internal/types.Array 结构体。而[...]T会在 cmd/compile/internal/gc.typecheckcomplit 函数中对该数组的大小进行推导。

语句转换

当数组元素数量小于4个，直接将数组中的元素放置在栈上（不考虑逃逸分析）。而大于4个会将数组中的元素放置到静态区并在运行时取出；

比如：

- 小于4：
```go
var arr [3]int
arr[0] = 1
arr[1] = 2
arr[2] = 3
```
- 大于4
```go
var arr [5]int
statictmp_0[0] = 1
statictmp_0[1] = 2
statictmp_0[2] = 3
statictmp_0[3] = 4
statictmp_0[4] = 5
arr = statictmp_0
```

原因：

栈上直接初始化：元素较少的数组，直接在栈上初始化是高效的。元素很多，编译器需要在栈上生成大量独立的赋值指令（如 MOVQ），会增加编译后代码的体积，并可能因为指令过多而拖慢执行速度。

静态区初始化：将数组放在静态数据区，编译器可以在编译期就计算好所有初始值，并在二进制文件中紧凑地存储为一整块数据。运行时，只需要调用 runtime.memmove 进行一次内存拷贝，就能将整个数组“搬”到栈上。这种“一次拷贝”的方式，远胜于“多次单独赋值”，能显著提升初始化效率。

访问与赋值：

数组为连续内存空间，通过指向开头的指针，元素数量及大小快速访问。Go 语言中可以在编译期间的静态类型检查判断数组越界。数组寻址和赋值都是在编译阶段完成的，没有运行时的参与。

### 切片

切片长度为动态，切片内元素的类型都是在编译期间确定的。可以将切片理解成一片连续的内存空间加上长度与容量的标识。

#### 初始化

三种方法：
```go
arr[0:3] or slice[0:3]
slice := []int{1, 2, 3}
slice := make([]int, 10)
```
1. 使用下标：通过下标创建切片最原始也最接近汇编语言的方式，使用下标初始化切片不会拷贝原数组或者原切片中的数据，它只会创建一个指向原数组的切片结构体，所以修改新切片的数据也会修改原切片

```go
func newSlice() []int {
	arr := [3]int{1, 2, 3}
	slice := arr[0:1]
	return slice
}
```

2. 字面量 使用[]int{1,2,3}创建时（实际上当元素大于一定值后才会选择用静态模板），编译期间会展开为：
```go
var vstat [3]int
vstat[0] = 1
vstat[1] = 2
vstat[2] = 3
var vauto *[3]int = new([3]int)
*vauto = vstat //将静态存储区的数组 vstat 赋值给 vauto 指针所在的地址
slice := vauto[:]
```
为什么要这么麻烦呢，一vstat是会标记位readonly（只读），二new是切片需要可追加，需要逃逸到堆上，三[:]是将指针，len，cap打包成header作为切片

3. 关键字（make）：当切片发生逃逸或者非常大时，运行时需要在堆上初始化切片。如果当前的切片不会发生逃逸并且切片非常小的时候，make([]int, 3, 4) 会被直接转换成如下所示的代码：
```go
var arr [4]int
n := arr[:3]
```
#### 访问元素

使用 len 和 cap 获取长度或者容量是切片最常见的操作，访问切片中的字段可能会触发 “decompose builtin” 阶段的优化，len(slice) 或者 cap(slice) 在一些情况下会直接替换成切片的长度或者容量，不需要在运行时获取。访问切片中元素使用的 OINDEX 操作也会在中间代码生成期间转换成对地址的直接访问。

#### 追加和扩容

如果 append 返回的新切片不需要赋值回原有的变量，就会进入如下的处理流程：
```go
// append(slice, 1, 2, 3)
ptr, len, cap := slice
newlen := len + 3
if newlen > cap {
    ptr, len, cap = growslice(slice, newlen)
    newlen = len + 3
}
*(ptr+len) = 1
*(ptr+len+1) = 2
*(ptr+len+2) = 3
return makeslice(ptr, newlen, cap)
```
大概就是：先获取slice的数组指针，len和cap，将len增加，如果大于cap则获取新底层数组，之后通过地址赋值，最后创建新切片，所以如果没有超过cap会用同一个底层数组的

如果使用 slice = append(slice, 1, 2, 3) 语句，那么 append 后的切片会覆盖原切片，这时 cmd/compile/internal/gc.state.append 方法会使用另一种方式展开关键字：
```go
// slice = append(slice, 1, 2, 3)
a := &slice
ptr, len, cap := slice
newlen := len + 3
if uint(newlen) > uint(cap) {
   newptr, len, newcap = growslice(slice, newlen)
   vardef(a)
   *a.cap = newcap
   *a.ptr = newptr
}
newlen = len + 3
*a.len = newlen
*(ptr+len) = 1
*(ptr+len+1) = 2
*(ptr+len+2) = 3
```
如果我们选择覆盖原有的变量，就不需要担心切片发生拷贝影响性能，因为 Go 语言编译器已经对这种常见的情况做出了优化。实际上只要扩容了就是新的底层数组。

为什么 *a.cap 写在 *a.ptr 前面？
因为写 ptr 要调写屏障，cap 这期间还得占着寄存器，先落盘能少一次寄存器溢出。

有些其实难想明白，虽然说传副本仍然是同一个底层数组，但是仅仅读操作并不会出现危害吧，然而我发现ai写代码时会尽可能避开。

一个有趣的：
```go
var a []int
fmt.Println(a == nil) // true

b := []int{}
fmt.Println(b == nil) // false
//nil 切片可以直接 append，Go 会自动分配底层数组。
s := []int{1, 2, 3, 4, 5}
a := s[1:3]     // len=2, cap=4
b := s[1:3:3]   // len=2, cap=2
//三索引切片可以限制容量
```

对了，即使是:=也是同一个底层数组：
```go
arr := [5]int{1, 2, 3, 4, 5}
s := arr[1:3] // [2,3]
```
s 的底层数组仍然是 arr：
- len(s) = 3 - 1 = 2
- cap(s) = len(arr) - 1 = 4
- 修改 s[0] 会影响 arr[1]

问题：大数组小切片导致内存泄漏
```go
func getSub() []int {
    big := make([]int, 1_000_000)
    return big[:10]
}//返回的切片只用了 10 个元素，但整个底层数组仍被引用，无法被 GC 回收。
```

扩容具体实现简要讲下，函数：`func growslice(et *_type, old slice, cap int) slice`；cap是期望扩容的容量，当cap > old的cap的两倍，则新容器的容量直接等于cap否则判断：当old长度小于1024则新容量为old的两倍，大于则循环增加25%直至大于期望容量。

#### 拷贝切片

分为运行时与非运行时，但是二者都会将整块内存的内容拷贝到目标的内存区域中。所有需要注意性能

### 哈希表

读写O(1)。由于输入终会大于输出，所以需要解决冲突，方法：
- 开放寻址法：发生冲突则写入下个索引不为空的位置，对性能影响最大的是装载因子（数组中元素的数量与数组大小的比值）
- 拉链法：简要就是数组加上链表（装载因子:=元素数量÷桶数量）

反正大体就是通过hash函数将一串任意数据转换为一串数字。比如：index := hash(aim) % array.len

go中的hmap，哈希表中桶的数量都 2 的倍数（通常？），存在一个叫哈希种子的东西hash0），用于引入随机性。oldbuckets是哈希在扩容时用于保存之前 buckets 的字段，它的大小是当前 buckets 的一半（现在不理解为什么是一半）。还有就是有个东西叫溢出桶用于减少扩容频率。


```text
桶数组 buckets：有 2^B 个桶
每个桶 bmap：
    tophash[8]   // 8个槽分别对应的高8位
    keys[8]      // 8个key
    values[8]    // 8个value
    overflow *bmap
```

还有个优化是其桶有个tophash字段，存储键的哈希高8位，以减少访问键值对的次数。

bmap:
```go
type bmap struct {
    topbits  [8]uint8
    keys     [8]keytype
    values   [8]valuetype
    pad      uintptr
    overflow uintptr
}
```

#### 初始化

同样根据大小分，当小于25个时，会一次加入好哈希表中，大于时会先创建数组分别存储键和值，然后循环加入哈希。当桶得数量较少时，会省略溢出桶得创建。

#### 读写

访问可以通过下标和遍历，如果是两个参数返回一个bool用于判断键值对是否存在。hmap是桶而bmap是槽，高8位存到这个key对应的tophash，第B位决定选择哪个bucket（桶），有个误区，就是这里低B位不是除了高8位的其余位数，其实中间还有很多位，高8位用来快速跳过不匹配的。遍历会将正常桶和溢出桶都遍历，通过一个桶中的overflow指向的是下一个溢出桶

#### 扩容

触发条件：负载因子 > 6.5

1. 翻倍扩容：新桶数量 = 旧桶数量 x ，旧桶元素会分裂到两个新桶中
2. 等量扩容： 当B < 15时，如果 noverflow >= 2^B 或 B >= 15时，如果noverflow >= 2^15 就会触发，其B不变，新桶数量与旧桶一致。

先讲解下等量扩容，可能会认为桶的数量没有增加，就像饭满了，即使有新的碗装也会慢，其实有种情况是：
```text
旧桶 i：
  主桶：8 个槽，实际有效 5 个，3 个空
  溢出桶1：8 个槽，实际有效 2 个，6 个空
  溢出桶2：8 个槽，实际有效 1 个，7 个空
  溢出桶3：8 个槽，实际有效 0 个，8 个空
```
也就是说，删除map元素是，go不会回收，而是将槽标记成 emptyOne 或 emptyRest。这样会出现很多空位，而等量扩容则是创建新的空桶，然后将8个桶装满才装溢出桶，相当于填满了空位。然而因为是渐进式扩容，则会导致如果在扩容中，删除了元素，仍然会在新桶中造成空位。

而翻倍扩容，会增加一位B，按照增加的位是1或0分配不同的两个桶，旧桶i如果新增0去新桶i，1去新桶i+oldLen。oldLen = 2_oldB。


渐进式扩容：会创建新的桶和溢出桶，保留原有的桶并设置到oldbuckets上，之后每次对 map 进行写、删等操作时，会触发 growWork，迁移至少两个桶。通过哈希计数器nevacuate在所有的旧桶都被分流后清空哈希的 oldbuckets 和 oldoverflow。在获取键值时会先去oldbuckets。


#### 考题
<details>
<summary>常见考题</summary>
1. Go map 底层结构？
经典实现：hmap + bmap。hmap 有 count、flags、B、hash0、buckets、oldbuckets、nevacuate 等；bmap 是桶，默认存 8 个 KV，含 tophash[8]、key 数组、value 数组、overflow 指针。

2. 哈希冲突怎么解决？
链地址法变种：一个桶 8 个槽，满了挂 overflow 桶，形成溢出桶链表。

3. key 如何定位到桶？
hash(key) 后，低 B 位选桶，因为桶数 2^B，可用位运算代替取模；高 8 位存 tophash，用于桶内快速过滤。

4. tophash 有什么用？
存 hash 高 8 位，先比 tophash 再比完整 key，减少比较开销。还有特殊值：emptyOne、emptyRest、evacuatedX/Y 等。

5. 负载因子是多少？为什么？
经典实现是 6.5。每个桶 8 槽，平均超过 6.5 后溢出桶概率明显升高，查找退化，所以触发翻倍扩容。

6. 扩容触发条件？
- 负载因子 > 6.5：翻倍扩容，B+1，桶数 ×2。
- 溢出桶过多：等量扩容，B 不变，重新整理桶，减少溢出链。
条件大致：B<15 时 noverflow >= 2^B，否则 >= 2^15。

7. 扩容过程？
渐进式扩容。创建新桶，oldbuckets 指向旧桶，nevacuate 记录迁移进度。每次写/删触发迁移，至少迁移当前桶和 nevacuate 桶。读时若旧桶未迁移，会去旧桶读。迁移完释放旧桶。

8. 翻倍扩容和等量扩容区别？
翻倍：解决元素太多；等量：解决溢出桶太多但元素不多，让数据更紧凑。

9. 为什么 map 遍历顺序随机？
迭代器随机选起始 bucket 和 cell，且扩容迁移影响顺序。不要依赖遍历顺序。

10. 遍历中能删除吗？能新增吗？
删除安全，但可能删到未遍历的；新增不保证被遍历到。并发读写一定不安全。

11. map 并发安全吗？
不安全。并发读写可能 fatal error: concurrent map read and map write，并发写可能 concurrent map writes。运行时用 flags 检测，但不是 100% 必现。

12. nil map 和空 map 区别？
nil map 可读、len=0、可 range、delete 不 panic，但不能写，写会 panic。空 map 可读写。

13. map key 必须可比较吗？
是。slice、map、func 不能做 key；结构体含不可比较字段也不行。interface 可做 key，但动态类型必须可比较。

14. 为什么 map 元素不可取地址？
因为扩容/迁移会导致元素位置变化，&m[k] 会失效。所以不能直接改结构体字段：
tmp := m[k]; tmp.Field = x; m[k] = tmp。

15.删除元素会释放内存吗？
通常不会立即释放桶，只标记 emptyOne/emptyRest。大量删除后内存可能仍高，可重建 map。旧桶在扩容迁移后才释放。

16. map 会自动缩容吗？
不会。经典 map 只增不减，等量扩容也不减少 B。

17. hash0 作用？
随机种子，参与哈希，防止哈希碰撞攻击，使不同 map 实例哈希不同。

18. make(map, hint) 有什么用？
根据 hint 估算 B，预分配桶，减少扩容。

19. map 的 len 和 cap？
len 是元素个数；cap 不适用。

20. NaN 作为 key 的坑？
可以插入，但 NaN != NaN，查找和删除可能无法命中。range 能遍历到。

二、sync.Map 高频题
1. sync.Map 原理？
空间换时间，内部有 read 只读 map 和 dirty 可写 map。读多写少、key 稳定时性能好。

2. sync.Map 和 map+锁怎么选？
读多写少、key 基本不变：sync.Map。写多、需要 len、复杂范围操作：RWMutex + map 或分片锁。

3. sync.Map 适合写多吗？
不适合。写多会频繁操作 dirty，miss 多了还要提升 dirty，可能不如加锁 map。

4. sync.Map Range 是一致快照吗？
不是，不保证一致快照。

三、使用陷阱常考
- map 并发读写会 fatal，不是 panic 可 recover。
- map 元素不可寻址。
- nil map 可读不可写。
- map 遍历顺序随机。
- map 删除不缩容。
- map key 必须可比较。
- interface{} 做 key，动态类型不可比较会 panic。
- 大量增删的长期 map 建议定期重建。
四、算法题常考 Hash 题
- 两数之和：map 存 值 -> 下标。
- 字母异位词分组：排序字符串或计数数组做 key。
- 最长连续序列：set，找连续段起点。
- 无重复字符最长子串：滑动窗口 + map 记录位置。
- 和为 K 的子数组：前缀和 + map 计数。
- 四数相加 II：分组 map 计数。
- 三数之和：排序 + 双指针，去重。
- 有效的字母异位词：计数数组。
- 同构字符串 / 单词规律：双 map 映射。
- 快乐数：set 判环。
- 重复 DNA 序列：map 计数。
- 两个数组交集：set。
- 字符串第一个唯一字符：计数。
- LRU 缓存：map + 双向链表。
- LFU 缓存：map + 频率链表。
- 设计哈希集合/映射：数组 + 链表。
- 常数时间插入删除随机：数组 + map。
- 随机黑名单：map 映射。
- TinyURL：map 编解码。
- 数组中的第 K 个最大元素：哈希/堆/快排，但哈希不是最优。

五、背诵版一句话
Go map 经典结构是 hmap + bmap，桶内 8 槽，冲突挂溢出桶；负载因子 6.5 触发翻倍扩容，溢出桶过多触发等量扩容，扩容是渐进式；map 非并发安全，遍历随机，元素不可寻址，key 必须可比较，删除不缩容；读多写少可用 sync.Map。Go 1.24 后底层改为 Swiss Table。
</details>