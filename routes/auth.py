from flask import Blueprint, redirect, url_for, flash, session, render_template, request, make_response
from flask_login import login_user, logout_user, login_required, current_user
import uuid
from routes.forms import LoginForm, RegisterForm
from routes.models import User, Engineer, CustomerService, Trainee, db, Role, Permission, OperationLog
from routes.decorators import can_modify_user, log_operation

auth_bp = Blueprint('auth', __name__)

# 记录操作日志辅助函数
def log_operation_helper(username, operation, module, success=True, params=None):
    try:
        log = OperationLog(
            username=username,
            operation=operation,
            module=module,
            ip=request.remote_addr,
            user_agent=str(request.user_agent),
            params=str(params) if params else None,
            success=success
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"记录操作日志时出错: {e}")
        db.session.rollback()

@auth_bp.route('/login', methods=['GET', 'POST'])
@log_operation('login')
def login():
    if current_user.is_authenticated:
        # 根据用户角色和权限级别重定向到适当的面板
        if current_user.role_level == 0:
            return redirect(url_for('admin.admin_panel'))  # 超级管理员
        elif current_user.role_level in [1, 2]:
            return redirect(url_for('admin.admin_panel'))  # 高级管理员和普通管理员
        elif current_user.role_level == 3:
            # 区分工程师和客服
            if current_user.role_detail == 'customer_service':
                return redirect(url_for('user.customer_service_panel'))
            else:
                return redirect(url_for('user.engineer_panel'))
        else:
            return redirect(url_for('user.trainee_panel'))  # 试岗员工
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # 生成唯一会话ID
            session_id = str(uuid.uuid4())[:8]
            
            # 检查用户是否已有活跃会话（登录互斥逻辑）
            old_session_id = user.active_session_id
            if old_session_id:
                # 从app模块导入active_sessions字典
                from app import active_sessions
                # 标记旧会话为无效（可以选择删除或标记为无效）
                if old_session_id in active_sessions:
                    active_sessions[old_session_id]['is_valid'] = False
                # 移除多设备登录提示，保持静默处理
            
            # 更新用户的活跃会话ID
            user.active_session_id = session_id
            db.session.commit()
            
            # 清理现有session以避免冲突，但保留CSRF token和flash消息
            for key in list(session.keys()):
                if key not in ['_flashes', 'csrf_token']:  # 保留flash消息和CSRF token
                    session.pop(key)
            
            # 设置会话参数
            session['session_id'] = session_id
            session['user_id'] = user.id
            
            # 将角色和权限级别信息存入session
            session['role_level'] = user.role_level
            session['role_detail'] = user.role_detail or ''
            
            # 确保session被标记为已修改，防止会话信息丢失
            session.modified = True
            
            # 允许remember参数，但使用session而非cookie来存储登录状态
            login_user(user, remember=False)
            
            # 获取用户权限信息并存储到会话中
            user_role = Role.query.filter_by(name=user.role).first()
            if user_role:
                session['permissions'] = [p.code for p in user_role.permissions]
            else:
                session['permissions'] = []
            
            flash('登录成功')
            
            # 记录登录成功日志
            log_operation_helper(username, '用户登录', 'auth', True, {'username': username})
            
            # 根据角色和权限级别重定向
            if user.role_level == 0:
                return redirect(url_for('admin.admin_panel'))  # 超级管理员
            elif user.role_level in [1, 2]:
                return redirect(url_for('admin.admin_panel'))  # 高级管理员和普通管理员
            elif user.role_level == 3:
                # 区分工程师和客服
                if user.role_detail == 'customer_service':
                    return redirect(url_for('user.customer_service_panel'))
                else:
                    return redirect(url_for('user.engineer_panel'))
            else:
                return redirect(url_for('user.trainee_panel'))  # 试岗员工
        else:
            flash('用户名或密码不正确')
            # 记录登录失败日志
            log_operation_helper(username, '用户登录', 'auth', False, {'username': username})
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
@log_operation('register')
def register():
    if current_user.is_authenticated:
        # 根据用户角色和权限级别重定向
        if current_user.role_level == 0:
            return redirect(url_for('admin.admin_panel'))
        elif current_user.role_level in [1, 2]:
            return redirect(url_for('admin.admin_panel'))
        elif current_user.role_level == 3:
            if current_user.role_detail == 'customer_service':
                return redirect(url_for('user.customer_service_panel'))
            else:
                return redirect(url_for('user.engineer_panel'))
        else:
            return redirect(url_for('user.trainee_panel'))

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        name = form.name.data

        try:
            if User.query.filter_by(username=username).first():
                flash('用户名已存在')
                log_operation_helper(username, '用户注册', 'auth', False, {'username': username, 'reason': '用户名已存在'})
                return redirect(url_for('auth.register'))

            # 默认注册为试岗员工
            new_user = User(
                username=username,
                role='engineer',  # 基础角色类型
                role_level=4,     # 试岗员工级别
                role_detail='trainee',  # 详细角色标识
                created_by='system',  # 记录创建者
                updated_by='system'  # 记录更新者
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            # 创建试岗员工信息
            trainee_info = Trainee(user_id=new_user.id, name=name)
            db.session.add(trainee_info)
            db.session.commit()

            flash('注册成功，请登录。您当前为试岗员工状态，需要管理员审核后才能升级。')
            log_operation_helper(username, '用户注册', 'auth', True, {'username': username, 'name': name})
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败: {str(e)}')
            log_operation_helper(username, '用户注册', 'auth', False, {'username': username, 'error': str(e)})
            return redirect(url_for('auth.register'))

    return render_template('register.html', form=form)

@auth_bp.route('/force_logout')
@log_operation('force_logout')
def force_logout():
    # 记录强制登出前的用户名
    username = current_user.username if current_user.is_authenticated else 'unknown'
    
    # 清理会话信息
    session_id = session.get('session_id')
    if session_id:
        from app import active_sessions
        if session_id in active_sessions:
            del active_sessions[session_id]
    
    # 清除session
    session.clear()
    
    # 登出用户（即使在未登录状态下也安全）
    if current_user.is_authenticated:
        # 清除用户数据库中的活跃会话ID
        current_user.active_session_id = None
        db.session.commit()
        logout_user()
    
    # 记录强制登出日志
    log_operation_helper(username, '用户强制登出', 'auth', True, {'session_id': session_id})
    
    # 渲染强制登出页面
    return render_template('force_logout.html')

@auth_bp.route('/logout')
@login_required
@log_operation('logout')
def logout():
    # 记录登出前的用户名
    username = current_user.username if current_user.is_authenticated else 'unknown'
    
    # 清除用户数据库中的活跃会话ID（登录互斥逻辑）
    if current_user.is_authenticated:
        current_user.active_session_id = None
        db.session.commit()
    
    # 从活跃会话字典中删除当前会话
    session_id = session.get('session_id')
    if session_id:
        from app import active_sessions
        if session_id in active_sessions:
            del active_sessions[session_id]
    
    # 清理session
    session.clear()
    # 登出用户
    logout_user()
    
    # 记录登出日志
    log_operation_helper(username, '用户登出', 'auth', True)
    
    flash('已退出登录')
    return redirect(url_for('auth.login'))