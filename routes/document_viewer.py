from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file
from flask_login import login_required, current_user
import os
import zipfile
import tarfile
import tempfile
import json
import urllib.parse
import logging
from docx import Document

from routes.models import Document, User, Project, db
from routes.decorators import admin_required, engineer_required

document_viewer_bp = Blueprint('document_viewer', __name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取压缩包文件结构
def get_archive_structure(archive_path):
    """解析压缩包文件结构，支持ZIP和TAR.GZ格式"""
    file_structure = {'name': os.path.basename(archive_path), 'type': 'directory', 'children': []}
    
    try:
        # 处理ZIP文件
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                _build_zip_structure(zip_ref, file_structure)
        
        # 处理TAR文件
        elif archive_path.endswith(('.tar.gz', '.tgz')):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                _build_tar_structure(tar_ref, file_structure)
        
        return file_structure
        
    except Exception as e:
        logger.error(f"解析压缩文件结构失败: {str(e)}")
        return None

def _build_zip_structure(zip_ref, file_structure):
    """构建ZIP文件的目录结构"""
    for info in zip_ref.infolist():
        file_path = info.filename
        # 规范化路径，统一使用正斜杠
        normalized_path = file_path.replace('\\', '/')
        
        # 分割路径
        path_parts = normalized_path.split('/')
        current_level = file_structure['children']
        
        # 构建目录结构
        for i, part in enumerate(path_parts):
            if not part:  # 跳过空部分
                continue
                
            # 检查当前部分是否已存在
            found = False
            for item in current_level:
                if item['name'] == part:
                    current_level = item['children']
                    found = True
                    break
            
            # 如果不存在，创建新项
            if not found:
                is_dir = i < len(path_parts) - 1 or normalized_path.endswith('/')
                new_item = {
                    'name': part,
                    'type': 'directory' if is_dir else 'file',
                    'path': normalized_path,
                    'children': [] if is_dir else None
                }
                current_level.append(new_item)
                current_level = new_item['children'] if is_dir else current_level

def _build_tar_structure(tar_ref, file_structure):
    """构建TAR文件的目录结构"""
    for member in tar_ref.getmembers():
        file_path = member.name
        # 规范化路径
        normalized_path = file_path.replace('\\', '/')
        
        # 分割路径
        path_parts = normalized_path.split('/')
        current_level = file_structure['children']
        
        # 构建目录结构
        for i, part in enumerate(path_parts):
            if not part:
                continue
                
            # 检查当前部分是否已存在
            found = False
            for item in current_level:
                if item['name'] == part:
                    current_level = item['children']
                    found = True
                    break
            
            # 如果不存在，创建新项
            if not found:
                is_dir = member.isdir() or i < len(path_parts) - 1
                new_item = {
                    'name': part,
                    'type': 'directory' if is_dir else 'file',
                    'path': normalized_path,
                    'children': [] if is_dir else None
                }
                current_level.append(new_item)
                current_level = new_item['children'] if is_dir else current_level

# 从压缩包中读取文件内容
def read_file_from_archive(archive_path, file_path):
    """从压缩包中读取指定文件的内容"""
    try:
        # URL解码
        decoded_path = urllib.parse.unquote(file_path)
        # 规范化路径
        normalized_path = decoded_path.replace('\\', '/')
        
        # 处理ZIP文件
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # 检查文件是否存在
                if normalized_path not in zip_ref.namelist():
                    # 尝试模糊匹配
                    for item in zip_ref.namelist():
                        if item.endswith('/'):
                            continue
                        if normalized_path in item or item in normalized_path:
                            normalized_path = item
                            break
                    else:
                        return None
                
                # 读取文件内容
                content = zip_ref.read(normalized_path)
                return content
        
        # 处理TAR文件
        elif archive_path.endswith(('.tar.gz', '.tgz')):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                try:
                    member = tar_ref.getmember(normalized_path)
                    content = tar_ref.extractfile(member).read()
                    return content
                except KeyError:
                    # 文件不存在
                    return None
        
    except Exception as e:
        logger.error(f"从压缩包读取文件失败: {str(e)}")
    
    return None

# JSON清理函数
def clean_json_data(obj):
    """清理数据结构，确保可以安全地进行JSON序列化"""
    if isinstance(obj, dict):
        clean_obj = {}
        for k, v in obj.items():
            if v is None:
                continue
            elif isinstance(v, (dict, list)):
                clean_obj[k] = clean_json_data(v)
            elif isinstance(v, str):
                # 清理字符串中的特殊字符
                clean_str = v.replace('\\', '/')
                clean_str = clean_str.replace('\\\\', '/')
                clean_str = clean_str.replace('\/', '/')
                # 移除控制字符
                for char in ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', 
                            '\x08', '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12',
                            '\x13', '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a',
                            '\x1b', '\x1c', '\x1d', '\x1e', '\x1f']:
                    clean_str = clean_str.replace(char, '')
                
                clean_obj[k] = clean_str
            else:
                clean_obj[k] = v
        return clean_obj
    elif isinstance(obj, list):
        return [clean_json_data(v) for v in obj if v is not None]
    elif isinstance(obj, str):
        # 基础清理
        clean_str = obj.replace('\\', '/')
        clean_str = clean_str.replace('\\\\', '/')
        return clean_str
    return obj

# 查看文档
@document_viewer_bp.route('/view_document/<int:document_id>')
@login_required
@engineer_required
def view_document(document_id):
    """查看文档内容，支持不同类型的文件"""
    try:
        # 查找文档
        document = Document.query.get(document_id)
        
        if not document:
            logger.error(f"文档不存在: ID={document_id}")
            flash(f'文档不存在: ID={document_id}', 'danger')
            return redirect(url_for('project_management.projects_list'))

        # 检查文件是否存在
        if not os.path.exists(document.filepath):
            logger.error(f"文件不存在: {document.filepath}")
            flash(f'文件不存在: {document.filepath}', 'danger')
            return redirect(url_for('project_management.projects_list'))
        
        # 根据文件类型处理
        file_extension = os.path.splitext(document.filepath)[1].lower()

        # 处理压缩文件
        if file_extension in ['.zip', '.tar.gz', '.tgz']:
            return _handle_archive_document(document, file_extension)
        
        # 处理Word文档
        elif file_extension == '.docx':
            return _handle_word_document(document)
        
        # 处理文本文件
        elif file_extension in ['.txt', '.html', '.htm', '.js', '.css', '.json', '.xml', '.py', '.php']:
            return _handle_text_document(document, file_extension)
        
        # 其他文件类型，提供下载
        else:
            return _handle_download_document(document)
        
    except Exception as e:
        logger.error(f"查看文档时出错: {str(e)}")
        flash(f'查看文档时出错: {str(e)}', 'danger')
        return redirect(url_for('project_management.projects_list'))

def _handle_archive_document(document, file_extension):
    """处理压缩文件文档"""
    # 获取文件结构
    file_structure = get_archive_structure(document.filepath)
    
    if not file_structure:
        flash('无法解析压缩文件结构', 'danger')
        return redirect(url_for('project.projects_management'))

    # 清理数据以确保JSON序列化安全
    clean_file_structure = clean_json_data(file_structure)
    
    # JSON序列化
    try:
        json_string = json.dumps(clean_file_structure, 
                                ensure_ascii=False, 
                                separators=(',', ':'),
                                default=str)
        
        # 验证生成的JSON
        try:
            json.loads(json_string)
        except json.JSONDecodeError as verify_error:
            logger.error(f"JSON验证失败: {str(verify_error)}")
            flash('生成的文件结构格式错误', 'danger')
            return redirect(url_for('project.projects_management'))
        
    except Exception as e:
        logger.error(f"文件结构生成错误: {str(e)}")
        flash(f'文件结构生成错误: {str(e)}', 'danger')
        return redirect(url_for('project.projects_management'))
    
    # 渲染模板
    return render_template('document_viewer/archive_viewer.html', 
                          document=document, 
                          file_structure=json_string, 
                          is_archive=True)

def _handle_word_document(document):
    """处理Word文档"""
    try:
        doc = Document(document.filepath)
        content = []
        for para in doc.paragraphs:
            content.append(para.text)
        return render_template('document_viewer/docx_viewer.html', document=document, content=content)
    except Exception as e:
        logger.error(f"无法读取Word文档: {str(e)}")
        flash(f'无法读取Word文档: {str(e)}', 'danger')
        # 如果读取失败，提供下载选项
        return _handle_download_document(document)

def _handle_text_document(document, file_extension):
    """处理文本文件"""
    try:
        with open(document.filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template('document_viewer/text_viewer.html', 
                              document=document, 
                              content=content, 
                              file_extension=file_extension)
    except UnicodeDecodeError:
        # 尝试使用其他编码
        try:
            with open(document.filepath, 'r', encoding='gbk') as f:
                content = f.read()
            return render_template('document_viewer/text_viewer.html', 
                                  document=document, 
                                  content=content, 
                                  file_extension=file_extension)
        except Exception as e:
            logger.error(f"处理文本文件失败: {str(e)}")
            flash('无法以文本格式查看文件，请下载后查看', 'warning')
            return _handle_download_document(document)
    except Exception as e:
        logger.error(f"处理文本文件失败: {str(e)}")
        flash(f'无法查看文本文件: {str(e)}', 'danger')
        return _handle_download_document(document)

def _handle_download_document(document):
    """提供文档下载"""
    try:
        return send_file(document.filepath, as_attachment=True, download_name=document.title)
    except Exception as e:
        logger.error(f"发送文件失败: {str(e)}")
        flash(f'下载文件时出错: {str(e)}', 'danger')
        return redirect(url_for('project.projects_management'))

# 查看压缩包内文件
@document_viewer_bp.route('/view_archive_file/<int:document_id>')
@login_required
@engineer_required
def view_archive_file(document_id):
    """查看压缩包内的特定文件"""
    try:
        # 获取请求参数
        internal_file_path = request.args.get('file_path')
        
        if not internal_file_path:
            flash('文件路径参数缺失', 'danger')
            return redirect(url_for('document_viewer.view_document', document_id=document_id))
        
        # 查找文档
        document = Document.query.get(document_id)
        if not document:
            flash('文档不存在', 'danger')
            return redirect(url_for('project.projects_management'))
        
        # 检查文件是否存在
        if not os.path.exists(document.filepath):
            flash('文件不存在或已被删除', 'danger')
            return redirect(url_for('document_viewer.view_document', document_id=document_id))
        
        # 读取文件内容
        file_content = read_file_from_archive(document.filepath, internal_file_path)
        
        if file_content is None:
            flash('无法读取文件内容', 'danger')
            return redirect(url_for('document_viewer.view_document', document_id=document_id))
        
        # 尝试解析为文本
        try:
            content_text = file_content.decode('utf-8')
            # 获取文件扩展名
            file_extension = os.path.splitext(internal_file_path)[1].lower()
            
            return render_template('document_viewer/archive_file_viewer.html',
                                  document=document,
                                  file_path=internal_file_path,
                                  content=content_text,
                                  file_extension=file_extension)
        except UnicodeDecodeError:
            # 二进制文件，提供下载
            return redirect(url_for('document_viewer.download_archive_file_route',
                                  document_id=document_id,
                                  file_path=internal_file_path))
                                  
    except Exception as e:
        logger.error(f"查看压缩包内文件失败: {str(e)}")
        flash(f'操作失败: {str(e)}', 'danger')
        return redirect(url_for('document_viewer.view_document', document_id=document_id))

# 下载压缩包内文件路由
@document_viewer_bp.route('/download_archive_file_route/<int:document_id>')
@login_required
@engineer_required
def download_archive_file_route(document_id):
    """下载压缩包内的特定文件"""
    try:
        # 获取请求参数
        internal_file_path = request.args.get('file_path')
        
        if not internal_file_path:
            flash('文件路径参数缺失', 'danger')
            return redirect(url_for('document_viewer.view_document', document_id=document_id))
        
        # URL解码处理
        try:
            decoded_path = urllib.parse.unquote(internal_file_path)
            if '%' in decoded_path:
                decoded_path = urllib.parse.unquote(decoded_path)
        except Exception as decode_error:
            logger.error(f"URL解码失败: {str(decode_error)}")
            decoded_path = internal_file_path
        
        # 路径规范化
        normalized_path = _normalize_path(decoded_path)
        
        # 查找文档
        document = Document.query.get(document_id)
        if not document:
            flash('文档不存在', 'danger')
            return redirect(url_for('project.projects_management'))
        
        # 检查文件是否存在
        if not os.path.exists(document.filepath):
            flash('文件不存在或已被删除', 'danger')
            return redirect(url_for('document_viewer.view_document', document_id=document_id))
        
        # 读取文件内容
        file_content = _extract_from_archive(document.filepath, normalized_path)
        if file_content is None:
            flash(f'在压缩包中找不到文件: {normalized_path}', 'danger')
            return redirect(url_for('document_viewer.view_document', document_id=document_id))
        
        # 创建临时文件并提供下载
        return _create_and_send_temp_file(file_content, normalized_path)
        
    except Exception as e:
        logger.error(f"下载压缩包内文件时出错: {str(e)}")
        flash(f'下载文件时出错: {str(e)}', 'danger')
        return redirect(url_for('document_viewer.view_document', document_id=document_id))

def _normalize_path(path):
    """规范化文件路径"""
    normalized_path = path
    if '\\' in normalized_path:
        normalized_path = normalized_path.replace('\\', '/')
    if '\\\\' in normalized_path:
        normalized_path = normalized_path.replace('\\\\', '/')
    normalized_path = normalized_path.replace('\/', '/')
    return normalized_path

def _extract_from_archive(archive_path, file_path):
    """从压缩包中提取文件内容"""
    if archive_path.endswith('.zip'):
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # 查找文件
                normalized_path = file_path
                found = False
                for name in zip_ref.namelist():
                    if name == normalized_path or name.replace('\\', '/') == normalized_path:
                        found = True
                        normalized_path = name
                        break
                
                if not found:
                    # 尝试模糊匹配
                    for name in zip_ref.namelist():
                        if normalized_path in name or name in normalized_path:
                            normalized_path = name
                            found = True
                            break
                
                if found:
                    return zip_ref.read(normalized_path)
        except zipfile.BadZipFile:
            flash('无效的压缩文件', 'danger')
        except Exception as e:
            logger.error(f"读取压缩文件时出错: {str(e)}")
    else:
        flash('只支持ZIP文件格式', 'danger')
    return None

def _create_and_send_temp_file(file_content, file_path):
    """创建临时文件并发送给用户"""
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name
    
    # 获取文件名
    filename = os.path.basename(file_path)
    
    # 返回文件下载
    try:
        response = send_file(temp_file_path, as_attachment=True, download_name=filename)
        # 注册清理回调
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"无法删除临时文件: {str(e)}")
        return response
    except Exception as e:
        logger.error(f"发送文件失败: {str(e)}")
        flash(f'下载文件时出错: {str(e)}', 'danger')
        # 尝试清理临时文件
        try:
            os.unlink(temp_file_path)
        except Exception:
            pass
        return redirect(url_for('project.projects_management'))

# 文档列表路由
@document_viewer_bp.route('/documents')
@login_required
def documents():
    """重定向到项目管理页面"""
    return redirect(url_for('project.projects_management'))