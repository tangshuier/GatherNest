#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单的Jinja2模板语法检查器
"""

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
import os

# 只检查基本语法，不尝试渲染
print("开始检查模板语法...")
try:
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录（脚本所在目录的父目录）
    project_root = os.path.dirname(script_dir)
    # 初始化Jinja2环境，使用项目根目录下的templates文件夹
    template_dir = os.path.join(project_root, 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    
    # 读取模板文件内容
    template_path = os.path.join(template_dir, 'projects_list.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 编译模板（只检查语法）
    env.parse(template_content)
    
    print("✓ 模板语法检查通过！没有发现语法错误。")
    
except TemplateSyntaxError as e:
    print(f"✗ 发现模板语法错误！")
    print(f"  错误位置: 第{e.lineno}行")
    print(f"  错误信息: {e.message}")
    # 显示错误行附近的内容
    lines = template_content.split('\n')
    start_line = max(0, e.lineno - 2)
    end_line = min(len(lines), e.lineno + 2)
    print("  上下文:")
    for i in range(start_line, end_line):
        line_num = i + 1
        prefix = '>>> ' if line_num == e.lineno else '    '
        print(f"{prefix}{line_num}: {lines[i]}")
    
except Exception as e:
    print(f"✗ 检查过程中出现错误:")
    print(f"  {type(e).__name__}: {e}")