import os
import re

def check_template(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"检查文件: {file_path}")
        
        # 检查JavaScript代码块中的语法
        js_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        has_error = False
        
        for i, js_block in enumerate(js_blocks):
            print(f"  检查JavaScript代码块 {i+1}")
            
            # 检查花括号匹配
            open_curly = js_block.count('{')
            close_curly = js_block.count('}')
            if open_curly != close_curly:
                print(f"  错误: JavaScript代码块 {i+1} 存在花括号不匹配问题: 打开{open_curly}个，关闭{close_curly}个")
                has_error = True
                
                # 尝试找到问题行
                lines = js_block.split('\n')
                curly_diff = open_curly - close_curly
                current_diff = 0
                
                if curly_diff > 0:  # 有未闭合的左花括号
                    print("    可能的未闭合花括号位置:")
                    for j, line in enumerate(lines[:30]):  # 只检查前30行
                        current_diff += line.count('{') - line.count('}')
                        if line.count('{') > 0:
                            print(f"      第{j+1}行: {line.strip()[:50]}...")
                elif curly_diff < 0:  # 有多余的右花括号
                    print("    可能的多余右花括号位置:")
                    for j, line in enumerate(lines):
                        current_diff += line.count('{') - line.count('}')
                        if line.count('}') > 0:
                            print(f"      第{j+1}行: {line.strip()[:50]}...")
                            # 显示几行有多余花括号的位置后退出
                            if j > 30:
                                break
            
            # 检查括号匹配
            open_brackets = js_block.count('(')
            close_brackets = js_block.count(')')
            if open_brackets != close_brackets:
                print(f"  错误: JavaScript代码块 {i+1} 存在括号不匹配问题: 打开{open_brackets}个，关闭{close_brackets}个")
                has_error = True
            
            # 检查方括号匹配
            open_square = js_block.count('[')
            close_square = js_block.count(']')
            if open_square != close_square:
                print(f"  错误: JavaScript代码块 {i+1} 存在方括号不匹配问题: 打开{open_square}个，关闭{close_square}个")
                has_error = True
        
        return not has_error
    except Exception as e:
        print(f"文件 {file_path} 读取错误: {e}")
        return False

if __name__ == "__main__":
    templates_dir = "templates"
    files_to_check = [
        "training_materials.html",
        "products.html",
        "projects_list.html"
    ]
    
    all_valid = True
    for file_name in files_to_check:
        file_path = os.path.join(templates_dir, file_name)
        if not check_template(file_path):
            all_valid = False
    
    if all_valid:
        print("所有模板文件语法检查通过！")
    else:
        print("部分模板文件存在语法错误。")