#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Python安全重命名数据库文件
"""

import os
import time
import subprocess
import sys

# 设置路径
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(PROJECT_ROOT, 'instance')
OLD_DB = os.path.join(INSTANCE_DIR, 'database.db')
TEMP_DB = os.path.join(INSTANCE_DIR, 'database_new.db')

def terminate_python_processes():
    """终止所有Python进程以释放文件锁"""
    print("正在终止Python进程...")
    try:
        # 使用taskkill终止所有python进程
        subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                      check=False, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        print("Python进程已终止")
    except Exception as e:
        print(f"终止进程时出错: {e}")

def wait_for_file_release(seconds=3):
    """等待文件锁释放"""
    print(f"等待{seconds}秒以释放文件锁...")
    time.sleep(seconds)

def delete_old_database():
    """删除旧数据库文件"""
    if os.path.exists(OLD_DB):
        print(f"删除旧数据库文件: {OLD_DB}")
        try:
            os.remove(OLD_DB)
            print("删除成功")
            return True
        except Exception as e:
            print(f"删除失败: {e}")
            return False
    else:
        print("旧数据库文件不存在，跳过删除")
        return True

def rename_database():
    """重命名临时数据库文件"""
    print(f"重命名临时数据库文件到: {OLD_DB}")
    try:
        os.rename(TEMP_DB, OLD_DB)
        print("重命名成功!")
        return True
    except Exception as e:
        print(f"重命名失败: {e}")
        return False

def check_database_exists():
    """检查临时数据库文件是否存在"""
    if not os.path.exists(TEMP_DB):
        print(f"错误: 临时数据库文件不存在 - {TEMP_DB}")
        return False
    
    # 检查文件大小
    file_size = os.path.getsize(TEMP_DB) / 1024
    print(f"找到临时数据库文件，大小: {file_size:.2f} KB")
    return True

def verify_database_content():
    """验证数据库内容"""
    if not os.path.exists(OLD_DB):
        return
    
    print("\n验证数据库内容:")
    import sqlite3
    
    try:
        conn = sqlite3.connect(OLD_DB)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if tables:
            print(f"找到 {len(tables)} 个表:")
            for i, (table_name,) in enumerate(tables, 1):
                print(f"  {i}. {table_name}")
                # 检查记录数
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"     记录数: {count}")
                
                # 显示用户表内容
                if table_name == 'user':
                    cursor.execute("SELECT id, username, role FROM user;")
                    users = cursor.fetchall()
                    print("     用户:")
                    for user in users:
                        print(f"       ID={user[0]}, 用户名={user[1]}, 角色={user[2]}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"检查数据库时出错: {e}")

def main():
    print("===== 数据库文件重命名工具 =====")
    
    # 检查临时文件
    if not check_database_exists():
        return 1
    
    # 终止Python进程
    terminate_python_processes()
    
    # 等待文件释放
    wait_for_file_release()
    
    # 删除旧数据库
    if not delete_old_database():
        print("\n建议手动操作:")
        print(f"  1. 确保没有程序使用数据库文件")
        print(f"  2. 将 {TEMP_DB} 重命名为 database.db")
        return 1
    
    # 重命名文件
    if rename_database():
        print("\n数据库重命名完成!")
        print(f"文件位置: {OLD_DB}")
        
        # 验证数据库内容
        verify_database_content()
        
        print("\n===== 数据库初始化成功 =====")
        print("超级管理员账户信息:")
        print("  用户名: admin")
        print("  密码: admin123")
        print("请使用上述凭据登录系统")
        return 0
    else:
        print("\n重命名失败，请手动操作:")
        print(f"  1. 关闭所有可能使用数据库的程序")
        print(f"  2. 手动将 {TEMP_DB} 重命名为 database.db")
        return 1

if __name__ == '__main__':
    sys.exit(main())