from flask import Blueprint, render_template, redirect, url_for, session, request, flash, current_app
import json
import math
from flask import request
from flask_login import current_user
from routes.forms import AddAdminForm, AddEmployeeForm 
from routes.models import db
from routes.models import User, Project, Admin, Engineer, CustomerService, Trainee, Role, Permission, OperationLog
from routes.decorators import login_required, admin_required, super_admin_required, log_operation
from routes.models import TrainingMaterial

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_current_user_data():
    return {
        'username': current_user.username,
        'role': current_user.role,
        'role_level': current_user.role_level
    }


@admin_bp.route('/training_materials')
@login_required
@admin_required
@log_operation('访问培训资料管理页面')
def training_materials():
    # 重定向到培训资料管理页面
    return redirect(url_for('training.training_materials_manage'))

def get_current_user_data():
    return {
        'username': current_user.username,
        'role': current_user.role,
        'role_level': current_user.role_level
    }

# 然后在各个路由中使用
@admin_bp.route('/')
@login_required
@admin_required
@log_operation('访问管理员面板')
def admin_panel():
    current_user_data = get_current_user_data()
    # 添加调试信息
    current_app.logger.info(f"访问admin_panel: 用户 {current_user.username}, 角色 {current_user.role}, 权限级别 {current_user.role_level}")
    current_app.logger.info(f"Session内容: {dict(session)}")

    # 1. 关键统计数据
    total_projects = Project.query.count()
    assigned_projects = Project.query.filter(Project.assigned_engineer_id.isnot(None)).count()
    # 使用progress字段进行状态检查
    completed_projects = Project.query.filter_by(progress='已完成').count()

    stats = {
        'total_products': total_projects,  # 与前端模板保持一致
        'assigned_count': assigned_projects,
        'completed_count': completed_projects
    }

    # 2. 产品状态统计（与前端模板保持一致）
    completed_count = Project.query.filter_by(progress='已完成').count()
    in_progress_count = Project.query.filter(Project.progress!='已完成', Project.assigned_engineer_id.isnot(None)).count()
    unassigned_count = Project.query.filter(Project.assigned_engineer_id.is_(None)).count()
    
    product_status = {
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'unassigned_count': unassigned_count
    }

    # 3. 工程师任务分配统计
    # 移除未使用的task_count变量
    page = request.args.get('page', 1, type=int)
    per_page = 10

    engineers = User.query.filter_by(role='engineer').all()
    engineer_tasks = []
    for engineer_user in engineers:
        if engineer_user.engineer_profile and len(engineer_user.engineer_profile) > 0:
            engineer = engineer_user.engineer_profile[0]
            # 使用progress字段代替status字段，与系统保持一致
            task_count = Project.query.filter(Project.assigned_engineer_id == engineer.id, Project.progress != '已完成').count()
            engineer_tasks.append({'id': engineer_user.id, 'name': engineer.name, 'task_count': task_count})
    
    # 按任务数排序
    engineer_tasks.sort(key=lambda x: x['task_count'], reverse=True)

    # 分页
    total_engineers = len(engineers)
    total_pages = math.ceil(total_engineers / per_page) 
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paged_engineers = engineer_tasks[start_idx:end_idx]

    # 4. 获取最近添加的项目
    limit = request.args.get('limit', 5, type=int)
    recent_projects = Project.query.order_by(Project.created_time.desc()).limit(limit).all()

    return render_template(
        'admin.html',
        current_user=current_user,  # 只传递current_user对象
        stats=stats,
        product_status=product_status,  # 与前端模板保持一致
        engineer_tasks=paged_engineers,
        recent_products=recent_projects,  # 与前端模板保持一致
        page=page,
        total_pages=total_pages,
        limit=limit
    )

@admin_bp.route('/users')
@login_required
@admin_required
@log_operation('访问用户管理页面')
def admin_users():
    current_user_data = get_current_user_data()

    # 直接查询Admin模型
    admins = Admin.query.all()
    admins_data = [{
        'id': admin.user.id,
        'username': admin.user.username,
        'role_level': admin.user.role_level,
        'name': admin.name
    } for admin in admins]

    # 查询所有类型的员工（工程师、客服和试岗员工）
    employees = []
    
    # 查询工程师
    engineers = Engineer.query.all()
    for engineer in engineers:
        employees.append({
            'id': engineer.user.id,
            'name': engineer.name,
            'username': engineer.user.username,
            'role_level': 3,
            'role_detail': 'engineer'
        })
    
    # 查询客服
    customer_services = CustomerService.query.all()
    for cs in customer_services:
        # 检查user字段是否为空
        if cs.user:
            employees.append({
                'id': cs.user.id,
                'name': cs.name,
                'username': cs.user.username,
                'role_level': 3,
                'role_detail': 'customer_service'
            })
        else:
            # 只输出警告，不再将未关联用户添加到列表中
            print(f"警告: 客服员工记录缺少关联用户: {cs.name}")
    
    # 查询试岗员工
    trainees = Trainee.query.all()
    for trainee in trainees:
        # 检查user字段是否为空
        if trainee.user:
            employees.append({
                'id': trainee.user.id,
                'name': trainee.name,
                'username': trainee.user.username,
                'role_level': 4,
                'role_detail': 'trainee'
            })
        else:
            # 只输出警告，不再将未关联用户添加到列表中
            print(f"警告: 试岗员工记录缺少关联用户: {trainee.name}")

    return render_template('admin/users.html', 
                          current_user=current_user, 
                          admins=admins_data, 
                          employees=employees)

@admin_bp.route('/stats')
@login_required
@admin_required
@log_operation('访问统计页面')
def admin_stats():
    
    # 获取产品状态统计（与admin_panel保持一致，使用progress字段）
    completed_count = Project.query.filter_by(progress='已完成').count()
    in_progress_count = Project.query.filter(Project.progress!='已完成', Project.assigned_engineer_id.isnot(None)).count()
    unassigned_count = Project.query.filter(Project.assigned_engineer_id.is_(None)).count()
    
    # 获取工程师列表
    engineers = db.session.query(Engineer).all()
    
    # 准备图表数据
    engineer_names = []
    task_counts = []
    for engineer in engineers:
        engineer_names.append(engineer.name)
        # 使用progress字段代替status字段，与系统保持一致
        task_count = Project.query.filter(Project.assigned_engineer_id == engineer.id, Project.progress != '已完成').count()
        task_counts.append(task_count)
    
    # 在后端序列化JSON
    chart_data = {
        'engineer_names': json.dumps(engineer_names),
        'task_counts': json.dumps(task_counts)
    }
    
    return render_template('admin/stats.html', 
                          current_user=current_user, 
                          completed_count=completed_count, 
                          in_progress_count=in_progress_count, 
                          unassigned_count=unassigned_count, 
                          chart_data=chart_data,
                          engineers=engineers)  # 添加这一行传递工程师数据

@admin_bp.route('/engineer_projects')
@login_required
@admin_required
@log_operation('访问工程师项目列表')
def engineer_projects():
    # 获取工程师ID，优先使用手动输入的ID
    engineer_id = request.args.get('engineer_id_manual') or request.args.get('engineer_id')

    engineer = None
    projects = None

    if engineer_id:
        engineer = Engineer.query.get(engineer_id)
        if not engineer:
            flash('工程师不存在')
            return redirect(url_for('admin.admin_stats'))
        projects = Project.query.filter_by(assigned_engineer_id=engineer_id).order_by(Project.created_time.desc()).all()
    else:
        engineer = {'name': '所有工程师'}
        projects = Project.query.order_by(Project.created_time.desc()).all()

    return render_template('engineer_products.html', engineer=engineer, projects=projects)

@admin_bp.route('/add_admin', methods=['GET', 'POST'])
@login_required
@super_admin_required
@log_operation('添加管理员')
def add_admin():
    # 超级管理员只能有一个默认的，无法添加新的超级管理员
    form = AddAdminForm()
    # 移除超级管理员选项
    form.role_level.choices = [(1, '高级管理员'), (2, '普通管理员')]
    
    if form.validate_on_submit():
        name = form.name.data
        username = form.username.data
        password = form.password.data
        role_level = form.role_level.data

        try:
            # 检查用户名是否已存在
            if User.query.filter_by(username=username).first():
                flash('用户名已存在')
                return redirect(url_for('admin.add_admin'))

            # 创建新用户
            new_user = User(
                username=username,
                role='admin',
                role_level=role_level,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            # 创建管理员信息
            admin_info = Admin(user_id=new_user.id, name=name)
            db.session.add(admin_info)
            db.session.commit()

            flash('管理员添加成功')
            return redirect(url_for('admin.admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败: {str(e)}')
            return redirect(url_for('admin.add_admin'))

    return render_template('add_admin.html', form=form, current_user=current_user)

@admin_bp.route('/add_engineer', methods=['GET', 'POST'])
@login_required
@admin_required
@log_operation('添加员工')
def add_engineer():
    # 检查权限级别，只有0级和1级管理员可以添加员工
    if current_user.role_level > 1:
        flash('无权限添加员工账户')
        return redirect(url_for('admin.admin_users'))

    form = AddEmployeeForm()
    
    if form.validate_on_submit():
        name = form.name.data
        username = form.username.data
        password = form.password.data
        role_level = form.role_level.data
        role_detail = form.role_detail.data if form.role_detail.data else None

        try:
            # 检查用户名是否已存在
            if User.query.filter_by(username=username).first():
                flash('用户名已存在')
                return redirect(url_for('admin.add_engineer'))

            # 根据角色级别和详细角色确定角色名称
            if role_level == 3:
                user_role = role_detail if role_detail else 'engineer'
            elif role_level == 4:
                user_role = 'trainee'
            else:
                user_role = 'engineer'

            # 创建新用户
            new_user = User(
                username=username,
                role=user_role,
                role_level=role_level,
                role_detail=role_detail if role_level == 3 else None
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            # 根据角色创建对应的模型实例
            employee_name = form.name.data
            
            if role_level == 3:
                if role_detail == 'customer_service':
                    # 创建客服信息
                    from routes.models import CustomerService
                    cs_info = CustomerService(user_id=new_user.id, name=employee_name)
                    db.session.add(cs_info)
                    role_text = '客服'
                else:
                    # 创建工程师信息
                    engineer_info = Engineer(user_id=new_user.id, name=employee_name)
                    db.session.add(engineer_info)
                    role_text = '工程师'
            elif role_level == 4:
                # 创建试岗员工信息
                from routes.models import Trainee
                trainee_info = Trainee(user_id=new_user.id, name=employee_name)
                db.session.add(trainee_info)
                role_text = '试岗员工'
            else:
                # 默认创建工程师
                engineer_info = Engineer(user_id=new_user.id, name=employee_name)
                db.session.add(engineer_info)
                role_text = '工程师'
            
            db.session.commit()
            flash(f'{role_text}添加成功')
            return redirect(url_for('admin.admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败: {str(e)}')
            return redirect(url_for('admin.add_engineer'))

    return render_template('add_engineer.html', form=form, current_user=current_user)

@admin_bp.route('/set_admin_permission', methods=['POST'])
@login_required
@admin_required
@log_operation('设置管理员权限')
def set_admin_permission():
    from routes.decorators import can_modify_user
    
    user_id = request.form.get('admin_id')
    new_role_level = request.form.get('role_level')
    role_detail = request.form.get('role_detail')
    
    if not user_id or not new_role_level:
        flash('参数不完整')
        return redirect(url_for('admin.admin_users'))
    
    try:
        # 查找对应的用户
        user = User.query.get(user_id)
        if not user:
            flash('用户不存在')
            return redirect(url_for('admin.admin_users'))
        
        # 检查是否有权限修改该用户（只能修改比自己权限低的用户）
        if not can_modify_user(user):
            flash('无权限修改此用户权限')
            return redirect(url_for('admin.admin_users'))
        
        new_role_level = int(new_role_level)
        old_role = user.role
        old_role_level = user.role_level
        
        # 角色转换逻辑
        if new_role_level in (1, 2) and user.role != 'admin':
            # 工程师升级为管理员
            user.role = 'admin'
            user.role_level = new_role_level
            user.role_detail = None  # 管理员不需要详细角色
            user.updated_by = current_user.id
            
            # 先保存所有可能的角色名称
            person_name = None
            
            # 检查工程师信息
            engineer_info = Engineer.query.filter_by(user_id=user.id).first()
            if engineer_info:
                person_name = engineer_info.name
                db.session.delete(engineer_info)
            
            # 检查客服信息
            if not person_name:
                cs_info = CustomerService.query.filter_by(user_id=user.id).first()
                if cs_info:
                    person_name = cs_info.name
                    db.session.delete(cs_info)
            
            # 检查试岗员工信息
            if not person_name:
                trainee_info = Trainee.query.filter_by(user_id=user.id).first()
                if trainee_info:
                    person_name = trainee_info.name
                    db.session.delete(trainee_info)
            
            # 创建管理员信息
            # 为name字段提供默认值，避免违反NOT NULL约束
            admin_name = person_name if person_name else f"{user.username}(未设置姓名)"
            admin_info = Admin(user_id=user.id, name=admin_name)
            db.session.add(admin_info)
            
            flash(f'用户 {user.username} 已升级为管理员')
        elif new_role_level == 3 and user.role_level != 0:
            # 管理员降级为工程师或客服
            # 超级管理员无法被降级
            if user.role_level == 0:
                flash('超级管理员无法被降级')
                return redirect(url_for('admin.admin_users'))
            
            # 保存管理员名称，同时检查其他可能存在的角色表以获取真实姓名
            admin_info = Admin.query.filter_by(user_id=user.id).first()
            admin_name = admin_info.name if admin_info else None
            
            # 如果管理员表中没有找到姓名，尝试从其他角色表中查找
            if not admin_name:
                # 检查工程师信息
                engineer_info_tmp = Engineer.query.filter_by(user_id=user.id).first()
                if engineer_info_tmp:
                    admin_name = engineer_info_tmp.name
                
                # 检查客服信息
                if not admin_name:
                    cs_info_tmp = CustomerService.query.filter_by(user_id=user.id).first()
                    if cs_info_tmp:
                        admin_name = cs_info_tmp.name
                
                # 检查试岗员工信息
                if not admin_name:
                    trainee_info_tmp = Trainee.query.filter_by(user_id=user.id).first()
                    if trainee_info_tmp:
                        admin_name = trainee_info_tmp.name
            
            # 删除管理员信息(如果存在)
            if admin_info:
                db.session.delete(admin_info)
            
            # 删除其他角色信息(如果存在)
            engineer_info = Engineer.query.filter_by(user_id=user.id).first()
            if engineer_info:
                db.session.delete(engineer_info)
            
            cs_info = CustomerService.query.filter_by(user_id=user.id).first()
            if cs_info:
                db.session.delete(cs_info)
            
            trainee_info = Trainee.query.filter_by(user_id=user.id).first()
            if trainee_info:
                db.session.delete(trainee_info)
            
            if new_role_level == 3:
                # 降级为工程师或客服
                user.role = role_detail if role_detail in ('engineer', 'customer_service') else 'engineer'
                user.role_level = 3
                user.role_detail = role_detail if role_detail in ('engineer', 'customer_service') else 'engineer'
                user.updated_by = current_user.id
                
                # 创建对应角色信息
                # 为name字段提供默认值，避免违反NOT NULL约束
                display_name = admin_name if admin_name else f"{user.username}(未设置姓名)"
                if user.role == 'engineer':
                    engineer_info = Engineer(user_id=user.id, name=display_name)
                    db.session.add(engineer_info)
                else:
                    cs_info = CustomerService(user_id=user.id, name=display_name)
                    db.session.add(cs_info)
                
                role_text = '工程师' if role_detail == 'engineer' else '客服'
                flash(f'用户 {user.username} 已降级为{role_text}')
        else:
            # 同角色内部权限调整
            # 允许从正式员工(3级)降到试岗员工(4级)，或修改同级详细角色
            if (user.role_level == 3 and new_role_level == 4) or new_role_level < user.role_level or (new_role_level == user.role_level and role_detail):
                # 允许降级、从3级降到4级或修改同级详细角色
                user.role_level = new_role_level
                if role_detail:
                    user.role_detail = role_detail
                user.updated_by = current_user.id
                flash(f'用户 {user.username} 权限已更新')
            else:
                flash('无法提升用户权限')
                return redirect(url_for('admin.admin_users'))
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'更新失败: {str(e)}')
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/remove_admin', methods=['POST'])
@login_required
@admin_required
@log_operation('移除管理员')
def remove_admin():
    from routes.decorators import can_modify_user
    
    try:
        # 从表单获取管理员ID
        admin_id = request.form.get('admin_user_id')
        if not admin_id:
            flash('参数错误')
            return redirect(url_for('admin.admin_users'))
            
        # 查找对应的用户
        user = User.query.get(admin_id)
        if not user or user.role != 'admin':
            flash('管理员不存在')
            return redirect(url_for('admin.admin_users'))
        
        # 超级管理员无法被删除
        if user.role_level == 0:
            flash('超级管理员无法被删除')
            return redirect(url_for('admin.admin_users'))
        
        # 检查是否有权限删除该用户
        if not can_modify_user(user):
            flash('无权限删除此管理员')
            return redirect(url_for('admin.admin_users'))
        
        # 查找管理员信息
        admin_info = Admin.query.filter_by(user_id=admin_id).first()
        
        # 查找用户的真实姓名，同时检查其他可能存在的角色表
        real_name = None
        if admin_info:
            real_name = admin_info.name
        
        # 如果管理员表中没有找到姓名，尝试从其他角色表中查找
        if not real_name:
            # 检查工程师信息
            engineer_info_tmp = Engineer.query.filter_by(user_id=admin_id).first()
            if engineer_info_tmp:
                real_name = engineer_info_tmp.name
            
            # 检查客服信息
            if not real_name:
                cs_info_tmp = CustomerService.query.filter_by(user_id=admin_id).first()
                if cs_info_tmp:
                    real_name = cs_info_tmp.name
            
            # 检查试岗员工信息
            if not real_name:
                trainee_info_tmp = Trainee.query.filter_by(user_id=admin_id).first()
                if trainee_info_tmp:
                    real_name = trainee_info_tmp.name
        
        # 如果没有找到任何角色信息，显示错误
        if not admin_info and not real_name:
            flash('管理员信息不存在')
            return redirect(url_for('admin.admin_users'))
        
        # 将用户角色改为工程师（降级）
        user.role = 'engineer'
        user.role_level = 3
        user.role_detail = 'engineer'
        user.updated_by = current_user.id
        
        # 删除管理员信息
        db.session.delete(admin_info)
        
        # 创建工程师信息，使用查找的真实姓名，并提供默认值避免NULL
        display_name = real_name if real_name else f"{user.username}(未设置姓名)"
        engineer_info = Engineer(user_id=admin_id, name=display_name)
        db.session.add(engineer_info)
        
        db.session.commit()
        flash('管理员已降级为工程师')
    except Exception as e:
        db.session.rollback()
        flash(f'操作失败: {str(e)}')
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/remove_engineer', methods=['POST'])
@login_required
@admin_required
@log_operation('移除工程师')
def remove_engineer():
    try:
        # 从表单获取工程师ID
        engineer_id = request.form.get('user_id')
        if not engineer_id:
            flash('参数错误')
            return redirect(url_for('admin.admin_users'))
            
        # 查找对应的用户
        user = User.query.get(engineer_id)
        if not user or user.role != 'engineer':
            flash('工程师不存在')
            return redirect(url_for('admin.admin_users'))
        
        # 检查权限 (只有0级和1级管理员可以删除工程师)
        if current_user.role_level > 1:
            flash('无权限删除工程师')
            return redirect(url_for('admin.admin_users'))
        
        # 查找工程师信息
        engineer_info = Engineer.query.filter_by(user_id=engineer_id).first()
        if not engineer_info:
            flash('工程师信息不存在')
            return redirect(url_for('admin.admin_users'))
        
        # 解除该工程师分配的所有项目
        projects = Project.query.filter_by(assigned_engineer_id=engineer_info.id).all()
        for project in projects:
            project.assigned_engineer_id = None
            project.progress = '未开始'
            project.updated_by = current_user.id
        
        # 删除工程师信息
        db.session.delete(engineer_info)
        
        # 删除用户账号
        db.session.delete(user)
        
        db.session.commit()
        flash('工程师已移除')
    except Exception as e:
        db.session.rollback()
        flash(f'操作失败: {str(e)}')
    
    return redirect(url_for('admin.admin_users'))
