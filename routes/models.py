from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# 优化后的User模型 - 添加索引和RBAC关联
class User(UserMixin, db.Model):
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

    def check_password(self, password):
        return check_password_hash(self.password, password)

# 项目和标签的多对多关联表 - 添加级联删除
project_tags = db.Table('project_tags',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

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

# 优化后的Project模型 - 添加索引、外键约束和复合索引
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
    status = db.Column(db.String(20), default='not_started', index=True)  # 保留以兼容旧代码
    progress = db.Column(db.String(50), default='无方案', index=True)  # 添加索引，作为主要状态字段
    created_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 添加索引
    assigned_time = db.Column(db.DateTime)
    completed_time = db.Column(db.DateTime)
    reviewed_time = db.Column(db.DateTime)
    materials_path = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))  # 添加创建者字段
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))  # 添加更新者字段
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 添加更新时间
    
    # 关系定义
    assigned_engineer = db.relationship('Engineer', backref='assigned_projects')
    documents = db.relationship('Document', backref='project', lazy=True, cascade='all, delete-orphan')
    images = db.relationship('ProjectImage', backref='project', lazy=True, cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=project_tags, lazy='subquery',
                          backref=db.backref('projects', lazy=True))
    created_user = db.relationship('User', foreign_keys=[created_by], backref='created_projects')
    updated_user = db.relationship('User', foreign_keys=[updated_by], backref='updated_projects')
    # 添加复合索引
    __table_args__ = (
        db.Index('idx_project_type_status', 'project_type', 'status'),
    )

# 优化后的Engineer模型 - 添加索引和外键约束
class Engineer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)  # 添加索引和级联删除
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='engineer_profile', uselist=False)

# 优化后的Admin模型 - 添加索引和外键约束
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)  # 添加索引和级联删除
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='admin_profile', uselist=False)

# 优化后的Document模型 - 添加索引和外键约束
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)  # 添加索引和级联删除
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), default='document', index=True)  # 添加索引
    version = db.Column(db.Integer, default=1)
    is_latest = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 添加索引
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))  # 添加上传者字段
    title = db.Column(db.String(255))  # 添加文档标题
    filetype = db.Column(db.String(50))  # 添加文件类型字段
    is_package = db.Column(db.Boolean, default=False)  # 添加是否为数据包标志
    
    # 关系定义
    uploader = db.relationship('User', backref='uploaded_documents')

# 优化后的ProjectImage模型 - 添加外键约束
class ProjectImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)  # 添加级联删除
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    order_index = db.Column(db.Integer, default=0)

# 优化后的CustomerService模型 - 添加索引和外键约束
class CustomerService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)  # 添加索引和级联删除
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='customer_service_profile', uselist=False)

# 优化后的Trainee模型 - 添加索引和外键约束
class Trainee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)  # 添加索引和级联删除
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='trainee_profile', uselist=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    evaluation_status = db.Column(db.String(20), default='pending', index=True)  # 添加索引

# 优化后的TrainingMaterial模型 - 添加索引
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

# 优化后的Tag模型 - 添加索引
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 添加索引
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))  # 添加创建者用户ID
    
    # 关系定义
    creator = db.relationship('User', backref='created_tags')

# 优化后的TagRequest模型 - 添加索引和外键约束
class TagRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(50), nullable=False)
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id', ondelete='CASCADE'), nullable=False, index=True)  # 添加索引和级联删除
    status = db.Column(db.String(20), default='pending', index=True)  # 添加索引
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 添加索引
    
    # 关系
    engineer = db.relationship('Engineer', backref='tag_requests')

# 新增RBAC权限模型 - Permission
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 新增RBAC角色模型 - Role
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 关系
    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                                backref=db.backref('roles', lazy=True))

# 新增文档版本历史表
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

# 新增项目历史记录表
class ProjectHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), index=True)
    changed_by = db.Column(db.String(50))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    field_name = db.Column(db.String(50))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    notes = db.Column(db.Text)

# 新增操作日志表
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

# 新增进度修改申请表
class ProgressChangeRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    engineer_id = db.Column(db.Integer, db.ForeignKey('engineer.id', ondelete='CASCADE'), nullable=False, index=True)
    requested_progress = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    processed_at = db.Column(db.DateTime)
    
    # 关系定义
    project = db.relationship('Project', backref='progress_requests')
    engineer = db.relationship('Engineer', backref='progress_requests')
    processor = db.relationship('User', foreign_keys=[processed_by], backref='processed_progress_requests')