from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
from datetime import datetime

# 创建Flask应用实例
app = Flask(__name__)
# 配置数据库URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 初始化数据库
db = SQLAlchemy(app)

# 优化后的数据模型定义

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 添加索引
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # 添加索引
    role_level = db.Column(db.Integer, default=4, index=True)  # 添加索引
    role_detail = db.Column(db.String(20), nullable=True, index=True)  # 添加索引
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 添加索引
    active_session_id = db.Column(db.String(20), nullable=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

# 项目和标签的多对多关联表
project_tags = db.Table('project_tags',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)  # 添加索引
    project_type = db.Column(db.String(20), default='custom', index=True)  # 添加索引
    price = db.Column(db.Float)
    cost = db.Column(db.Float)
    unit_price = db.Column(db.Float)
    group_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    assigned_engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id', ondelete='SET NULL'), index=True)  # 添加索引和级联删除
    status = db.Column(db.String(20), default='not_started', index=True)  # 添加索引
    progress = db.Column(db.String(50), default='无方案')
    created_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 添加索引
    assigned_time = db.Column(db.DateTime)
    completed_time = db.Column(db.DateTime)
    reviewed_time = db.Column(db.DateTime)
    materials_path = db.Column(db.String(255))
    
    # 关系定义
    assigned_engineer = db.relationship('Engineer', backref='assigned_projects')
    documents = db.relationship('Document', backref='project', lazy=True, cascade='all, delete-orphan')
    images = db.relationship('ProjectImage', backref='project', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=project_tags, lazy='subquery',
                          backref=db.backref('projects', lazy=True))
    # 添加复合索引
    __table_args__ = (
        db.Index('idx_project_type_status', 'project_type', 'status'),
    )

class Engineer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)  # 添加索引和级联删除
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='engineer_profile', uselist=False)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)  # 添加索引和级联删除
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='admin_profile', uselist=False)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)  # 添加索引和级联删除
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), default='document', index=True)  # 添加索引
    version = db.Column(db.Integer, default=1)
    is_latest = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 添加索引

class ProjectImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)  # 添加级联删除
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    order_index = db.Column(db.Integer, default=0)

class CustomerService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)  # 添加索引和级联删除
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='customer_service_profile', uselist=False)

class Trainee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)  # 添加索引和级联删除
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='trainee_profile', uselist=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    evaluation_status = db.Column(db.String(20), default='pending', index=True)  # 添加索引

class TrainingMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)  # 添加索引
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(20), nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 添加索引
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))

class TagRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(50), nullable=False)
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id', ondelete='CASCADE'), nullable=False, index=True)  # 添加索引和级联删除
    status = db.Column(db.String(20), default='pending', index=True)  # 添加索引
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 添加索引
    
    # 关系
    engineer = db.relationship('Engineer', backref='tag_requests')

# 新增优化的模型 - 权限管理相关
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 用户-权限关联表
user_permissions = db.Table('user_permissions',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE'), primary_key=True)
)

# 角色-权限关联表
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE'), primary_key=True)
)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 关系
    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                                backref=db.backref('roles', lazy=True))

# 文档版本历史表
class DocumentVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id', ondelete='CASCADE'), index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), index=True)
    version = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.String(50))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

# 项目历史记录表
class ProjectHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), index=True)
    changed_by = db.Column(db.String(50))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    field_name = db.Column(db.String(50))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    notes = db.Column(db.Text)

# 操作日志表
class OperationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, index=True)
    operation = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(100), index=True)
    ip = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    params = db.Column(db.Text)
    result = db.Column(db.Text)
    success = db.Column(db.Boolean, default=True)
    create_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# 创建数据库和初始化数据
def init_database():
    with app.app_context():
        # 确保instance目录存在
        os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
        
        # 删除旧数据库文件（如果存在）
        db_path = os.path.join(app.root_path, 'instance', 'database.db')
        if os.path.exists(db_path):
            print(f"删除旧数据库文件: {db_path}")
            os.remove(db_path)
        
        # 创建所有表
        print("创建数据库表...")
        db.create_all()
        
        # 配置SQLite优化参数
        from sqlalchemy import text
        with db.engine.connect() as conn:
            # 启用外键约束
            conn.execute(text('PRAGMA foreign_keys = ON'))
            # 优化SQLite性能
            conn.execute(text('PRAGMA journal_mode = WAL'))
            conn.execute(text('PRAGMA synchronous = NORMAL'))
            conn.execute(text('PRAGMA temp_store = MEMORY'))
            conn.execute(text('PRAGMA cache_size = -8000'))  # 约64MB缓存
        
        print("初始化基础数据...")
        # 创建角色
        create_roles()
        
        # 创建权限
        create_permissions()
        
        # 创建超级管理员账户
        create_super_admin()
        
        print("数据库初始化完成！")

def create_roles():
    # 创建系统角色
    roles = [
        {'name': '超级管理员', 'level': 0},
        {'name': '高级管理员', 'level': 1},
        {'name': '中级管理员', 'level': 2},
        {'name': '普通管理员', 'level': 3},
        {'name': '普通员工', 'level': 4},
        {'name': '试岗员工', 'level': 5}
    ]
    
    for role_data in roles:
        existing_role = Role.query.filter_by(name=role_data['name']).first()
        if not existing_role:
            role = Role(name=role_data['name'], level=role_data['level'])
            db.session.add(role)
    
    db.session.commit()

def create_permissions():
    # 创建系统权限
    permissions = [
        {'name': '用户管理', 'code': 'user_manage'},
        {'name': '项目管理', 'code': 'project_manage'},
        {'name': '文档管理', 'code': 'document_manage'},
        {'name': '标签管理', 'code': 'tag_manage'},
        {'name': '培训资料管理', 'code': 'training_manage'},
        {'name': '权限管理', 'code': 'permission_manage'},
        {'name': '角色管理', 'code': 'role_manage'},
        {'name': '日志查看', 'code': 'log_view'},
        {'name': '管理员访问', 'code': 'admin_access'},
        {'name': '超级管理员访问', 'code': 'super_admin_access'},
        {'name': '工程师访问', 'code': 'engineer_access'},
        {'name': '修改所有用户', 'code': 'modify_all_users'}
    ]
    
    for perm_data in permissions:
        existing_perm = Permission.query.filter_by(code=perm_data['code']).first()
        if not existing_perm:
            perm = Permission(name=perm_data['name'], code=perm_data['code'], description=perm_data['name'])
            db.session.add(perm)
    
    db.session.commit()
    
    # 为超级管理员角色分配所有权限
    super_admin_role = Role.query.filter_by(name='超级管理员').first()
    if super_admin_role:
        all_permissions = Permission.query.all()
        super_admin_role.permissions = all_permissions
        db.session.commit()

def create_super_admin():
    # 创建超级管理员用户
    admin_username = 'admin'
    admin_password = 'admin123'  # 生产环境请修改为强密码
    
    # 检查是否已存在
    existing_user = User.query.filter_by(username=admin_username).first()
    if not existing_user:
        # 创建用户
        admin_user = User(
            username=admin_username,
            role='super_admin',
            role_level=0,
            role_detail='超级管理员'
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()
        
        # 创建管理员资料
        admin_profile = Admin(
            user_id=admin_user.id,
            name='系统管理员'
        )
        db.session.add(admin_profile)
        db.session.commit()
        
        print(f"超级管理员账户已创建: 用户名={admin_username}, 密码={admin_password}")
        print("注意：请在首次登录后修改密码！")

if __name__ == '__main__':
    init_database()