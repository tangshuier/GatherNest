from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
import json
import logging
from logging.handlers import RotatingFileHandler
from logging import Formatter
from functools import wraps
from routes.models import User
import hashlib
import subprocess
import sys

# 初始化应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # 使用随机生成的密钥，提高安全性
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'documents')
app.config['VIDEO_UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'videos')

# 添加测试路由以验证日志功能
@app.route('/test/404')
def test_404():
    # 重定向到不存在的页面以测试404错误处理
    return redirect(url_for('non_existent_route'))

@app.route('/test/500')
def test_500():
    # 触发500错误以测试内部服务器错误处理
    raise Exception("这是一个测试性的服务器错误")

@app.route('/test/logging')
def test_logging():
    # 测试不同级别的日志记录
    app.logger.debug("这是一条调试日志")
    app.logger.info("这是一条信息日志")
    app.logger.warning("这是一条警告日志")
    app.logger.error("这是一条错误日志")
    return "日志测试完成，请检查日志文件"

# 创建测试404.html和500.html模板
if not os.path.exists('templates/404.html'):
    os.makedirs('templates', exist_ok=True)
    with open('templates/404.html', 'w', encoding='utf-8') as f:
        f.write('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>页面未找到</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { font-size: 50px; color: #333; }
                p { font-size: 18px; color: #666; }
                a { color: #0066cc; text-decoration: none; }
            </style>
        </head>
        <body>
            <h1>404</h1>
            <p>抱歉，您访问的页面不存在。</p>
            <a href="/">返回首页</a>
        </body>
        </html>
        ''')

if not os.path.exists('templates/500.html'):
    os.makedirs('templates', exist_ok=True)
    with open('templates/500.html', 'w', encoding='utf-8') as f:
        f.write('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>服务器错误</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { font-size: 50px; color: #333; }
                p { font-size: 18px; color: #666; }
                a { color: #0066cc; text-decoration: none; }
            </style>
        </head>
        <body>
            <h1>500</h1>
            <p>抱歉，服务器内部发生了错误。</p>
            <p>我们已经记录了这个错误，技术人员将尽快处理。</p>
            <a href="/">返回首页</a>
        </body>
        </html>
        ''')

# 配置日志格式，添加用户名信息
import logging
from flask import request
from flask_login import current_user

# 创建日志文件夹
import os
LOGS_DIR = 'logs'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# 配置基本日志记录到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 配置错误日志文件处理器
import datetime
log_filename = os.path.join(LOGS_DIR, f'error_log_{datetime.datetime.now().strftime("%Y%m%d")}.log')
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.WARNING)  # 降低级别以捕获警告和错误

# 创建一个更加健壮的格式化器，处理可能缺失的字段
class SafeFormatter(logging.Formatter):
    def format(self, record):
        # 确保所有必需的字段都有默认值
        record.request = getattr(record, 'request', 'N/A')
        record.user = getattr(record, 'user', 'anonymous')
        record.ip = getattr(record, 'ip', 'N/A')
        record.session = getattr(record, 'session', 'N/A')
        record.error_details = getattr(record, 'error_details', 'N/A')
        return super().format(record)

file_formatter = SafeFormatter(
    '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s\n' +
    'Request: %(request)s\nUser: %(user)s\nIP: %(ip)s\nSession: %(session)s\nError Details: %(error_details)s\n' +
    '-'*80
)
file_handler.setFormatter(file_formatter)

# 移除可能存在的旧处理器，避免重复
root_logger = logging.getLogger()
for handler in list(root_logger.handlers):
    if isinstance(handler, logging.FileHandler):
        root_logger.removeHandler(handler)

# 添加新的文件处理器
root_logger.addHandler(file_handler)
# 设置根日志记录器的级别
root_logger.setLevel(logging.INFO)

# 添加服务器启动日志
app.logger.info("正在初始化日志系统...")

# 创建一个增强的请求日志装饰器，包含异常捕获
def log_requests():
    @app.after_request
    def after_request(response):
        # 跳过静态文件
        if request.path.startswith('/static/'):
            return response
        
        # 获取IP地址
        ip = request.remote_addr
        
        # 安全地获取用户名
        username = 'anonymous'
        try:
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                if hasattr(current_user, 'username'):
                    username = current_user.username
        except Exception as e:
            app.logger.error(f"获取用户名时出错: {str(e)}")
        
        # 记录请求信息
        log_message = f"{ip} - {username} - {request.method} {request.path} - {response.status_code}"
        
        # 根据响应状态码决定日志级别
        if response.status_code >= 500:
            app.logger.error(log_message)
        elif response.status_code >= 400:
            app.logger.warning(log_message)
        else:
            app.logger.info(log_message)
            
        return response
    
    # 添加请求前处理，捕获全局异常
    @app.before_request
    def before_request():
        # 可以在这里添加请求前的额外处理
        pass
    
    # 添加teardown_appcontext处理函数，确保即使请求失败也能记录异常
    @app.teardown_request
    def teardown_request(exception):
        if exception:
            # 获取详细的异常信息
            import traceback
            error_trace = traceback.format_exc()
            
            # 获取请求信息
            try:
                request_info = f"{request.method} {request.path} {request.query_string.decode('utf-8')}"
            except:
                request_info = "Unknown request"
            
            # 获取用户信息
            username = 'anonymous'
            try:
                if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                    if hasattr(current_user, 'username'):
                        username = current_user.username
            except:
                pass
            
            # 获取IP地址
            ip = request.remote_addr if request else "Unknown IP"
            
            # 获取会话信息
            session_info = str(dict(session)) if 'session' in locals() else "No session"
            
            # 记录异常到日志文件
            logger = logging.getLogger()
            extra_info = {
                'request': request_info,
                'user': username,
                'ip': ip,
                'session': session_info,
                'error_details': error_trace
            }
            logger.error(f"请求处理异常: {str(exception)}", extra=extra_info)

# 应用装饰器
log_requests()
app.logger.info("日志系统初始化完成，已应用请求日志装饰器")

# 自定义错误处理函数 - 404 错误处理
@app.errorhandler(404)
def page_not_found(error):
    # 获取请求信息
    try:
        request_info = f"{request.method} {request.path} {request.query_string.decode('utf-8')}"
    except Exception:
        request_info = f"{request.method} {request.path}"
    
    # 获取用户信息
    user_info = 'anonymous'
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            if hasattr(current_user, 'username'):
                user_info = current_user.username
    except Exception:
        pass
    
    # 获取IP地址
    ip_address = request.remote_addr
    
    # 获取会话信息
    try:
        session_info = str(dict(session))
    except Exception:
        session_info = "无法获取会话信息"
    
    # 记录详细的404错误信息到日志文件
    logger = logging.getLogger()
    # 使用更简单的方式记录，确保信息被写入
    logger.warning(
        f"页面未找到 (404): {request.path} | IP: {ip_address} | 用户: {user_info} | 请求: {request_info}"
    )
    
    # 同时使用extra参数记录详细信息
    try:
        logger.error(
            f"页面未找到 (404): {request.path}",
            extra={
                'request': request_info,
                'user': user_info,
                'ip': ip_address,
                'session': session_info,
                'error_details': str(error)
            }
        )
    except Exception as log_error:
        # 如果extra方式失败，至少用普通方式记录
        logger.error(f"记录404详细日志失败: {str(log_error)}")
    
    # 返回404页面
    return render_template('404.html'), 404

# 自定义错误处理函数 - 500 错误处理
@app.errorhandler(500)
def internal_server_error(error):
    # 获取请求信息
    try:
        request_info = f"{request.method} {request.path} {request.query_string.decode('utf-8')}"
    except Exception:
        request_info = f"{request.method} {request.path}"
    
    # 获取用户信息
    user_info = 'anonymous'
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            if hasattr(current_user, 'username'):
                user_info = current_user.username
    except Exception:
        pass
    
    # 获取IP地址
    ip_address = request.remote_addr
    
    # 获取会话信息
    try:
        session_info = str(dict(session))
    except Exception:
        session_info = "无法获取会话信息"
    
    # 获取错误堆栈
    import traceback
    try:
        error_trace = traceback.format_exc()
    except Exception:
        error_trace = str(error)
    
    # 记录详细的500错误信息到日志文件
    logger = logging.getLogger()
    
    # 先使用简单方式记录，确保信息被写入
    logger.error(
        f"服务器内部错误 (500): {str(error)} | IP: {ip_address} | 用户: {user_info} | 请求: {request_info}"
    )
    
    # 然后尝试使用extra参数记录详细信息
    try:
        logger.error(
            f"服务器内部错误 (500): {str(error)}",
            extra={
                'request': request_info,
                'user': user_info,
                'ip': ip_address,
                'session': session_info,
                'error_details': error_trace
            }
        )
    except Exception as log_error:
        # 如果extra方式失败，至少记录堆栈信息
        logger.error(f"记录500详细日志失败: {str(log_error)}")
        logger.error(f"错误堆栈: {error_trace}")
    
    # 返回500页面
    return render_template('500.html'), 500

app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls', 'csv', 'doc', 'docx', 'pdf', 'mp4', 'avi', 'mov', 'wmv', 'md'}

# 文件大小限制设置
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 全局最大限制200MB
app.config['MAX_VIDEO_SIZE'] = 200 * 1024 * 1024  # 视频文件最大200MB
app.config['MAX_ENGINEERING_SIZE'] = 50 * 1024 * 1024  # 工程文件最大50MB
app.config['MAX_IMAGE_SIZE'] = 10 * 1024 * 1024  # 图片文件最大10MB
# 会话配置
app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止JavaScript访问cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 防止跨站请求伪造
# 使用固定的session cookie名称
app.config['SESSION_COOKIE_NAME'] = 'training_system_session'
# 添加自定义会话ID支持
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 会话有效期1小时

csrf = CSRFProtect(app)

# 存储活跃会话的字典
active_sessions = {}

# 请求前处理器 - 实现会话隔离和登录互斥
@app.before_request
def manage_session():
    # 跳过静态文件请求、强制登出路由、登录和注册路由
    skip_routes = ['/static/', '/force_logout', '/login', '/register']
    if any(request.path.startswith(route) for route in skip_routes):
        return
    
    # 检测潜在的重定向循环
    redirect_count = session.get('_redirect_count', 0)
    # 增加阈值到5次，并添加更严格的判断条件
    if redirect_count > 5:  # 提高阈值，避免正常操作被误判
        # 记录重定向历史以进行更精确的循环检测
        redirect_history = session.get('_redirect_history', [])
        current_path = request.path
        
        # 检查是否在同一个路径连续重定向多次
        if current_path in redirect_history[-3:] and len(redirect_history) >= 3:
            # 重置重定向计数和历史
            session.pop('_redirect_count', None)
            session.pop('_redirect_history', None)
            # 清理会话并重定向到登录页
            flash('检测到异常的重定向循环，已重置会话')
            return redirect(url_for('auth.logout'))
        
        # 更新重定向历史
        redirect_history.append(current_path)
        if len(redirect_history) > 10:  # 只保留最近10次记录
            redirect_history = redirect_history[-10:]
        session['_redirect_history'] = redirect_history
    
    # 从URL参数或表单数据中获取session_id
    session_id = request.args.get('session_id') or request.form.get('session_id')
    current_session_id = session.get('session_id')
    
    # 如果URL或表单中有session_id且与当前session不同，才进行会话恢复
    if session_id and session_id != current_session_id:
        # 检查是否有这个会话ID的活跃会话
        if session_id in active_sessions:
            # 检查会话是否有效
            if active_sessions[session_id].get('is_valid', True):
                # 恢复会话信息
                session_info = active_sessions[session_id]
                # 验证用户是否仍然有效
                user = User.query.get(session_info.get('user_id'))
                if user:
                    # 检查用户的活跃会话ID是否与当前会话匹配（登录互斥检查）
                    if user.active_session_id != session_id:
                        # 如果不匹配，说明用户在其他地方登录了
                        return redirect(url_for('auth.force_logout'))
                    
                    # 确保当前会话与这个用户关联
                    if current_user.is_authenticated and current_user.id != user.id:
                        # 如果当前用户与会话用户不匹配，重新登录
                        login_user(user)
                    session['session_id'] = session_id
                    session['user_id'] = user.id
                    session['role_level'] = session_info.get('role_level')
                    session['role_detail'] = session_info.get('role_detail')
                    g.current_session_id = session_id
            else:
                # 会话已无效，重定向到登录页
                flash('您的会话已失效，请重新登录')
                return redirect(url_for('auth.logout'))
    
    # 如果用户已认证但会话ID不存在或不匹配，重新创建会话
    if current_user.is_authenticated and (not current_session_id or current_session_id not in active_sessions):
        # 生成新的会话ID
        new_session_id = str(uuid.uuid4())[:8]
        # 更新用户的活跃会话ID
        try:
            current_user.active_session_id = new_session_id
            from routes.models import db
            db.session.commit()
        except Exception as e:
            if hasattr(app, 'logger'):
                app.logger.error(f"更新用户active_session_id失败: {str(e)}")
        # 设置会话参数
        session['session_id'] = new_session_id
        session['user_id'] = current_user.id
        session['role_level'] = current_user.role_level
        session['role_detail'] = current_user.role_detail or ''
        # 确保session被标记为已修改
        session.modified = True
        current_session_id = new_session_id
    
    # 如果当前会话有session_id，进行会话有效性检查和更新
    if current_session_id and current_user.is_authenticated:
        # 获取用户信息
        user = current_user
        
        # 优化会话验证逻辑：确保用户的active_session_id与会话ID匹配
        if user.active_session_id != current_session_id:
            # 更新用户的active_session_id以匹配当前会话
            try:
                user.active_session_id = current_session_id
                from routes.models import db
                db.session.commit()
            except Exception as e:
                # 如果更新失败，记录错误但不强制登出
                if hasattr(app, 'logger'):
                    app.logger.error(f"更新用户active_session_id失败: {str(e)}")
        
        # 更新活跃会话信息
        active_sessions[current_session_id] = {
            'user_id': current_user.id,
            'role_level': session.get('role_level'),
            'role_detail': session.get('role_detail'),
            'last_activity': request.url,
            'is_valid': True  # 标记会话为有效
        }
        g.current_session_id = current_session_id
    # 设置默认值，避免模板中出现None
    if not hasattr(g, 'current_session_id'):
        g.current_session_id = None

# 响应后处理器 - 跟踪重定向次数和历史
@app.after_request
def track_redirects(response):
    # 检查是否是重定向响应
    if response.status_code in (301, 302, 303, 307, 308):
        # 增加重定向计数
        redirect_count = session.get('_redirect_count', 0)
        session['_redirect_count'] = redirect_count + 1
        # 在重定向时不更新历史，由before_request处理
    else:
        # 非重定向响应重置计数和历史
        session.pop('_redirect_count', None)
        session.pop('_redirect_history', None)
    # 必须返回response对象
    return response

# 添加Jinja2上下文处理器，确保在所有模板中都能访问session_id
@app.context_processor
def inject_session_id():
    # 只在有有效会话时提供session_id，避免在未登录状态下注入
    if current_user.is_authenticated and hasattr(g, 'current_session_id'):
        return dict(current_session_id=g.current_session_id)
    return dict(current_session_id=None)

# 确保实例文件夹存在
os.makedirs(app.instance_path, exist_ok=True)
# 确保上传文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化数据库
from routes.models import db
from sqlalchemy import text
db.init_app(app)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面'

# 优化SQLite数据库配置
def configure_sqlite_optimizations():
    with app.app_context():
        # 启用外键约束
        db.session.execute(text('PRAGMA foreign_keys = ON'))
        # 启用WAL日志模式
        db.session.execute(text('PRAGMA journal_mode = WAL'))
        # 设置同步级别为NORMAL
        db.session.execute(text('PRAGMA synchronous = NORMAL'))
        # 使用内存临时存储
        db.session.execute(text('PRAGMA temp_store = MEMORY'))
        # 设置缓存大小（约64MB）
        db.session.execute(text('PRAGMA cache_size = -8000'))
        db.session.commit()

# 记录操作日志
def log_operation(username, operation, module, success=True, params=None, result=None):
    try:
        from routes.models import OperationLog
        log = OperationLog(
            username=username,
            operation=operation,
            module=module,
            ip=request.remote_addr,
            user_agent=str(request.user_agent),
            params=str(params) if params else None,
            result=str(result) if result else None,
            success=success
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"记录操作日志时出错: {e}")
        db.session.rollback()

# 从routes.decorators导入权限检查装饰器，避免重复定义
from routes.decorators import permission_required as decorators_permission_required
# 重命名为本地使用
permission_required = decorators_permission_required

# 用户加载回调
from routes.models import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from routes.auth import auth_bp
from routes.user import user_bp

# from routes.project import project_bp  # 注释掉project_bp以避免与project_management_bp冲突
from routes.video import video_bp
from admin_blueprint import admin_bp
from routes.training import training_bp
from routes.project_management import project_management_bp
from routes.document_viewer import document_viewer_bp
from routes.models import TrainingMaterial
from routes.decorators import login_required, role_required

# 注册蓝图，确保不会有冲突
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
# app.register_blueprint(project_bp)  # 注释掉project_bp以避免与project_management_bp冲突
app.register_blueprint(video_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(training_bp, url_prefix='/training')
app.register_blueprint(project_management_bp, url_prefix='/project_management')
app.register_blueprint(document_viewer_bp)
# app.register_blueprint(project_management_bp, url_prefix='/projects')  # 暂时注释，避免路由冲突

# 根路由重定向 - 修复侧边栏/profile链接问题
@app.route('/profile')
def root_profile_redirect():
    return redirect(url_for('user.update_profile'))

# 修复管理员页面项目管理相关路由404错误
@app.route('/projects/management')
@login_required
def projects_management_redirect():
    return redirect(url_for('project_management.projects_list'))

# 修复添加项目页面路由404错误
@app.route('/projects/add')
@login_required
def projects_add_redirect():
    return redirect(url_for('project_management.add_project'))

# 修复编辑项目页面路由404错误
@app.route('/projects/edit/<int:project_id>')
@login_required
def projects_edit_redirect(project_id):
    return redirect(url_for('project_management.edit_project', project_id=project_id))

# 错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# 添加处理/@vite/client的路由
@app.route('/@vite/client')
def vite_client():
    return '', 204  # 返回空响应

# 主页路由
@app.route('/')
def index():
    return redirect(url_for('auth.login'))

# 布尔值修复测试路由
@app.route('/test_boolean_fix')
def test_boolean_fix():
    return render_template('test_boolean_fix.html')

# 注意：/training_materials路由已移至routes/user.py中实现
# 此处删除直接路由定义，避免与user_bp中的路由冲突

# 推荐设置为局域网中计算机的固定IP地址
FIXED_HOST = '192.168.170.178'  # 修改为您的局域网IP地址

def kill_process_using_port(port):
    try:
        # 在Windows上使用netstat命令查找占用端口的进程
        import os
        
        # 检查操作系统类型
        if os.name == 'nt':  # Windows系统
            # 使用netstat命令查找占用端口的进程
            result = subprocess.run(
                ['netstat', '-ano', f'|findstr :{port}'],
                shell=True,
                capture_output=True,
                text=True
            )
            
            # 解析输出，找到PID
            if result.stdout:
                # 提取最后一列作为PID
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            print(f"检测到占用端口 {port} 的进程，PID: {pid}")
                            
                            # 在Windows上终止进程
                            kill_result = subprocess.run(
                                ['taskkill', '/F', '/PID', pid],
                                capture_output=True,
                                text=True
                            )
                            if kill_result.returncode == 0:
                                print(f"成功: 已终止 PID 为 {pid} 的进程")
                                print(f"已终止进程PID: {pid}")
                                return True
                            else:
                                print(f"无法终止进程 PID {pid}: {kill_result.stderr}")
        else:  # Unix/Linux系统
            # 原始的lsof实现
            try:
                result = subprocess.run(
                    ['lsof', '-i', f':{port}'],
                    capture_output=True,
                    text=True
                )
                
                for line in result.stdout.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        print(f"检测到占用端口 {port} 的进程，PID: {pid}")
                        subprocess.run(['kill', '-9', pid], capture_output=True, text=True)
                        print(f"已终止进程 PID: {pid}")
                        return True
            except FileNotFoundError:
                print("警告: 未找到lsof命令，无法检查端口占用")
                
    except Exception as e:
        print(f"检查或关闭占用端口的进程时出错: {str(e)}")
    
    return False

if __name__ == '__main__':
    # 检查并关闭占用5001端口的进程
    print("检查是否有其他实例占用端口 5001...")
    kill_process_using_port(5001)
    
    # 在应用启动时创建数据库表
    with app.app_context():
        db.create_all()
        # 配置SQLite优化参数
        configure_sqlite_optimizations()
    
    # 使用固定IP地址启动服务器
    print(f"服务器启动在固定IP地址: http://{FIXED_HOST}:5001")
    app.run(debug=False, host=FIXED_HOST, port=5001)