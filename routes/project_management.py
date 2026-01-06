from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import zipfile
import shutil
from datetime import datetime
from .models import Project, Tag, TagRequest, Engineer, Document, db, Role, Permission, OperationLog
from .decorators import role_required, log_operation, admin_required

project_management_bp = Blueprint('project_management', __name__)

# 确保项目资料文件夹存在
PROJECTS_DIR = os.path.join('static', 'uploads', 'projects')
if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR)

@project_management_bp.route('/projects_list')
@login_required
@log_operation('查看项目列表')
def projects_list():
    # 获取筛选参数
    search_query = request.args.get('search', '').strip()
    engineer_id = request.args.get('engineer_id', '').strip()
    tag_search = request.args.get('tag', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10
    # 强制使用卡片视图，不再支持列表视图
    view_type = 'card'
    
    # 获取当前用户信息
    engineer = Engineer.query.filter_by(user_id=current_user.id).first() if current_user.role != 'admin' else None
    
    # 基础查询：根据用户角色设置可见项目
    if current_user.role_level == 0:
        # 超级管理员可以查看所有项目
        query = Project.query
    elif engineer:
        # 工程师只能查看自己的项目
        query = Project.query.filter_by(assigned_engineer_id=engineer.id)
    else:
        # 其他角色不应该访问此页面，但为了安全返回空结果
        query = Project.query.filter_by(id=-1)
    
    # 应用搜索条件 - 只在有实际搜索内容时应用
    if search_query:
        query = query.filter(Project.name.like(f'%{search_query}%') | Project.description.like(f'%{search_query}%'))
    
    # 按工程师筛选 - 只在有值且超级管理员角色时应用
    if engineer_id and current_user.role_level == 0:
        query = query.filter_by(assigned_engineer_id=engineer_id)
    
    # 按标签筛选 - 只在有标签搜索内容时应用
    if tag_search:
        # 查找匹配的标签
        tags = Tag.query.filter(Tag.name.like(f'%{tag_search}%')).all()
        if tags:
            # 收集所有标签关联的项目ID
            project_ids = []
            for tag in tags:
                for project in tag.projects:
                    # 确保只有用户有权限的项目才被加入
                    if current_user.role_level == 0 or (engineer and project.assigned_engineer_id == engineer.id):
                        project_ids.append(project.id)
            
            if project_ids:
                query = query.filter(Project.id.in_(project_ids))
            else:
                # 没有匹配的项目
                query = query.filter_by(id=-1)
    
    # 分页
    total = query.count()
    total_pages = (total + per_page - 1) // per_page
    projects = query.order_by(Project.created_time.desc()).paginate(page=page, per_page=per_page, error_out=False).items
    
    # 获取工程师列表（仅超级管理员可见）
    engineers = []
    if current_user.role_level == 0:
        engineers = Engineer.query.all()
    
    # 获取所有标签
    all_tags = Tag.query.all()
    
    # 始终使用卡片视图模板
    template_name = 'projects_list_card.html'
    
    return render_template(template_name, 
                         projects=projects,
                         engineers=engineers,
                         tags=all_tags,
                         search_query=search_query,
                         assigned_engineer_id=engineer_id,
                         tag_search=tag_search,
                         current_page=page,
                         total_pages=total_pages,
                         total=total,
                         per_page=per_page)

@project_management_bp.route('/add_project', methods=['GET', 'POST'])
@login_required
@log_operation('添加项目')
def add_project():
    # 超级管理员和工程师可以添加项目
    engineer = Engineer.query.filter_by(user_id=current_user.id).first()
    # 允许超级管理员(role_level=0或role='super_admin')或工程师添加项目
    if not (current_user.role_level == 0 or current_user.role == 'super_admin' or engineer):
        flash('没有权限添加项目', 'danger')
        # 上传完成后返回到项目列表页面，并带上项目ID以便可以重新打开该项目的详情模态框
    return redirect(url_for('project_management.projects_list', project_id=project_id))
    
    tags = Tag.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        project_type = request.form.get('project_type', 'custom')
        price = request.form.get('price')
        cost = request.form.get('cost')
        unit_price = request.form.get('unit_price')
        group_name = request.form.get('group_name', '').strip()
        status = request.form.get('status', 'not_started')
        tag_ids = request.form.getlist('tags')
        
        # 验证必要字段
        if not name:
            flash('项目名称不能为空', 'danger')
            return render_template('add_project.html', tags=tags, name=name, description=description, selected_tags=tag_ids)
        
        # 定制项目需要群名
        if project_type == 'custom' and not group_name:
            flash('定制项目必须填写群名', 'danger')
            return render_template('add_project.html', tags=tags, name=name, description=description, selected_tags=tag_ids, project_type=project_type)
        
        # 确定工程师ID
        if current_user.role_level == 0 and request.form.get('engineer_id'):
            project_engineer_id = int(request.form.get('engineer_id'))
        elif engineer:
            project_engineer_id = engineer.id
        else:
            flash('找不到有效的工程师信息', 'danger')
            return render_template('add_project.html', tags=tags, name=name, description=description, selected_tags=tag_ids, project_type=project_type, group_name=group_name)
        
        # 创建项目
        project = Project(
            name=name,
            description=description,
            project_type=project_type,
            assigned_engineer_id=project_engineer_id,
            progress=status,  # 使用progress字段替代status
            group_name=group_name,
            price=float(price) if price else None,
            cost=float(cost) if cost else None,
            unit_price=float(unit_price) if unit_price else None,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        
        # 添加标签
        for tag_id in tag_ids:
            tag = Tag.query.get(int(tag_id))
            if tag:
                project.tags.append(tag)
        
        try:
            db.session.add(project)
            db.session.flush()  # 获取项目ID但不提交
            
            # 创建项目文件夹
            project_folder = os.path.join(PROJECTS_DIR, f'project_{project.id}_{name.replace(" ", "_")}')
            project.materials_path = project_folder
            
            # 创建实际的文件夹
            if not os.path.exists(project_folder):
                os.makedirs(project_folder)
                # 创建文档和图片子文件夹
                os.makedirs(os.path.join(project_folder, 'documents'), exist_ok=True)
                os.makedirs(os.path.join(project_folder, 'images'), exist_ok=True)
            
            db.session.commit()
            flash('项目创建成功', 'success')
            # 上传完成后返回到项目列表页面，并带上项目ID以便可以重新打开该项目的详情模态框
            return redirect(url_for('project_management.projects_list', project_id=project_id))
        except Exception as e:
            db.session.rollback()
            flash(f'创建项目失败: {str(e)}', 'danger')
    
    # 超级管理员可以选择工程师
    engineers = []
    if current_user.role_level == 0:
        engineers = Engineer.query.all()
    
    return render_template('add_project.html', tags=tags, engineers=engineers)

@project_management_bp.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
@log_operation('编辑项目')
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # 检查权限
    engineer = Engineer.query.filter_by(user_id=current_user.id).first()
    # 允许超级管理员(role_level=0或role='super_admin')或项目分配的工程师编辑项目
    if not (current_user.role_level == 0 or current_user.role == 'super_admin' or 
           (engineer and project.assigned_engineer_id == engineer.id)):
        flash('没有权限编辑此项目', 'danger')
        # 上传完成后返回到项目列表页面，并带上项目ID以便可以重新打开该项目的详情模态框
    return redirect(url_for('project_management.projects_list', project_id=project_id))
    
    tags = Tag.query.all()
    selected_tags = [str(tag.id) for tag in project.tags]
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        project_type = request.form.get('project_type', 'custom')
        price = request.form.get('price')
        cost = request.form.get('cost')
        unit_price = request.form.get('unit_price')
        group_name = request.form.get('group_name', '').strip()
        status = request.form.get('status', 'not_started')
        tag_ids = request.form.getlist('tags')
        
        # 验证必要字段
        if not name:
            flash('项目名称不能为空', 'danger')
            return render_template('edit_project.html', project=project, tags=tags, selected_tags=selected_tags)
        
        # 定制项目需要群名
        if project_type == 'custom' and not group_name:
            flash('定制项目必须填写群名', 'danger')
            return render_template('edit_project.html', project=project, tags=tags, selected_tags=selected_tags)
        
        # 更新项目信息
        project.name = name
        project.description = description
        project.project_type = project_type
        project.progress = status  # 使用progress字段替代status
        project.group_name = group_name
        project.price = float(price) if price else None
        project.cost = float(cost) if cost else None
        project.unit_price = float(unit_price) if unit_price else None
        project.updated_at = datetime.utcnow()
        project.updated_by = current_user.id
        
        # 更新标签
        project.tags.clear()
        for tag_id in tag_ids:
            tag = Tag.query.get(int(tag_id))
            if tag:
                project.tags.append(tag)
        
        try:
            db.session.commit()
            flash('项目更新成功', 'success')
            # 上传完成后返回到项目列表页面，并带上项目ID以便可以重新打开该项目的详情模态框
            return redirect(url_for('project_management.projects_list', project_id=project_id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新项目失败: {str(e)}', 'danger')
    
    return render_template('edit_project.html', project=project, tags=tags, selected_tags=selected_tags)

@project_management_bp.route('/upload_materials/<int:project_id>', methods=['GET', 'POST'])
@login_required
@log_operation('上传项目资料')
def upload_materials(project_id):
    # 查找项目
    project = Project.query.get_or_404(project_id)
    
    # 检查权限
    engineer = Engineer.query.filter_by(user_id=current_user.id).first()
    # 允许超级管理员(role_level=0或role='super_admin')或项目分配的工程师上传资料
    if not (current_user.role_level == 0 or current_user.role == 'super_admin' or engineer):
        flash('没有权限上传项目资料', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 非管理员和非超级管理员只能上传自己的项目资料
    if engineer and not (current_user.role_level == 0 or current_user.role == 'super_admin') and project.assigned_engineer_id != engineer.id:
        flash('没有权限上传其他工程师的项目资料', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 处理GET请求，显示上传页面
    if request.method == 'GET':
        # 获取上传类型参数，默认为项目资料
        upload_type = request.args.get('type', 'material')
        page_title = '上传论文资料' if upload_type == 'paper' else '上传项目资料'
        return render_template('upload_materials.html', project=project, page_title=page_title, upload_type=upload_type)
    
    # 检查文件是否存在
    if 'file' not in request.files:
        flash('请选择要上传的文件', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    files = request.files.getlist('file')  # 获取所有上传的文件
    file_type = request.form.get('file_type', 'document')  # document 或 image
    document_type = request.form.get('document_type', 'material')  # paper 或 material
    
    # 检查是否选择了文件
    if not any(file.filename for file in files):
        flash('请选择要上传的文件', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 确保项目文件夹存在
    project_folder = project.materials_path
    if not project_folder:
        project_folder = os.path.join(PROJECTS_DIR, f'project_{project.id}_{project.name.replace(" ", "_")}')
        project.materials_path = project_folder
        project.updated_by = current_user.id
        db.session.commit()
    
    # 创建子文件夹
    if file_type == 'image':
        upload_dir = os.path.join(project_folder, 'images')
    elif file_type == 'package':
        upload_dir = os.path.join(project_folder, 'packages')
    else:
        upload_dir = os.path.join(project_folder, 'documents')
    
    os.makedirs(upload_dir, exist_ok=True)
    
    # 上传成功的文件数
    success_count = 0
    error_count = 0
    error_messages = []
    
    # 处理每个文件
    for file in files:
        if file.filename:
            try:
                # 保存文件
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_dir, filename)
                
                # 避免文件名冲突
                if os.path.exists(file_path):
                    base_name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(os.path.join(upload_dir, f"{base_name}_{counter}{ext}")):
                        counter += 1
                    filename = f"{base_name}_{counter}{ext}"
                    file_path = os.path.join(upload_dir, filename)
                
                file.save(file_path)
                success_count += 1
                
                # 创建数据库记录
                material = Material(
                    project_id=project_id,
                    filename=filename,
                    file_path=os.path.relpath(file_path, PROJECTS_DIR),
                    file_type=file_type,
                    document_type=document_type,
                    uploaded_by=current_user.id,
                    uploaded_at=datetime.now()
                )
                db.session.add(material)
                
            except Exception as e:
                error_count += 1
                error_messages.append(f'{file.filename}: {str(e)}')
    
    # 提交数据库更改
    if success_count > 0:
        db.session.commit()
        flash(f'成功上传 {success_count} 个文件', 'success')
    
    if error_count > 0:
        for msg in error_messages:
            flash(f'文件上传失败: {msg}', 'danger')
    
    # 上传完成后返回到项目列表页面，并带上项目ID以便可以重新打开该项目的详情模态框
    return redirect(url_for('project_management.projects_list', project_id=project_id))

@project_management_bp.route('/download_materials/<int:project_id>/<file_type>/<filename>')
@login_required
@log_operation('下载项目资料')
def download_materials(project_id, file_type, filename):
    # 查找项目
    project = Project.query.get_or_404(project_id)
    
    # 检查权限
    engineer = Engineer.query.filter_by(user_id=current_user.id).first()
    if not engineer and current_user.role != 'admin':
        flash('没有权限下载项目资料', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 非管理员只能下载自己的项目资料
    if engineer and project.assigned_engineer_id != engineer.id:
        flash('没有权限下载其他工程师的项目资料', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 构建文件路径
    if file_type == 'image':
        file_path = os.path.join(project.materials_path, 'images', filename)
        upload_dir = os.path.join(project.materials_path, 'images')
    elif file_type == 'package':
        file_path = os.path.join(project.materials_path, 'packages', filename)
        upload_dir = os.path.join(project.materials_path, 'packages')
    else:
        file_path = os.path.join(project.materials_path, 'documents', filename)
        upload_dir = os.path.join(project.materials_path, 'documents')
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        flash('文件不存在', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 发送文件
    try:
        return send_from_directory(upload_dir, filename, as_attachment=True)
    except Exception as e:
        flash(f'下载文件失败: {str(e)}', 'danger')
        return redirect(url_for('project_management.projects_list'))

@project_management_bp.route('/preview_materials/<int:project_id>/<file_type>/<filename>')
@login_required
@log_operation('预览项目资料')
def preview_materials(project_id, file_type, filename):
    # 查找项目
    project = Project.query.get_or_404(project_id)
    
    # 检查权限
    engineer = Engineer.query.filter_by(user_id=current_user.id).first()
    if not engineer and current_user.role != 'admin':
        flash('没有权限预览项目资料', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 非管理员只能预览自己的项目资料
    if engineer and project.assigned_engineer_id != engineer.id:
        flash('没有权限预览其他工程师的项目资料', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 构建文件路径
    if file_type == 'image':
        file_path = os.path.join(project.materials_path, 'images', filename)
        upload_dir = os.path.join(project.materials_path, 'images')
    elif file_type == 'package':
        file_path = os.path.join(project.materials_path, 'packages', filename)
        upload_dir = os.path.join(project.materials_path, 'packages')
    else:
        file_path = os.path.join(project.materials_path, 'documents', filename)
        upload_dir = os.path.join(project.materials_path, 'documents')
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        flash('文件不存在', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 检查是否为可预览的文件类型
    ext = os.path.splitext(filename)[1].lower()
    image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    text_exts = ['.txt', '.log', '.md', '.csv']
    
    if ext in image_exts or ext in text_exts:
        # 对于图片和文本文件，可以直接预览
        try:
            return send_from_directory(upload_dir, filename, as_attachment=False)
        except Exception as e:
            flash(f'预览文件失败: {str(e)}', 'danger')
            return redirect(url_for('project_management.projects_list'))
    else:
        # 对于其他文件类型，提供下载
        flash('该文件类型不支持预览，请下载查看', 'info')
        return redirect(url_for('project_management.download_materials', 
                               project_id=project_id, file_type=file_type, filename=filename))

@project_management_bp.route('/request_tag', methods=['GET', 'POST'])
@login_required
@log_operation('申请标签')
def request_tag():
    # 仅工程师可以申请标签
    engineer = Engineer.query.filter_by(user_id=current_user.id).first()
    if not engineer:
        flash('只有工程师可以申请标签', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    if request.method == 'POST':
        tag_name = request.form.get('tag_name', '').strip()
        reason = request.form.get('reason', '').strip()
        
        if not tag_name:
            flash('标签名称不能为空', 'danger')
            return render_template('request_tag.html', tag_name=tag_name, reason=reason)
        
        # 检查标签是否已存在
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if existing_tag:
            flash('该标签已存在', 'info')
            return redirect(url_for('project_management.projects_list'))
        
        # 检查是否有未处理的相同申请
        pending_request = TagRequest.query.filter_by(tag_name=tag_name, status='pending').first()
        if pending_request:
            flash('该标签已有申请正在处理中', 'info')
            return redirect(url_for('project_management.projects_list'))
        
        # 创建申请
        tag_request = TagRequest(
            tag_name=tag_name,
            engineer_id=engineer.id,
            reason=reason
        )
        
        try:
            db.session.add(tag_request)
            db.session.commit()
            flash('标签申请已提交，请等待管理员审核', 'success')
            return redirect(url_for('project_management.projects_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'申请失败: {str(e)}', 'danger')
    
    return render_template('request_tag.html')

@project_management_bp.route('/manage_tag_requests')
@login_required
@role_required('admin')
@log_operation('管理标签申请')
def manage_tag_requests():
    # 管理员查看标签申请
    requests = TagRequest.query.filter_by(status='pending').order_by(TagRequest.created_at.desc()).all()
    # 获取所有已存在的标签，用于显示
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('manage_tag_requests.html', requests=requests, tags=tags)

@project_management_bp.route('/add_tag', methods=['GET', 'POST'])
@login_required
# @role_required('admin')  # 暂时注释掉权限限制进行测试
@log_operation('直接添加标签')
def add_tag():
    """管理员直接添加标签的功能"""
    if request.method == 'POST':
        tag_name = request.form.get('tag_name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not tag_name:
            flash('标签名称不能为空', 'danger')
            return render_template('add_tag.html')
        
        # 检查标签是否已存在
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if existing_tag:
            flash('该标签已存在', 'info')
            return redirect(url_for('project_management.manage_tag_requests'))
        
        # 创建新标签
        new_tag = Tag(
            name=tag_name,
            created_by=f'管理员直接添加({current_user.username})',
            created_by_user_id=current_user.id
        )
        
        try:
            db.session.add(new_tag)
            db.session.commit()
            flash(f'标签 "{tag_name}" 已成功添加', 'success')
            return redirect(url_for('project_management.manage_tag_requests'))
        except Exception as e:
            db.session.rollback()
            flash(f'添加标签失败: {str(e)}', 'danger')
    
    return render_template('add_tag.html')

@project_management_bp.route('/approve_tag/<int:request_id>')
@login_required
@role_required('admin')
@log_operation('批准标签申请')
def approve_tag(request_id):
    tag_request = TagRequest.query.get_or_404(request_id)
    
    # 检查标签是否已存在
    existing_tag = Tag.query.filter_by(name=tag_request.tag_name).first()
    if not existing_tag:
        # 创建新标签
        new_tag = Tag(
                name=tag_request.tag_name,
                created_by=f'管理员批准({tag_request.engineer.name})',
                created_by_user_id=current_user.id if current_user else None
            )
        db.session.add(new_tag)
    
    # 更新申请状态
    tag_request.status = 'approved'
    
    try:
        db.session.commit()
        flash('标签已批准并添加到标签库', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'批准失败: {str(e)}', 'danger')
    
    return redirect(url_for('project_management.manage_tag_requests'))

@project_management_bp.route('/delete_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
@log_operation('删除项目')
def delete_project(project_id):
    # 导入权限检查函数
    from routes.decorators import has_permission
    
    # 权限验证：管理员、工程师或具有删除项目权限的用户可以删除项目
    engineer = Engineer.query.filter_by(user_id=current_user.id).first()
    
    try:
        project = Project.query.get_or_404(project_id)
        project_name = project.name
        
        # 检查权限：管理员、具有删除项目权限的用户、或工程师只能删除自己的项目
        if (current_user.role != 'admin' and 
            not has_permission('delete_projects') and 
            (not engineer or project.assigned_engineer_id != engineer.id)):
            flash('没有权限删除该项目', 'danger')
            return redirect(url_for('project_management.projects_list'))
        
        # 获取项目文件夹路径
        folder_path = project.materials_path
        
        # 删除项目文件夹
        if folder_path and os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
            except Exception as e:
                print(f"无法删除项目文件夹: {folder_path}, 错误: {str(e)}")
        
        # 从数据库中删除项目
        db.session.delete(project)
        db.session.commit()
        
        flash(f'项目 "{project_name}" 已成功删除', 'success')
        return redirect(url_for('project_management.projects_list'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除项目时出错: {str(e)}', 'danger')
        return redirect(url_for('project_management.projects_list'))

@project_management_bp.route('/batch_delete_projects', methods=['POST'])
@login_required
@log_operation('批量删除项目')
def batch_delete_projects():
    try:
        data = request.get_json()
        project_ids = data.get('project_ids', [])
        
        if not project_ids:
            return jsonify({'error': '没有选择要删除的项目'}), 400
        
        # 导入权限检查函数
        from routes.decorators import has_permission
        
        # 权限检查
        engineer = Engineer.query.filter_by(user_id=current_user.id).first()
        deleted_count = 0
        
        for project_id in project_ids:
            try:
                project = Project.query.get(project_id)
                if project:
                    # 检查权限
                    if (current_user.role != 'admin' and 
                        not has_permission('delete_projects') and 
                        (not engineer or project.assigned_engineer_id != engineer.id)):
                        continue
                    
                    # 删除项目文件夹
                    if project.materials_path and os.path.exists(project.materials_path):
                        try:
                            shutil.rmtree(project.materials_path)
                        except Exception as e:
                            print(f"无法删除项目文件夹: {project.materials_path}, 错误: {str(e)}")
                    
                    # 删除项目记录
                    db.session.delete(project)
                    deleted_count += 1
            except Exception as e:
                print(f"删除项目 {project_id} 失败: {str(e)}")
        
        db.session.commit()
        return jsonify({'success': True, 'deleted_count': deleted_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@project_management_bp.route('/reject_tag/<int:request_id>')
@login_required
@role_required('admin')
@log_operation('拒绝标签申请')
def reject_tag(request_id):
    try:
        tag_request = TagRequest.query.get_or_404(request_id)
        db.session.delete(tag_request)
        db.session.commit()
        flash('标签请求已拒绝', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'拒绝标签请求失败: {str(e)}', 'danger')
    
    return redirect(url_for('project_management.manage_tag_requests'))

@project_management_bp.route('/get_project_details/<int:project_id>')
@login_required
@log_operation('获取项目详情')
def get_project_details(project_id):
    """获取项目详情的API"""
    try:
        # 查找项目
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404
        
        # 检查权限
        engineer = Engineer.query.filter_by(user_id=current_user.id).first()
        if engineer and project.assigned_engineer_id != engineer.id and current_user.role != 'admin':
            return jsonify({'error': '没有权限查看此项目'}), 403
        
        # 构建项目详情数据
        project_data = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'project_type': '定制' if project.project_type == 'custom' else '成品',
            'price': project.price,
            'cost': project.cost,
            'unit_price': project.unit_price,
            'engineer': project.assigned_engineer.name if project.assigned_engineer else '未分配',
            'group_name': project.group_name or '未设置',
            'tags': [{'id': tag.id, 'name': tag.name} for tag in project.tags],
            'created_time': project.created_time.strftime('%Y-%m-%d %H:%M:%S') if project.created_time else '',
            'progress': project.progress,
            'documents': [{'id': doc.id, 'filename': doc.filename, 'filepath': doc.filepath, 'type': doc.type} for doc in project.documents]
        }
        
        return jsonify(project_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500