import requests
import time
import os

# 服务器地址
BASE_URL = 'http://192.168.31.47:5001'

print("开始测试日志功能...")

# 测试1: 访问不存在的页面，触发404错误
print("\n测试1: 访问不存在的页面，触发404错误")
try:
    response = requests.get(f"{BASE_URL}/non_existent_page_12345")
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容长度: {len(response.text)} 字符")
except Exception as e:
    print(f"请求失败: {str(e)}")

# 等待1秒确保日志写入
print("等待1秒确保日志写入...")
time.sleep(1)

# 测试2: 使用test/404路由
print("\n测试2: 访问 /test/404 路由")
try:
    response = requests.get(f"{BASE_URL}/test/404")
    print(f"响应状态码: {response.status_code}")
except Exception as e:
    print(f"请求失败: {str(e)}")

# 等待1秒确保日志写入
print("等待1秒确保日志写入...")
time.sleep(1)

# 测试3: 访问 /test/logging 路由
print("\n测试3: 访问 /test/logging 路由")
try:
    response = requests.get(f"{BASE_URL}/test/logging")
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
except Exception as e:
    print(f"请求失败: {str(e)}")

# 等待1秒确保日志写入
print("等待1秒确保日志写入...")
time.sleep(1)

# 检查日志文件是否存在并包含内容
print("\n检查日志文件:")
log_dir = 'logs'
today = time.strftime('%Y%m%d')
log_filename = f'error_log_{today}.log'
log_path = os.path.join(log_dir, log_filename)

if os.path.exists(log_path):
    file_size = os.path.getsize(log_path)
    print(f"日志文件存在: {log_path}")
    print(f"日志文件大小: {file_size} 字节")
    
    if file_size > 0:
        print("日志文件不为空！")
        # 读取并显示日志文件的最后几行
        print("\n日志文件最后10行:")
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) > 10 else lines
                for line in last_lines:
                    print(line.strip())
        except Exception as e:
            print(f"读取日志文件失败: {str(e)}")
    else:
        print("警告: 日志文件为空！")
else:
    print(f"错误: 日志文件不存在: {log_path}")

print("\n测试完成！")