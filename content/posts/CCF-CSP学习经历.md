---
title: 'CCF CSP学习经历'
date: 2026-08-26T22:25:36+08:00
draft: false
tags: ["CCF", "CSP","竞赛"]
---

# 前言
CSP比赛我觉得是值得打的，相比于ACM肯定轻松点，相比蓝桥杯更重要点，而且学校有团体参加的话，报名费只要75元，蓝桥杯几百元太贵了。而且稍微看了下上次的题目，200分学习下好拿下，然后选择刷分或打CCF-CCSP。想着记录下比赛经历。

# 报名
首先进入[官网链接](https://passport.ccf.org.cn/sso/platform)，然后点击CSP报名，如果学校有团报一定要填团队报名，个人报名太贵了，然后个人信息有模拟考试的码，在模拟考试界面选择对应试卷填写兑换码，注意只能兑换一个试卷，且只有一次机会，但是考完后可以自由练习题目。

# 学习准备

## STL

- vector(向量/动态数组)：
  - 构造：vector<类型> arr（长度，[初值]）;
  - 二维数组：`vector<vector<int>> dp(5,vector<int> (6,10))`
  - 尾接：arr.push_back([数值]); 
  - 尾删: arr.pop_back();
  - 长度：arr.size();返回的值类型为size_t,*注意溢出*。
  - 清空：arr.clear();
  - 判断空：arr.empty();空则返回true。
  - 加长：arr.resize([长度],[默认值]);改长添加默认值，改段删除。
- stack(栈):
  - 构造：stack<类型> stk;
  - 进栈：stk.push([数据]);
  - 查看栈顶:stk.top();
  - 出栈：stk.pop();
  - 查看大小：stk.size();
  - 判空：stk.empty();
- queue(队列)：
  - 构造：queue<类型> que;
  - 进队：que.push([数据]);
  - 查看队首：que.front();
  - 从查看队尾：que.back();
  - 出队：que.pop();
  - 查看大小：que.size();
  - 判空：que.empty();
- priority queue(优先队列[堆]，本质为完全二叉树):
  - 构造：
    - 小顶堆：`priority_queue<类型,vector<类型>,greater<类型>> pque;`
    - 大顶堆：`priority_queue<类型> pque`
    - 第一个参数：存储数据类型
    - 第二个参数：存储数据类型的容器
    - 第三个参数：比较仿函数（`值更大的优先级更高：less<int> 值更小的优先级更高：greater<int>`）
  - 进堆（自动排序）：pque.push([数据]);
  - 出堆（堆顶）：pque.pop();
  - 取堆顶: pque.top();默认为大顶堆，
  - 补充：使用优先队列维持元素有序性，复杂度为$k\times\log n$而队列为$k\times n\times\log n$
- set(集合,底层为红黑树)：
  - 补充：set会自动排好序，可以用无序集合unordered_set,还有支持不互异的multiset
  - 构造：set<类型> st;
  - 插入：st.insert([数据]);
  - 查找：st.find(数据);返回的是迭代器，如果没有找到返回尾迭代器==st.end()
  - 查询个数：st.count(数据);
  - 清空：st.clear();
  - 判空：st.empty();
  - 遍历：
    - 声明迭代器：`set<int>::iterator it `
    - 遍历：
      ```c++
      for(set<int>::iterator it= st.begin();it != st.end();++it{
        cout<<*it<<endl;
      }
      ```
- map(字典)：
  - 构造：map<类型，类型> m；有序，互异
    - multimap：有序，不互异
    - unordered_map：互异，无序
  - 遍历：迭代器——map<类型，类型>::iterator it，例子:`for(auto &pr:m){cout<<pr.first<<pr.second<<endl;}`first为键，second为值。
  - 查询：m.find(数据);同样返回迭代器（找不到返回尾迭代器m.end()）。
  - 删除：m.erase(数据);
  - 查找个数：m.count(数据);
  - 判空：m.empty();
  - 查看大小:m.size();
  - 清空：m.clear();
  - 头迭代器：m.begin();
  - 尾迭代器：m.end();
- string(字符串):
  - 构造：string s;
  - 注意：用scanf和printf无法直接用string，写入需要用char[]帮忙转接，输出需要s.c_str().
  - 获取子串：s.substr(下标，长度);
  - 查找：s.find("数据");没找到返回string::npos，返回起始点下标。
  - 转换：stoll，stold，stoi......即sto什么。
  - *优化1*：尾接字符串用s+="a"而不是s = s+"a",相当于减少临时变量的开销
  - 注意：find()复杂度为$O(n^2)$
- pair(二元组)：
  - 构造：pair<类型，类型> p;
    - `pair<int,int> p1 = make_pair(1,2)`
    - `pair<int,int> p2 = {1,2}`
  - 访问：p.first访问第一个元素，p.second访问第二个元素。
  - 判同："=="

注意尽量不要用迭代器操作容器

## 算法

### 算法函数/数学函数

- swap(a,b):交换a，b数据
- `sort(arr.begin(),arr.end(),cmp)`:可以对数组排序
  - 自定义比较器：
    ```c++
    bool cmp(pair<int,int> a,pair<int,int> b){
      //第二位从小到大
      if(a.second != b.second){
        return a.second < b.second;//当返回true代表无需交换位置
        }
      //第一位从大到小
      return a.first > b.first;//注意==必须返回false
      }
      //`这里的`pair<int,int>`就是sort中arr的类型，可变
    ```
- 二分查找(前提有序)
  - lower_bound(arr.begin(),arr.end(),c):查找>=c的元素迭代器位置
  - upper_bound(arr.begin(),arr.end(),c):查找>c的元素迭代器位置
- reverse(arr.begin(),arr.end())：按迭代器位置反转数据
- max(a,b)：取最大值
- min(a,b)：取最小值
- unique(arr.begin(),arr.end())：消除数组的重复*相邻*元素，长度不变，单有效数据缩短，返回有效数据位置的结尾迭代器
  
  例如：{0,1,1,2,3,4,4,5} ---> {0,1,2,3,4,5,?,?}

- 数学公式：
  | 公式 | 示例 |
  | ---- | ---- |
  | $f(x)=\mid x\mid$ | `abs(-1.0)` |
  | $f(x)=e^x$ | `exp(2)` |
  | $f(x)=\ln x$ | `log(3)` |
  | $f(x,y)=x^y$ | `pow(2, 3)` |
  | $f(x)=\sqrt{x}$ | `sqrt(2)` |
  | $f(x)=\lceil x\rceil$(向上取整) | `ceil(2.1)` |
  | $f(x)=\lfloor x\rfloor$（向下取整） | `floor(2.1)` |
  | $f(x)=\text{round}(x)$(四舍五入) | `round(2.1)` |

  所有函数参数均支持 int / long long / float / double / long double

  注意事项：

  由于浮点误差，有些数学函数的行为可能与预期不符，导致 WA。如果你的操作数都是整型，那么用下面的写法会更稳妥。

  - $\lfloor \frac{a}{b} \rfloor$
    - 别用：`floor(1.0 * a / b)`
    - 要用：`a / b`

  - $\lceil \frac{a}{b} \rceil$
    - 别用：`ceil(1.0 * a / b)`
    - 要用：`(a + b - 1) / b` （$\lceil \frac{a}{b} \rceil=\lfloor \frac{a+b-1}{b} \rfloor$）

  - $\lfloor \sqrt{a} \rfloor$
    - 别用：`(int)sqrt(a)`
    - 要用：二分查找

  - $a^b$
    - 别用：`pow(a, b)`
    - 要用：快速幂

  - $\lfloor \log_2 a \rfloor$
    - 别用：`log2(a)`
    - 要用：`__lg`（不规范，但是竞赛可用） / `bit_width`（C++20 可用）

- gcd()/lcm():返回最大公因数/最小公倍数，如果是GNU编译器，用__gcd().



