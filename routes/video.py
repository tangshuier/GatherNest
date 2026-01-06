from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
import time
import re
from .utils import allowed_file, validate_filename
from .decorators import role_required

video_bp = Blueprint('video', __name__)

# 视频上传目录
VIDEO_UPLOAD_FOLDER = os.path.join('static', 'uploads', 'videos')

# 确保视频上传目录存在
if not os.path.exists(VIDEO_UPLOAD_FOLDER):
    os.makedirs(VIDEO_UPLOAD_FOLDER, exist_ok=True)
    print(f"创建视频上传目录: {VIDEO_UPLOAD_FOLDER}")
# 检查目录权限
if os.path.exists(VIDEO_UPLOAD_FOLDER) and not os.access(VIDEO_UPLOAD_FOLDER, os.W_OK):
    print(f"警告: 视频上传目录没有写入权限: {VIDEO_UPLOAD_FOLDER}")

@video_bp.route('/upload_video', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def upload_video():
    """管理员上传视频文件的功能"""
    if request.method == 'POST':
        try:
            # 检查文件是否存在
            if 'video_file' not in request.files:
                flash('请上传视频文件', 'danger')
                return redirect(request.url)
                
            file = request.files['video_file']
            
            # 检查是否选择了文件
            if file.filename == '':
                flash('没有选择文件', 'danger')
                return redirect(request.url)
                
            # 检查文件类型是否允许
            if file and allowed_file(file.filename):
                # 检查文件大小是否超过视频限制
                if file.content_length > current_app.config.get('MAX_VIDEO_SIZE', 200 * 1024 * 1024):
                    max_size_mb = current_app.config.get('MAX_VIDEO_SIZE', 200 * 1024 * 1024) / (1024 * 1024)
                    flash(f'文件大小超过限制，最大允许 {max_size_mb}MB', 'danger')
                    return redirect(request.url)
                # 添加调试信息，追踪文件名处理过程
                print(f"原始文件名: {file.filename}")
                
                # 自定义的中文文件名处理逻辑，更好地保留原始中文名称
                # 首先获取文件扩展名
                original_name, ext = os.path.splitext(file.filename)
                print(f"原始文件名: {original_name}, 扩展名: {ext}")
                
                # 仅移除文件名中的非法字符，保留中文和其他安全字符
                # 这比使用secure_filename更好，因为它不会移除中文字符
                safe_name = re.sub(r'[\\/:*?"<>|]', '', original_name)
                
                # 如果处理后文件名为空，则使用时间戳作为默认名称
                if not safe_name:
                    safe_name = str(int(time.time()))
                
                # 确保扩展名格式正确
                ext = ext.lower()
                if not ext:
                    ext = '.mp4'  # 默认使用.mp4扩展名
                elif ext not in ['.mp4', '.avi', '.mov', '.wmv']:
                    ext = '.mp4'  # 限制为支持的视频格式
                
                # 重新组合文件名
                filename = f"{safe_name}{ext}"
                print(f"自定义处理后文件名: {filename}")
                
                # 应用自定义的文件名验证
                filename = validate_filename(filename)
                print(f"应用validate_filename后: {filename}")
                
                # 保存文件
                file_path = os.path.join(VIDEO_UPLOAD_FOLDER, filename)
                print(f"保存路径: {file_path}")
                print(f"目录名: {os.path.dirname(file_path)}")
                print(f"文件名: {os.path.basename(file_path)}")
                print(f"路径是否存在: {os.path.exists(file_path)}")
                print(f"是否为目录: {os.path.isdir(file_path)}")
                
                # 重要修复：检查文件名，确保扩展名不会被当作目录名处理
                # 特别是处理static/uploads/videos/mp4这种情况
                if os.path.isdir(file_path):
                    # 如果文件路径已经是一个目录，则修改文件名以避免冲突
                    base_name, ext = os.path.splitext(filename)
                    # 使用更具体的方式处理冲突，避免所有文件都变成相似的名称
                    new_filename = f"{base_name}_{int(time.time())}{ext}"
                    file_path = os.path.join(VIDEO_UPLOAD_FOLDER, new_filename)
                    # 同时更新filename变量，确保前端显示的文件名与实际保存的一致
                    filename = new_filename
                    print(f"文件路径已存在为目录，修改为: {file_path}")
                
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # 保存文件，添加错误处理
                try:
                    file.save(file_path)
                    flash(f'视频文件 "{filename}" 上传成功', 'success')
                except Exception as e:
                    print(f"文件保存错误: {str(e)}")
                    # 检测权限错误并显示中文提示
                    if 'Permission denied' in str(e) or '权限' in str(e):
                        flash(f'文件保存失败: 没有写入权限，请检查文件夹权限设置。路径: {file_path}', 'danger')
                    else:
                        flash(f'文件保存失败: {str(e)}', 'danger')
                    return redirect(url_for('video.upload_video'))
                
                return redirect(url_for('video.upload_video'))
            else:
                flash('不支持的文件类型，请上传 MP4、AVI、MOV 或 WMV 格式的视频', 'danger')
                return redirect(request.url)
        except Exception as e:
            print(f"上传处理错误: {str(e)}")
            flash(f'上传过程发生错误: {str(e)}', 'danger')
            return redirect(request.url)
            
    # 获取当前已上传的视频列表
    videos = []
    if os.path.exists(VIDEO_UPLOAD_FOLDER):
        videos = [f for f in os.listdir(VIDEO_UPLOAD_FOLDER) if allowed_file(f)]
        
    return render_template('upload_video.html', videos=videos)

@video_bp.route('/serve_video/<filename>')
def serve_video(filename):
    """提供视频文件下载或流式传输，优化视频质量"""
    # 使用绝对路径以确保在Windows环境下正确工作
    video_upload_folder = os.path.join(current_app.root_path, VIDEO_UPLOAD_FOLDER)
    file_path = os.path.join(video_upload_folder, filename)
    print(f"服务视频文件: {filename} 来自: {video_upload_folder}")
    
    # 确保文件存在
    if not os.path.exists(file_path):
        return "文件不存在", 404
    
    # 获取文件扩展名以设置正确的Content-Type
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv'
    }
    content_type = mime_types.get(ext, 'application/octet-stream')
    
    # 使用send_file替代send_from_directory，以便更好地控制响应头
    from flask import send_file
    
    # 发送文件，设置适当的响应头以确保高质量视频传输
    response = send_file(
        file_path,
        mimetype=content_type,
        as_attachment=False,  # 在线播放而不是下载
        conditional=True,     # 启用条件请求以支持断点续传
        etag=True,            # 添加ETag支持缓存优化
        last_modified=os.path.getmtime(file_path)  # 添加最后修改时间
    )
    
    # 添加额外的响应头以优化视频播放
    response.headers['Accept-Ranges'] = 'bytes'  # 启用范围请求
    response.headers['Cache-Control'] = 'public, max-age=31536000'  # 长期缓存
    response.headers['X-Content-Type-Options'] = 'nosniff'  # 防止MIME类型嗅探
    
    # 禁用任何可能的压缩，以确保视频质量不被降低
    response.headers['Content-Encoding'] = 'identity'
    
    return response

@video_bp.route('/delete_video/<filename>')
@login_required
@role_required('admin')
def delete_video(filename):
    """管理员删除视频文件"""
    video_upload_folder = current_app.config['VIDEO_UPLOAD_FOLDER']
    file_path = os.path.join(video_upload_folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f'视频文件 "{filename}" 已删除', 'success')
        print(f"删除视频文件: {file_path}")
    else:
        print(f"删除失败，文件不存在: {file_path}")
        flash('视频文件不存在', 'danger')
    return redirect(url_for('video.upload_video'))