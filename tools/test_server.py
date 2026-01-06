import requests
import time

print("开始测试服务器日志记录功能...")

# 测试URL
BASE_URL = "http://192.168.31.47:5001"

test_endpoints = [
    "/",  # 首页
    "/login",  # 登录页面
    "/register"  # 注册页面
]

# 发送测试请求
for endpoint in test_endpoints:
    url = BASE_URL + endpoint
    print(f"\n发送请求到: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"响应状态码: {response.status_code}")
        print(f"响应大小: {len(response.content)} 字节")
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
    
    # 等待1秒
    time.sleep(1)

print("\n测试完成！请查看服务器日志确认是否记录了这些请求。")