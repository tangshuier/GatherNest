from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user, login_required
from routes.models import OperationLog, db, Role, Permission

# 记录权限检查日志

def log_permission_check(action, resource, success):
    try:
        log = OperationLog(
            username=current_user.username if current_user.is_authenticated else 'anonymous',
            operation='权限检查',
            module='permissions',
            ip=request.remote_addr,
            user_agent=str(request.user_agent),
            params=f"action={action}, resource={resource}, success={success}",
            success=success
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"记录权限检查日志时出错: {e}")
        db.session.rollback()

# 检查用户是否有特定权限
def has_permission(permission_code):
    # 超级管理员拥有所有权限
    if current_user.role_level == 0:
        return True
    
    # 检查会话中缓存的权限
    from flask import session
    permissions = session.get('permissions', [])
    
    # 如果会话中没有权限信息，从数据库重新获取
    if not permissions:
        user_role = Role.query.filter_by(name=current_user.role).first()
        if user_role:
            permissions = [p.code for p in user_role.permissions]
            session['permissions'] = permissions
    
    return permission_code in permissions

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # 支持旧的role_level检查和新的RBAC权限检查
        # 同时支持'super_admin'和'admin'角色
        has_admin_role = (current_user.role in ['admin', 'super_admin'] and 
                         current_user.role_level in (0, 1, 2))
        has_admin_perm = has_permission('admin_access')
        
        if not (has_admin_role or has_admin_perm):
            flash('无权限访问此页面')
            log_permission_check('访问', 'admin_panel', False)
            return redirect(url_for('auth.login'))
        
        log_permission_check('访问', 'admin_panel', True)
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # 支持旧的role_level检查和新的RBAC权限检查
        # 同时支持'super_admin'和'admin'角色
        is_super_admin = (current_user.role in ['admin', 'super_admin'] and 
                         current_user.role_level == 0)
        has_super_admin_perm = has_permission('super_admin_access')
        
        if not (is_super_admin or has_super_admin_perm):
            flash('无权限访问此页面')
            log_permission_check('访问', 'super_admin_panel', False)
            return redirect(url_for('auth.login'))
        
        log_permission_check('访问', 'super_admin_panel', True)
        return f(*args, **kwargs)
    return decorated_function

# 检查是否有修改用户的权限（只能修改比自己权限低的用户）
def can_modify_user(target_user):
    # 超级管理员可以修改所有用户，除了自己
    if current_user.role_level == 0 or has_permission('modify_all_users'):
        return target_user.role_level != 0 or current_user.id != target_user.id
    # 其他管理员只能修改比自己权限低的用户
    return current_user.role_level < target_user.role_level

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # 处理传递列表作为单个参数的情况
            roles_to_check = []
            if len(allowed_roles) == 1 and isinstance(allowed_roles[0], list):
                roles_to_check = allowed_roles[0]
            else:
                roles_to_check = allowed_roles
                
            # 首先检查角色是否匹配
            role_match = current_user.role in roles_to_check
            
            # 同时支持RBAC权限检查
            has_required_perm = any(has_permission(role + '_access') for role in roles_to_check)
            
            if not (role_match or has_required_perm):
                flash('无权限访问此页面')
                log_permission_check('访问', f'role_{"_".join(roles_to_check)}_resource', False)
                return redirect(url_for('auth.login'))
            
            log_permission_check('访问', f'role_{"_".join(roles_to_check)}_resource', True)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 基于RBAC的权限装饰器
def permission_required(permission_code):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not has_permission(permission_code):
                flash('无权限执行此操作')
                log_permission_check('执行', permission_code, False)
                return redirect(url_for('auth.login'))
            
            log_permission_check('执行', permission_code, True)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def engineer_required(f):
    """工程师权限装饰器，允许admin和engineer角色访问"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # 支持旧的角色检查和新的RBAC权限检查
        has_engineer_role = current_user.role in ['admin', 'engineer']
        has_engineer_perm = has_permission('engineer_access')
        
        if not (has_engineer_role or has_engineer_perm):
            flash('无权限访问此页面')
            log_permission_check('访问', 'engineer_resource', False)
            return redirect(url_for('auth.login'))
        
        log_permission_check('访问', 'engineer_resource', True)
        return f(*args, **kwargs)
    return decorated_function

# 操作日志记录装饰器 - 简化版本，只支持 @log_operation('login') 格式
def log_operation(operation_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 记录操作日志的实际逻辑
            try:
                username = current_user.username if current_user.is_authenticated else 'anonymous'
                module = f.__module__.split('.')[-1]  # 获取模块名
                
                log = OperationLog(
                    username=username,
                    operation=operation_name,
                    module=module,
                    ip=request.remote_addr,
                    user_agent=str(request.user_agent),
                    params=str(kwargs) if kwargs else None,
                    result='操作成功',
                    success=True
                )
                db.session.add(log)
                db.session.commit()
                
                # 执行原函数
                return f(*args, **kwargs)
            except Exception as e:
                # 记录失败日志
                try:
                    username = current_user.username if current_user.is_authenticated else 'anonymous'
                    module = f.__module__.split('.')[-1]
                    
                    log = OperationLog(
                        username=username,
                        operation=operation_name,
                        module=module,
                        ip=request.remote_addr,
                        user_agent=str(request.user_agent),
                        params=str(kwargs) if kwargs else None,
                        result=f'操作失败: {str(e)}',
                        success=False
                    )
                    db.session.add(log)
                    db.session.commit()
                except:
                    # 如果日志记录失败，不影响原函数执行
                    pass
                # 重新抛出异常，让调用方处理
                raise
        return decorated_function
    return decorator
