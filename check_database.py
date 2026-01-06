#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查数据库结构脚本
用于列出SQLite数据库中的所有表和表结构
"""

import sqlite3
import os
import sys

def check_database_structure():
    """检查数据库结构并输出详细信息"""
    # 尝试多个可能的数据库路径
    db_paths = [
        r'f:\资料整理网站\instance\database.db',
        r'F:\资料整理网站\instance\database.db',
        os.path.join(os.getcwd(), 'instance', 'database.db'),
        os.path.abspath('instance/database.db')
    ]
    
    # 找到存在的数据库文件
    found_db = None
    for db_path in db_paths:
        if os.path.exists(db_path):
            found_db = db_path
            break
    
    if not found_db:
        print("错误: 未找到数据库文件")
        print("搜索的路径:")
        for path in db_paths:
            print(f"  - {path}")
        return False
    
    print(f"找到数据库文件: {found_db}")
    print(f"绝对路径: {os.path.abspath(found_db)}")
    print(f"文件大小: {os.path.getsize(found_db) / 1024:.2f} KB")
    print(f"文件修改时间: {os.path.getmtime(found_db)}")
    
    try:
        # 连接到SQLite数据库
        print("\n正在连接数据库...")
        conn = sqlite3.connect(found_db)
        cursor = conn.cursor()
        
        # 启用外键约束
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # 调试：打印所有SQLite master记录
        print("\nSQLite Master表内容:")
        cursor.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name;")
        all_master = cursor.fetchall()
        
        if not all_master:
            print("警告: sqlite_master表为空，数据库可能未正确初始化")
        else:
            print(f"找到 {len(all_master)} 条记录在sqlite_master中:")
            for item in all_master:
                print(f"  - 类型: {item[0]}, 名称: {item[1]}, 表名: {item[2]}")
                # 只显示表的SQL定义的前200个字符
                if item[3] and item[0] == 'table':
                    sql_preview = item[3][:200] + '...' if len(item[3]) > 200 else item[3]
                    print(f"    SQL: {sql_preview}")
        
        # 获取所有表名
        print("\n数据库中的所有表:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("警告: 数据库中没有表")
        else:
            print(f"找到 {len(tables)} 个表:")
            for i, (table_name,) in enumerate(tables, 1):
                print(f"  {i}. {table_name}")
                # 显示每个表的记录数
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    count = cursor.fetchone()[0]
                    print(f"     记录数: {count}")
                except Exception as e:
                    print(f"     获取记录数失败: {e}")
        
        # 检查所有可能的用户表名
        possible_user_tables = ['user', 'User', 'users', 'Users']
        user_table_found = None
        
        for table_name in possible_user_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
            if cursor.fetchone():
                user_table_found = table_name
                break
        
        if user_table_found:
            print(f"\n找到用户表: {user_table_found}")
            print(f"表结构:")
            cursor.execute(f"PRAGMA table_info({user_table_found});")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # 显示前5条用户记录
            print("\n用户记录（前5条）:")
            try:
                cursor.execute(f"SELECT id, username, role, role_level FROM {user_table_found} LIMIT 5;")
                users = cursor.fetchall()
                if users:
                    for user in users:
                        print(f"  - ID: {user[0]}, 用户名: {user[1]}, 角色: {user[2]}, 级别: {user[3]}")
                else:
                    print("  无用户记录")
            except Exception as e:
                print(f"  查询用户记录失败: {e}")
        else:
            print("\n未找到用户相关表")
        
        # 检查admin表
        print("\n检查admin表:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin';")
        if cursor.fetchone():
            print("找到admin表")
            cursor.execute("SELECT COUNT(*) FROM admin;")
            count = cursor.fetchone()[0]
            print(f"admin表记录数: {count}")
            if count > 0:
                cursor.execute("SELECT * FROM admin LIMIT 5;")
                admins = cursor.fetchall()
                print("admin表内容:")
                for admin in admins:
                    print(f"  - {admin}")
        else:
            print("未找到admin表")
        
        # 关闭连接
        cursor.close()
        conn.close()
        print("\n数据库检查完成")
        return True
        
    except sqlite3.Error as e:
        print(f"数据库操作错误: {e}")
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        return False

if __name__ == '__main__':
    check_database_structure()