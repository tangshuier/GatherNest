#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的数据库文件重命名脚本
"""

import os
import time
import shutil

# 设置路径
INSTANCE_DIR = "F:\资料整理网站\instance"
OLD_DB = os.path.join(INSTANCE_DIR, 'database.db')
TEMP_DB = os.path.join(INSTANCE_DIR, 'database_new.db')

print("===== 数据库文件重命名工具 =====")

# 检查临时文件是否存在
if not os.path.exists(TEMP_DB):
    print(f"错误: 临时数据库文件不存在 - {TEMP_DB}")
    exit(1)

print(f"临时数据库文件: {TEMP_DB}")
print(f"大小: {os.path.getsize(TEMP_DB) / 1024:.2f} KB")

# 等待1秒
print("等待1秒...")
time.sleep(1)

# 尝试删除旧文件
if os.path.exists(OLD_DB):
    print(f"尝试删除旧数据库文件: {OLD_DB}")
    try:
        os.remove(OLD_DB)
        print("旧文件删除成功")
    except Exception as e:
        print(f"警告: 无法删除旧文件: {e}")
        print("将尝试直接复制文件...")
        # 尝试复制而不是重命名
        try:
            shutil.copy2(TEMP_DB, OLD_DB + '.new')
            print(f"已创建副本: {OLD_DB}.new")
            print("请手动将其重命名为 database.db")
            exit(0)
        except Exception as e:
            print(f"复制失败: {e}")

# 尝试重命名
print(f"尝试重命名文件到: {OLD_DB}")
try:
    os.rename(TEMP_DB, OLD_DB)
    print("重命名成功!")
    
    # 验证文件是否存在
    if os.path.exists(OLD_DB):
        print(f"\n数据库文件已准备就绪:")
        print(f"  位置: {OLD_DB}")
        print(f"  大小: {os.path.getsize(OLD_DB) / 1024:.2f} KB")
        print("\n超级管理员账户信息:")
        print("  用户名: admin")
        print("  密码: admin123")
        print("请使用上述凭据登录系统")
    else:
        print("错误: 文件重命名后不存在")
        exit(1)
        
    # 尝试简单验证数据库内容
    try:
        import sqlite3
        print("\n验证数据库内容:")
        conn = sqlite3.connect(OLD_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if tables:
            print(f"找到 {len(tables)} 个表:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("警告: 数据库中没有表")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"数据库检查失败: {e}")
        print("请手动检查数据库")
        
    exit(0)
    
except Exception as e:
    print(f"重命名失败: {e}")
    print("\n===== 手动操作指南 =====")
    print("请按照以下步骤手动操作:")
    print(f"1. 关闭所有可能使用数据库的程序")
    print(f"2. 打开文件资源管理器，导航到: {INSTANCE_DIR}")
    print(f"3. 删除 'database.db' 文件（如果存在）")
    print(f"4. 将 'database_new.db' 重命名为 'database.db'")
    print("\n超级管理员账户信息:")
    print("  用户名: admin")
    print("  密码: admin123")
    exit(1)