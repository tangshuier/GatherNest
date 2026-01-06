#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动查询计算机IP地址并更新网站IP配置脚本

该脚本会自动查询计算机的局域网IP地址，并更新app.py中的FIXED_HOST变量，
以便服务器总是使用正确的IP地址启动。
"""

import socket
import os
import re
import subprocess
import platform
from datetime import datetime

def get_local_ip():
    """
    获取本地计算机的局域网IP地址
    尝试多种方法获取IP地址
    """
    # 方法1: 使用socket连接外部服务器来确定本地IP
    try:
        # 创建一个UDP套接字并连接到外部服务器
        # 这不会发送任何数据，但会帮助我们找到正确的网络接口
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"方法1 (socket连接): 检测到IP地址 {ip}")
        return ip
    except Exception as e:
        print(f"方法1失败: {e}")
    
    # 方法2: 在Windows上使用ipconfig命令
    if platform.system() == 'Windows':
        try:
            # 运行ipconfig命令获取网络配置
            result = subprocess.check_output('ipconfig', universal_newlines=True)
            # 使用正则表达式匹配IPv4地址（排除127.0.0.1）
            ipv4_pattern = r'IPv4 地址[\.: ]+([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})'
            matches = re.findall(ipv4_pattern, result)
            for match in matches:
                if not match.startswith('127.'):
                    print(f"方法2 (Windows ipconfig): 检测到IP地址 {match}")
                    return match
        except Exception as e:
            print(f"方法2失败: {e}")
    
    # 方法3: 获取所有网络接口的IP地址
    try:
        # 获取所有网络接口
        hostname = socket.gethostname()
        addresses = socket.gethostbyname_ex(hostname)[2]
        # 过滤掉回环地址和IPv6地址
        for addr in addresses:
            if not addr.startswith('127.') and ':' not in addr:
                print(f"方法3 (gethostbyname_ex): 检测到IP地址 {addr}")
                return addr
    except Exception as e:
        print(f"方法3失败: {e}")
    
    # 如果所有方法都失败，返回默认值
    print("警告: 无法检测到局域网IP地址，使用默认IP 127.0.0.1")
    return '127.0.0.1'

def update_app_py(ip_address):
    """
    更新app.py文件中的FIXED_HOST变量
    """
    app_py_path = 'f:\\资料整理网站\\app.py'
    
    if not os.path.exists(app_py_path):
        print(f"错误: 找不到文件 {app_py_path}")
        return False
    
    # 读取文件内容
    try:
        with open(app_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}")
        return False
    
    # 检查是否已有FIXED_HOST变量
    fixed_host_pattern = r'FIXED_HOST\s*=\s*["\'](.*?)["\']'
    if re.search(fixed_host_pattern, content):
        # 更新已存在的FIXED_HOST变量
        new_content = re.sub(fixed_host_pattern, 
                           f"FIXED_HOST = '{ip_address}'", 
                           content)
    else:
        # 如果不存在，在文件末尾添加（在if __name__ == '__main__':之前）
        main_pattern = r'if __name__ == ["\']__main__["\']:'
        if re.search(main_pattern, content):
            new_content = re.sub(main_pattern, 
                               f"# 配置固定IP地址\nFIXED_HOST = '{ip_address}'  # 自动生成的固定IP地址\n\n{main_pattern}", 
                               content)
        else:
            # 如果也找不到main块，直接在文件末尾添加
            new_content = content + f"\n\n# 配置固定IP地址\nFIXED_HOST = '{ip_address}'  # 自动生成的固定IP地址\n"
    
    # 写入更新后的内容
    try:
        with open(app_py_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"成功更新 {app_py_path} 中的FIXED_HOST为 {ip_address}")
        return True
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False

def save_ip_to_file(ip_address):
    """
    将IP地址保存到日志文件中
    """
    log_dir = 'f:\\资料整理网站\\计算机IP查询配置网站IP'
    log_file = os.path.join(log_dir, 'ip_address_log.txt')
    
    try:
        # 确保目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 写入IP地址和时间戳
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] 检测到IP地址: {ip_address}\n")
        print(f"已将IP地址记录到 {log_file}")
    except Exception as e:
        print(f"保存IP地址日志失败: {e}")

def restart_server():
    """
    尝试重启Flask服务器（可选功能）
    注意：这可能需要管理员权限，或者根据实际部署方式调整
    """
    print("\n提示：请手动重启Flask服务器以应用新的IP配置。")
    print("您可以使用以下命令重启服务器:")
    print("python f:\\资料整理网站\\app.py")

if __name__ == '__main__':
    print("=" * 60)
    print("自动IP地址配置脚本 v1.0")
    print("=" * 60)
    
    # 获取本地IP地址
    ip_address = get_local_ip()
    
    # 保存IP地址到日志
    save_ip_to_file(ip_address)
    
    # 更新app.py中的配置
    success = update_app_py(ip_address)
    
    if success:
        print("\n配置更新成功！")
        print(f"服务器现在将使用IP地址: {ip_address}:5001")
        restart_server()
    else:
        print("\n配置更新失败，请检查错误信息。")
    
    print("\n脚本执行完毕。")