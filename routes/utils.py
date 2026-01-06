import os
import re
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov', 'wmv', 'md'}

def allowed_file(filename):
    print(f"检查文件类型: {filename}")
    result = '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    print(f"文件类型检查结果: {result}")
    return result

def validate_file_size(file, file_type=None):
    """
    根据文件类型验证文件大小
    
    Args:
        file: Flask文件对象
        file_type: 文件类型，可以是'video'、'engineering'、'image'等
    
    Returns:
        tuple: (is_valid, error_message)，is_valid为True表示文件大小有效，error_message为错误信息（如果有）
    """
    from flask import current_app
    
    # 根据文件类型获取对应的最大大小限制
    size_limits = {
        'video': current_app.config.get('MAX_VIDEO_SIZE', 200 * 1024 * 1024),
        'engineering': current_app.config.get('MAX_ENGINEERING_SIZE', 50 * 1024 * 1024),
        'image': current_app.config.get('MAX_IMAGE_SIZE', 10 * 1024 * 1024)
    }
    
    # 如果未指定文件类型，尝试根据扩展名推断
    if file_type is None and hasattr(file, 'filename'):
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext in ['mp4', 'avi', 'mov', 'wmv']:
            file_type = 'video'
        elif ext in ['zip', 'rar', '7z']:
            file_type = 'engineering'
        elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            file_type = 'image'
    
    # 获取对应的大小限制
    max_size = size_limits.get(file_type, current_app.config.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))
    max_size_mb = max_size / (1024 * 1024)
    
    # 获取文件大小
    if hasattr(file, 'content_length') and file.content_length:
        file_size = file.content_length
    else:
        # 如果content_length不可用，则读取文件获取大小
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
    
    # 验证文件大小
    if file_size > max_size:
        return False, f'文件过大，最大支持{max_size_mb}MB，当前文件大小：{file_size / 1024 / 1024:.2f}MB'
    
    return True, None

def validate_filename(filename):
    print(f"原始validate文件名: {filename}")
    # 移除文件名中的非法字符，但保留中文字符
    filename = re.sub(r'[\\/:*?"<>|]', '', filename)
    print(f"移除非法字符后: {filename}")
    
    # 确保文件名包含扩展名
    if '.' not in filename:
        print(f"文件名没有扩展名: {filename}")
        # 如果没有扩展名，默认添加.mp4（假设这是视频上传功能）
        filename += '.mp4'
        print(f"添加默认扩展名后: {filename}")
    
    # 限制文件名长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        print(f"文件名太长，截断: {name} -> {ext}")
        filename = name[:255 - len(ext)] + ext
    
    # 再次检查扩展名
    name, ext = os.path.splitext(filename)
    print(f"最终文件名 - 名称: {name}, 扩展名: {ext}")
    return filename

class FileUploader:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        # 确保上传文件夹存在
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
    
    def save_file(self, file):
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = validate_filename(filename)
            file_path = os.path.join(self.upload_folder, filename)
            file.save(file_path)
            return filename
        return None
    
    def delete_file(self, filename):
        file_path = os.path.join(self.upload_folder, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False