import subprocess
import time
import os

print("启动服务器脚本...")

# 首先确保没有进程占用端口5001
try:
    print("检查端口占用情况...")
    # 使用netstat查找占用端口的进程
    netstat_cmd = ['netstat', '-ano']
    netstat_process = subprocess.Popen(netstat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, _ = netstat_process.communicate()
    
    # 查找占用5001端口的进程
    for line in stdout.splitlines():
        if ':5001' in line and 'LISTENING' in line:
            parts = line.split()
            pid = parts[-1]
            print(f"发现占用端口5001的进程，PID: {pid}")
            # 终止该进程
            taskkill_cmd = ['taskkill', '/PID', pid, '/F']
            subprocess.run(taskkill_cmd, check=True)
            print(f"已终止进程PID: {pid}")
            break
except Exception as e:
    print(f"检查端口时出错: {e}")

# 启动Flask服务器
print("启动Flask服务器...")
try:
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录（脚本所在目录的父目录）
    project_root = os.path.dirname(script_dir)
    # 使用项目根目录下的app.py
    app_path = os.path.join(project_root, 'app.py')
    
    # 使用subprocess在后台启动服务器
    server_process = subprocess.Popen(
        ['python', app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True  # 在Windows上使用shell=True可能更可靠
    )
    
    # 等待服务器启动
    time.sleep(3)
    
    # 检查服务器是否仍在运行
    if server_process.poll() is None:
        print("服务器已成功启动并正在运行!")
        print("访问地址: http://192.168.31.47:5001")
        print("按Ctrl+C停止脚本...")
        # 保持脚本运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止服务器...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("服务器已停止")
    else:
        print("服务器启动失败")
        stderr = server_process.stderr.read()
        print(f"错误信息: {stderr}")
except Exception as e:
    print(f"启动服务器时出错: {e}")