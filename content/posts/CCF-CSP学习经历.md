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

### 算法技术

#### 前缀和数组，差分

- 前缀和数组；数组前n个数值和的数组，通常用于数组区间求和，时间复杂度从$O(n^2)$到$O(n)$。
  
  满足：`b[i] = a[i] + b[i-1].`
- 差分：将数组相邻元素之差存储到新数组中，通常用于求区间更改问题，对于数组a[]，在区间[l,r]所有元素加上x，只需在差分数组上的l处增加x，在r+1处减去x然后求前缀和。

  满足：`b[i] = a[i] - a[i-1]`

差分数组的前缀和为原数组，前缀和数组的差分也为原数组。

经典例题：

输入v头奶牛，第i个在m~n挤奶，需要q个桶，其中1<=q<=10,1<=m<=n<=1000,1<=v<=100,求需要的最小奶桶总数。

输入：
```bash
3
4 10 1
8 13 3
2 6 2
```
输出：
```bash
4
```
代码详解：
```c++
#include<bits/stdc++.h>
using namespace std;
int a[1024];
int m = 0;
int k = 0,v = 0,j = 0;;
int h = 0;
int res = 0;
int main(){
  while(scanf("%d",&m) != EOF){
    for(int i = 0;i < m;i++){
        scanf("%d %d %d",&k,&v,&j);
        a[k - 1] += j;
        a[v] += -j;
    }
    for(int i = 0;i < 1000;i++){
        h += a[i]; 
        res = max(res,h);
    }
    printf("%d",res);
  }
  return 0;
}
```
还有二维前缀和矩阵，二维差分矩阵，底层同样的逻辑，无需过多赘述。

#### 二分
二分查找：（利用有序的数据每次缩小一半查找数据）

通过中间数大小对比不断更改左右边界，来查询数据。

例：

给定长度为n`(1<n<1e6）`的非降序列，元素取值范围在`(0-1e9)`之间，另有m`(1<=m<=1e4)`个询问值，取值与元素一致，对每个询问值找出最接近它的元素值（若有多个满足条件，输出最小的）。
```
输入：
3
2 5 8
2
10
5
输出：
8
5
```
```c++
#include<bits/stdc++.h>
using namespace std;

const int as = 1e6+1;
const int bs = 1e4+1;
int length = 0;
int num = 0;
int a[as];
int b[bs];
int main(){
    while(scanf("%d",&length)){
        for(int i = 0;i < length;i++){
            scanf("%d",&a[i]);
        }
        scanf("%d",&num);
        for(int i = 0;i < num;i++){
            int aim = 0;
            scanf("%d",&aim);
            int l = 0,r = 0;
            if(aim <= a[0]){
                b[i] = a[0];
                continue;
            }else if(aim >= a[length-1]){
                b[i] = a[length - 1];
                continue;
            }
            while(l < r){
                int mid = (l+r+1)>>2;
                if(a[mid] > aim){
                     r = mid;
                }else if(a[mid] < aim){ 
                    l = mid;
                }else{
                    l = mid;
                    break;
                }
            }
            b[i] = abs(a[l] - aim) > abs(a[l+1] - aim)?a[l+1]:a[l];
        }
        for(int i = 0;i < num;i++){
            printf("%d",b[i]);
            printf("\n");
        }
    }
    return 0;
}
```

STL中常用的二分函数：
```c++
bool binary_search(ForwardIt first,ForwardIt last,const T& value);
/*
用于判断元素是否在有序序列中
first，last为迭代器范围（左闭右开）
value为查找的值
*/
ForwardIt lower_bound(ForwardIt first,ForwardIt last,const T& value);
/*
用于查找到第一个不小于目标值的元素位置
first，last为迭代器范围（左闭右开）
value为查找值
返回第一个>=value元素的迭代器，找不到则返回last，即末尾
*/
ForwardIt upper_bound(ForwardIt first,ForwardIt last,const T& value);
/*
查找第一个大于目标值的元素位置
返回第一个>value的元素的 迭代器
*/
```

#### 动态规划(DP)

利用小问题的答案求解大问题，常采用*递推*或*记忆化搜索*实现

- 重叠子问题：子问题是大问题的小版本
- 最优性原理：大问题的最优解包含小问题的最优解
- 无后效性原则：后续阶段不受前一阶段影响

典型例题(打家劫舍 II)

你是一个专业的小偷，计划偷窃沿街的房屋，每间房内都藏有一定的现金。这个地方所有的房屋都围成一圈 ，这意味着第一个房屋和最后一个房屋是紧挨着的。同时，相邻的房屋装有相互连通的防盗系统，如果两间相邻的房屋在同一晚上被小偷闯入，系统会自动报警 。

给定一个代表每个房屋存放金额的非负整数数组，计算你 在不触动警报装置的情况下 ，今晚能够偷窃到的最高金额。

```
输入：nums = [2,3,2]
输出：3
解释：你不能先偷窃 1 号房屋（金额 = 2），然后偷窃 3 号房屋（金额 = 2）, 因为他们是相邻的。
```
```c++
/*
 * @lc app=leetcode.cn id=213 lang=cpp
 *
 * [213] 打家劫舍 II
 */

// @lc code=start
#include<bits/stdc++.h>
using namespace std;
class Solution {
public:
    int rob(vector<int>& nums) {
        vector<int> money1(100,0);//不需要第一个
        vector<int> money2(100,0);
        int location = nums.size();
        if(location == 1){
            return nums[0];
        }else if(nums.size() == 2){
            return max(nums[0],nums[1]);
        }
        money1[1] = nums[1];
        money2[1] = nums[0];
        money2[0] = nums[0];
        for(int i = 2;i < location;i++){
            money1[i] = max(money1[i-1],money1[i-2]+nums[i]);
            if(i == location-1){
                money2[i] = money2[i-1];
                break;
            }
            money2[i] = max(money2[i-1],money2[i-2] + nums[i]);
        }
        return max(money1[location-1],money2[location-1]);
        
    }
};
// @lc code=end
```

#### 深度优先搜索(DFS)

一直遍历到头后从拐弯点继续,理论是栈实现，涉及递归。

应用场景：
- 图的连通性判断
- 路径搜索
- 组合问题...

典型例题：
按照国际象棋的规则，皇后可以攻击与之处在同一行或同一列或同一斜线上的棋子。

n 皇后问题 研究的是如何将 n 个皇后放置在 n×n 的棋盘上，并且使皇后彼此之间不能相互攻击。

给你一个整数 n ，返回所有不同的 n 皇后问题 的解决方案。

每一种解法包含一个不同的 n 皇后问题 的棋子放置方案，该方案中 'Q' 和 '.' 分别代表了皇后和空位。
```
输入：n = 4
输出：[[".Q..","...Q","Q...","..Q."],["..Q.","Q...","...Q",".Q.."]]
解释：如上图所示，4 皇后问题存在两个不同的解法。
```

```c++
/*
 * @lc app=leetcode.cn id=51 lang=cpp
 *
 * [51] N 皇后
 */

// @lc code=start
#include<bits/stdc++.h>
using namespace std;
class Solution {
public:
    vector<vector<string>> solveNQueens(int n) {
        vector<bool> lie(n,false);
        vector<bool> zh(2*n,false);
        vector<bool> fh(2*n,false);
        vector<vector<string>> res;
        vector<string> map(n,string(n,'.'));
        BFS(0,n,lie,zh,fh,res,map);
        return res;
    }
    void BFS(int x,int n,
        vector<bool> &l,vector<bool> &z,vector<bool> &f,
        vector<vector<string>> &r,
        vector<string> &now){
        if(x == n){
            r.push_back(now);
            return;
        }
        for(int i = 0;i < n;i++){
            if(l[i] || z[x+i] || f[x-i+n]){
                continue;
            }
            now[x][i] = 'Q';
            l[i] = true;
            z[x+i] = true;
            f[x-i+n] = true;
            BFS(x+1,n,l,z,f,r,now);
            l[i] = false;
            z[x+i] = false;
            f[x-i+n] = false;
            now[x][i] = '.';
        }

    }
};
// @lc code=end
```
#### 广度优先搜索(BFS)

类似洪水一样发散寻找，理论是队列实现。

