from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file, jsonify
from flask_login import login_required, current_user
import os
import uuid
import json
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
import shutil
import re
import logging

from routes.models import Project, Engineer, Document, ProjectImage, Tag, db, project_tags, Role, Permission, OperationLog
from routes.decorators import admin_required, engineer_required, log_operation, has_permission

project_bp = Blueprint('project', __name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 项目数据修复函数
def fix_project_data():
    try:
        # 获取所有项目
        projects = Project.query.all()
        
        for project in projects:
            # 修复项目数据问题
            if not project.name:
                project.name = f"未命名项目_{project.id}"
            
            if not project.folder_path:
                project.folder_path = f"projects/{project.id}_{re.sub(r'[^\w\-]', '_', project.name)}"
        
        db.session.commit()
        logger.info("项目数据修复完成")
    except Exception as e:
        logger.error(f"项目数据修复失败: {str(e)}")
        db.session.rollback()

# 项目管理页面
@project_bp.route('/projects_management')
@login_required
@engineer_required
@log_operation('projects_management')
def projects_management():
    try:
        # 首先运行数据修复
        fix_project_data()
        
        # 获取查询参数
        search_query = request.args.get('search', '')
        tag_filter = request.args.get('tag', '')
        engineer_filter_param = request.args.get('engineer', '')
        status_filter = request.args.get('status', '')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # 构建查询并根据用户角色和RBAC权限过滤
        is_admin = current_user.role_level == 0 or has_permission('super_admin_access')
        if is_admin:
            # 管理员可以查看所有项目
            query = Project.query
            engineer_filter = engineer_filter_param
        else:
            # 工程师只能查看分配给自己的项目
            engineer = Engineer.query.filter_by(user_id=current_user.id).first()
            if engineer:
                query = Project.query.filter_by(assigned_engineer_id=engineer.id)
                # 工程师不能通过过滤参数查看其他工程师的项目
                engineer_filter = str(engineer.id)
            else:
                # 不是工程师也不是管理员，则没有项目可查看
                query = Project.query.filter_by(id=-1)  # 返回空结果
                engineer_filter = ''
        
        # 应用搜索过滤
        if search_query:
            query = query.filter(Project.name.ilike(f'%{search_query}%') | 
                                Project.description.ilike(f'%{search_query}%'))
        
        # 应用标签过滤
        if tag_filter:
            query = query.join(project_tags).join(Tag).filter(Tag.name == tag_filter)
        
        # 应用工程师过滤
        if engineer_filter:
            query = query.filter(Project.engineer_id == engineer_filter)
        
        # 应用状态过滤（使用progress字段）
        if status_filter:
            query = query.filter(Project.progress == status_filter)
        
        # 应用排序
        if sort_by in ['created_at', 'updated_at', 'name', 'id']:
            order_column = getattr(Project, sort_by)
            if sort_order == 'desc':
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        
        # 分页
        projects = query.all()
        
        # 获取所有标签用于过滤
        tags = Tag.query.all()
        
        # 获取所有工程师用于过滤
        engineers = Engineer.query.all()
        
        # 统计信息
        total_projects = Project.query.count()
        completed_projects = Project.query.filter_by(progress='已完成').count()
        pending_projects = Project.query.filter_by(progress='完成待确认').count()
        
        # 检查文档存在性
        for project in projects:
            for doc in project.documents:
                if not os.path.exists(doc.filepath):
                    logger.warning(f"文档文件不存在: {doc.filepath}")
        
        return render_template('project/projects_management.html', 
                              projects=projects,
                              tags=tags,
                              engineers=engineers,
                              search_query=search_query,
                              tag_filter=tag_filter,
                              engineer_filter=engineer_filter,
                              status_filter=status_filter,
                              sort_by=sort_by,
                              sort_order=sort_order,
                              total_projects=total_projects,
                              completed_projects=completed_projects,
                              pending_projects=pending_projects)
    
    except Exception as e:
        logger.error(f"项目管理页面加载失败: {str(e)}")
        flash(f'加载项目管理页面时出错: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))

# 添加项目
@project_bp.route('/add_project', methods=['GET', 'POST'])
@login_required
@admin_required
@log_operation('add_project')
def add_project():
    if request.method == 'POST':
        try:
            # 获取表单数据
            project_name = request.form.get('project_name', '').strip()
            description = request.form.get('description', '').strip()
            engineer_id = request.form.get('engineer_id')
            status = request.form.get('status', 'pending')
            selected_tags = request.form.getlist('tags')
            
            # 验证必要字段
            if not project_name:
                flash('项目名称不能为空', 'danger')
                return redirect(url_for('project.add_project'))
            
            # 清理项目名称
            safe_name = re.sub(r'[^\w\-]', '_', project_name)
            folder_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
            folder_path = os.path.join('projects', folder_name)
            
            # 创建项目文件夹
            os.makedirs(folder_path, exist_ok=True)
            
            # 创建项目记录
            project = Project(
                name=project_name,
                description=description,
                assigned_engineer_id=engineer_id,
                progress=status,  # 使用progress替代status
                materials_path=folder_path,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(project)
            db.session.flush()  # 获取项目ID但不提交
            
            # 处理上传的文档
            if 'documents' in request.files:
                for file in request.files.getlist('documents'):
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        doc_folder = os.path.join(folder_path, 'documents')
                        os.makedirs(doc_folder, exist_ok=True)
                        filepath = os.path.join(doc_folder, filename)
                        file.save(filepath)
                        
                        # 创建文档记录
                        document = Document(
                            project_id=project.id,
                            filename=filename,
                            filepath=filepath,
                            type='document'
                        )
                        db.session.add(document)
            
            # 处理工程压缩包
            if 'engineering_package' in request.files:
                file = request.files['engineering_package']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    package_folder = os.path.join(folder_path, 'packages')
                    os.makedirs(package_folder, exist_ok=True)
                    filepath = os.path.join(package_folder, filename)
                    file.save(filepath)
                    
                    # 创建文档记录
                    document = Document(
                        project_id=project.id,
                        filename=filename,
                        filepath=filepath,
                        type='engineering_zip'
                    )
                    db.session.add(document)
            
            # 关联标签
            for tag_id in selected_tags:
                tag = Tag.query.get(tag_id)
                if tag:
                    project.tags.append(tag)
            
            # 提交所有更改
            db.session.commit()
            logger.info(f"项目 '{project_name}' 已添加")
            flash(f'项目 "{project_name}" 已成功添加', 'success')
            return redirect(url_for('project.projects_management'))
            
        except Exception as e:
            logger.error(f"添加项目失败: {str(e)}")
            db.session.rollback()
            flash(f'添加项目时出错: {str(e)}', 'danger')
            return redirect(url_for('project.add_project'))
    
    # GET 请求
    engineers = Engineer.query.all()
    tags = Tag.query.all()
    return render_template('project/add_project.html', engineers=engineers, tags=tags)

# 更新项目
@project_bp.route('/update_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
@engineer_required
@log_operation('update_project')
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        try:
            # 记录原始值
            original_name = project.name
            original_folder = project.folder_path
            
            # 更新基本信息
            new_name = request.form.get('project_name', '').strip()
            project.description = request.form.get('description', '').strip()
            project.assigned_engineer_id = request.form.get('engineer_id')
            project.progress = request.form.get('status', 'not_started')  # 使用progress替代status
            project.updated_by = current_user.id
            
            # 更新标签关联
            selected_tags = request.form.getlist('tags')
            project.tags.clear()
            for tag_id in selected_tags:
                tag = Tag.query.get(tag_id)
                if tag:
                    project.tags.append(tag)
            
            # 处理文档上传
            if 'documents' in request.files:
                for file in request.files.getlist('documents'):
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        doc_folder = os.path.join(project.folder_path, 'documents')
                        os.makedirs(doc_folder, exist_ok=True)
                        
                        # 版本控制
                        base_name, ext = os.path.splitext(filename)
                        filepath = os.path.join(doc_folder, filename)
                        counter = 1
                        
                        # 只保留最新版本和一个历史版本
                        while os.path.exists(filepath):
                            if counter == 1:
                                # 移动第一个冲突的文件到历史版本
                                history_file = os.path.join(doc_folder, f"{base_name}_v{counter}{ext}")
                                if not os.path.exists(history_file):  # 只在历史版本不存在时创建
                                    shutil.copy2(filepath, history_file)
                            counter += 1
                            filepath = os.path.join(doc_folder, f"{base_name}_v{counter}{ext}")
                        
                        file.save(filepath)
                        
                        # 创建文档记录
                        document = Document(
                            project_id=project.id,
                            filename=filename,
                            filepath=filepath,
                            type='document'
                        )
                        db.session.add(document)
            
            # 如果项目名称改变，更新文件夹名称
            if new_name and new_name != original_name:
                safe_name = re.sub(r'[^\w\-]', '_', new_name)
                new_folder_name = f"{os.path.basename(original_folder).split('_', 1)[0]}_{safe_name}"
                new_folder_path = os.path.join('projects', new_folder_name)
                
                if os.path.exists(original_folder):
                    os.rename(original_folder, new_folder_path)
                
                project.name = new_name
                project.folder_path = new_folder_path
                
                # 更新所有文档的路径
                for doc in project.documents:
                    doc.filepath = doc.filepath.replace(original_folder, new_folder_path)
            
            # 处理工程压缩包
            if 'engineering_package' in request.files:
                file = request.files['engineering_package']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    package_folder = os.path.join(project.folder_path, 'packages')
                    os.makedirs(package_folder, exist_ok=True)
                    
                    # 清理旧的压缩包（只保留最新的）
                    for old_file in os.listdir(package_folder):
                        if old_file.endswith(('.zip', '.rar', '.tar.gz', '.tgz')):
                            os.remove(os.path.join(package_folder, old_file))
                    
                    filepath = os.path.join(package_folder, filename)
                    file.save(filepath)
                    
                    # 清理旧的压缩包记录
                    for doc in project.documents:
                        if doc.is_package:
                            db.session.delete(doc)
                    
                    # 创建新的压缩包记录
                    document = Document(
                        project_id=project.id,
                        title=filename,
                        filename=filename,
                        filepath=filepath,
                        filetype=os.path.splitext(filename)[1].lower(),
                        uploaded_by=current_user.username,
                        is_package=True
                    )
                    db.session.add(document)
            
            db.session.commit()
            logger.info(f"项目 '{project.name}' 已更新")
            flash(f'项目 "{project.name}" 已成功更新', 'success')
            return redirect(url_for('project.projects_management'))
            
        except Exception as e:
            logger.error(f"更新项目失败: {str(e)}")
            db.session.rollback()
            flash(f'更新项目时出错: {str(e)}', 'danger')
            return redirect(url_for('project.update_project', project_id=project_id))
    
    # GET 请求
    engineers = Engineer.query.all()
    tags = Tag.query.all()
    selected_tag_ids = [tag.id for tag in project.tags]
    
    return render_template('project/update_project.html', 
                          project=project,
                          engineers=engineers,
                          tags=tags,
                          selected_tag_ids=selected_tag_ids)

# 删除项目
@project_bp.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
@log_operation('delete_project')
def delete_project(project_id):
    # 权限验证：只有管理员可以删除项目
    if not (current_user.role_level == 0 or has_permission('super_admin_access')):
        flash('没有权限删除项目', 'danger')
        return redirect(url_for('project.projects_management'))
        
    try:
        project = Project.query.get_or_404(project_id)
        project_name = project.name
        folder_path = project.folder_path
        
        # 删除相关的图片文件
        for image in project.images:
            if os.path.exists(image.filepath):
                os.remove(image.filepath)
        
        # 删除相关的文档文件
        for doc in project.documents:
            if os.path.exists(doc.filepath):
                try:
                    os.remove(doc.filepath)
                except Exception as e:
                    logger.warning(f"无法删除文档文件: {doc.filepath}, 错误: {str(e)}")
        
        # 删除项目文件夹
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
            except Exception as e:
                logger.warning(f"无法删除项目文件夹: {folder_path}, 错误: {str(e)}")
        
        # 从数据库中删除项目（级联删除会删除相关文档和图片）
        db.session.delete(project)
        db.session.commit()
        
        logger.info(f"项目 '{project_name}' 已删除")
        flash(f'项目 "{project_name}" 已成功删除', 'success')
        return redirect(url_for('project.projects_management'))
        
    except Exception as e:
        logger.error(f"删除项目失败: {str(e)}")
        db.session.rollback()
        flash(f'删除项目时出错: {str(e)}', 'danger')
        return redirect(url_for('project.projects_management'))

# 获取项目详情
@project_bp.route('/get_project_details/<int:project_id>')
@login_required
@log_operation('get_project_details')
def get_project_details(project_id):
    try:
        project = Project.query.get_or_404(project_id)
        
        # 权限验证：管理员可以查看所有项目，工程师只能查看分配给自己的项目
        is_admin = current_user.role_level == 0 or has_permission('super_admin_access')
        if not is_admin:
            engineer = Engineer.query.filter_by(user_id=current_user.id).first()
            if not engineer or project.assigned_engineer_id != engineer.id:
                flash('没有权限查看此项目', 'danger')
                return redirect(url_for('user.user_dashboard'))
        
        # 构建项目详情数据
        project_data = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'engineer': project.engineer.name if project.engineer else '未分配',
            'progress': project.progress,  # 使用progress替代status
            'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M:%S') if project.updated_at else None,
            'created_by': project.created_by,
            'updated_by': project.updated_by,
            'documents': [{
                'id': doc.id,
                'title': doc.title,
                'filename': doc.filename,
                'filetype': doc.filetype,
                'uploaded_by': doc.uploaded_by,
                'uploaded_at': doc.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_package': doc.is_package
            } for doc in project.documents],
            'tags': [tag.name for tag in project.tags]
        }
        
        return jsonify(project_data)
    
    except Exception as e:
        logger.error(f"获取项目详情失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 标记项目为已完成
@project_bp.route('/mark_project_completed', methods=['POST'])
@login_required
@log_operation('mark_project_completed')
def mark_project_completed():
    try:
        project_id = request.form.get('project_id', type=int)
        if not project_id:
            flash('项目ID不能为空', 'danger')
            return redirect(url_for('user.user_dashboard'))
        
        project = Project.query.get_or_404(project_id)
        
        # 权限验证：只有管理员或项目负责人可以标记项目完成
        is_admin = current_user.role_level == 0 or has_permission('super_admin_access')
        if not is_admin:
            engineer = Engineer.query.filter_by(user_id=current_user.id).first()
            if not engineer or project.assigned_engineer_id != engineer.id:
                flash('没有权限执行此操作', 'danger')
                return redirect(url_for('user.user_dashboard'))
        
        project.progress = '已完成'  # 使用progress替代status
        project.completed_time = datetime.now()
        project.updated_by = current_user.id
        db.session.commit()
        
        flash('项目已成功标记为完成', 'success')
    except Exception as e:
        logger.error(f"标记项目完成失败: {str(e)}")
        db.session.rollback()
        flash('标记项目完成失败，请稍后重试', 'danger')
    
    return redirect(url_for('user.user_dashboard'))

# 取消项目完成状态
@project_bp.route('/unmark_project_completed', methods=['POST'])
@login_required
@log_operation('unmark_project_completed')
def unmark_project_completed():
    try:
        project_id = request.form.get('project_id', type=int)
        if not project_id:
            flash('项目ID不能为空', 'danger')
            return redirect(url_for('user.user_dashboard'))
        
        project = Project.query.get_or_404(project_id)
        
        # 权限验证：只有管理员或项目负责人可以取消项目完成状态
        if current_user.role != 'admin':
            engineer = Engineer.query.filter_by(user_id=current_user.id).first()
            if not engineer or project.assigned_engineer_id != engineer.id:
                flash('没有权限执行此操作', 'danger')
                return redirect(url_for('user.user_dashboard'))
        
        project.status = 'active'
        project.completed_time = None
        db.session.commit()
        
        flash('项目已成功取消完成状态', 'success')
    except Exception as e:
        logger.error(f"取消项目完成状态失败: {str(e)}")
        db.session.rollback()
        flash('取消项目完成状态失败，请稍后重试', 'danger')
    
    return redirect(url_for('user.user_dashboard'))

# 批量删除项目
@project_bp.route('/batch_delete_projects', methods=['POST'])
@login_required
@admin_required
def batch_delete_projects():
    try:
        data = request.get_json()
        project_ids = data.get('project_ids', [])
        
        if not project_ids:
            return jsonify({'error': '没有选择要删除的项目'}), 400
        
        deleted_count = 0
        
        for project_id in project_ids:
            try:
                project = Project.query.get(project_id)
                if project:
                    # 删除项目文件夹
                    if project.folder_path and os.path.exists(project.folder_path):
                        try:
                            shutil.rmtree(project.folder_path)
                        except Exception as e:
                            logger.warning(f"无法删除项目文件夹: {project.folder_path}, 错误: {str(e)}")
                    
                    # 删除项目记录
                    db.session.delete(project)
                    deleted_count += 1
            except Exception as e:
                logger.error(f"删除项目 {project_id} 失败: {str(e)}")
        
        db.session.commit()
        logger.info(f"批量删除了 {deleted_count} 个项目")
        return jsonify({'success': True, 'deleted_count': deleted_count})
        
    except Exception as e:
        logger.error(f"批量删除项目失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 下载文档
@project_bp.route('/download_document/<int:document_id>')
@login_required
def download_document(document_id):
    try:
        document = Document.query.get_or_404(document_id)
        
        # 权限验证：管理员可以下载所有文档，工程师只能下载分配给自己项目的文档
        if current_user.role != 'admin':
            project = Project.query.get(document.project_id)
            engineer = Engineer.query.filter_by(user_id=current_user.id).first()
            if not engineer or project.assigned_engineer_id != engineer.id:
                flash('没有权限下载此文档', 'danger')
                return redirect(url_for('project.projects_management'))
        
        if not os.path.exists(document.filepath):
            flash('文件不存在或已被删除', 'danger')
            return redirect(url_for('project.projects_management'))
        
        # 处理中文文件名
        try:
            # 使用Unicode文件名确保中文正常显示
            return send_file(document.filepath, as_attachment=True, download_name=document.filename)
        except Exception as e:
            logger.warning(f"发送文件时出错: {str(e)}, 尝试使用备用方法")
            # 如果直接使用中文文件名失败，尝试使用URL编码
            return send_file(document.filepath, as_attachment=True, download_name=document.filename.encode('utf-8'))
    except Exception as e:
        logger.error(f"下载文档失败: {str(e)}")
        flash(f'下载文档时出错: {str(e)}', 'danger')
        return redirect(url_for('project.projects_management'))

# 导出项目数据
@project_bp.route('/export_projects', methods=['GET'])
@login_required
def export_projects():
    try:
        # 获取查询参数
        search_query = request.args.get('search', '')
        tag_filter = request.args.get('tag', '')
        engineer_filter = request.args.get('engineer', '')
        status_filter = request.args.get('status', '')
        
        # 构建查询
        query = Project.query
        
        # 应用过滤条件
        if search_query:
            query = query.filter(Project.name.ilike(f'%{search_query}%') | 
                                Project.description.ilike(f'%{search_query}%'))
        
        if tag_filter:
            query = query.join(project_tags).join(Tag).filter(Tag.name == tag_filter)
        
        if engineer_filter:
            query = query.filter(Project.engineer_id == engineer_filter)
        
        if status_filter:
            query = query.filter(Project.status == status_filter)
        
        # 执行查询
        projects = query.all()
        
        # 准备导出数据
        export_data = []
        for project in projects:
            # 获取标签信息
            tags = ', '.join([tag.name for tag in project.tags])
            
            # 获取工程师信息
            engineer_name = project.engineer.name if project.engineer else '未分配'
            
            # 获取文档信息
            doc_count = len(project.documents)
            package_count = len([doc for doc in project.documents if doc.is_package])
            
            # 获取最近更新时间
            latest_doc = max(project.documents, key=lambda d: d.uploaded_at, default=None)
            latest_update = latest_doc.uploaded_at if latest_doc else project.updated_at
            
            export_data.append({
                '项目ID': project.id,
                '项目名称': project.name,
                '描述': project.description,
                '工程师': engineer_name,
                '状态': project.status,
                '标签': tags,
                '文档数量': doc_count,
                '压缩包数量': package_count,
                '创建时间': project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '最近更新': latest_update.strftime('%Y-%m-%d %H:%M:%S'),
                '创建人': project.created_by
            })
        
        # 创建DataFrame
        df = pd.DataFrame(export_data)
        
        # 导出到Excel
        output = pd.ExcelWriter('projects_export.xlsx', engine='openpyxl')
        df.to_excel(output, index=False, sheet_name='项目列表')
        
        # 调整列宽
        worksheet = output.sheets['项目列表']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.close()
        
        # 提供文件下载
        return send_file('projects_export.xlsx', as_attachment=True, download_name=f'项目列表导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
        
    except Exception as e:
        logger.error(f"导出项目数据失败: {str(e)}")
        flash(f'导出项目数据时出错: {str(e)}', 'danger')
        return redirect(url_for('project.projects_management'))