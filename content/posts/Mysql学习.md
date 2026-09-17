---
title: 'Mysql学习'
date: 2026-09-17T19:22:53+08:00
draft: false
tags: ["mysql", "八股"]
---

# 前言

在使用很久Mysql后回来补充八股知识了

## 下载启动

这里只讲docker：
```bash
docker pull mysql:8.0
docker run -d --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=123456\
-v mysql-data:/var/lib/mysql\
--restart always\
mysql:8.0
```
进入：
```bash
docker exec -it mysql
```

## 指令

```bash
mysqlsh #进入mysqlsh客户端
mysql -h 127.0.0.1 -p 3306 -u root -p #传统命令行客户端,注意mysqlsh默认33060使用X协议
mysqldump -u root -p mifi test --where="id > 1000" > test.sql #将mifi库中的test表中的id大于1000的数据导出到test.sql中
mysql -u root -p mifi < test.sql #将表数据导入到mifi数据库中
SOURCE /path/to/dump.sql; #登录后也可以USE XXX然后通过这个导入
\help
\use xxx #使用xxx数据库
\sql #使用sql语法
\connect root@localhost #连接数据库
```

## SQL

语句
```sql
SHOW DATABASES; --查看库
CREATE DATABASE XXX; --创建XXX数据库
DROP DATABASE XXX; --删除XXX数据库
SELECT DATABASE(); --查看当前使用的数据库
USE XXX; --使用XXX数据库
SHOW TABLES; --查看当前数据库表
CREATE TABLE YYY (
  id INT,
  name VARCHAR(100),
  gold DECIMAL(10,2)
);
--创建YYY表
DESC YYY; --查看表结构
ALTER TABEL YYY MODIFY COLUMN name VARCHART(200) DEFAULT 'A'; --为YYY表修改name类型为VARCHAR(200)，默认值为'A'
ALTER TABEL YYY RENAME COLUMN name TO nick_name; --为YYY表修改name名为nick_name
ALTER TABLE YYY ADD COLUMN last_login DATETIME; --为YYY表添加列last_login,类型为datetime
ALTER TABLE YYY DROP COLUMN last_login; --删除YYY表中的last_login字段
DROP TABLE YYY; -- 删除YYY表
INSERT INTO YYY (id,name) VALUES (1,'mifi'); --向表添加数据，如果含所有列且顺序一致可以省略前面列的()，可以插入多条数据，用,隔开
SELECT * FROM YYY; --查询YYY表中的数据，*表示任意
UPDATE YYY SET NAME = 'B' WHERE NAME='A'; --将表YYY中name为'A'的行中的name修改为B
DELETE FROM YYY WHERE name='B'; --删除YYY表中name='B'的行
```

```bash

```
## 八股