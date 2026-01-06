from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# 创建Flask应用
app = Flask(__name__)

# 配置数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, '../instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 定义必要的模型类
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    role_level = db.Column(db.Integer, default=4, index=True)
    role_detail = db.Column(db.String(20), nullable=True, index=True)

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False, index=True)

# 定义关联表
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE'), primary_key=True)
)

# 为Role模型添加permissions关系
Role.permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                              backref=db.backref('roles', lazy=True))

def fix_permissions():
    """修复权限系统：初始化角色表并正确分配权限"""
    with app.app_context():
        print("======== 开始修复权限系统 ========")
        
        # 1. 确保所有必要的权限都存在
        required_permissions = [
            {'name': '用户管理', 'code': 'user_management', 'description': '管理用户信息和权限'},
            {'name': '项目管理', 'code': 'project_management', 'description': '管理项目信息'},
            {'name': '文档管理', 'code': 'document_management', 'description': '管理文档信息'},
            {'name': '系统配置', 'code': 'system_configuration', 'description': '修改系统配置'},
            {'name': '工程师管理', 'code': 'engineer_management', 'description': '管理工程师信息'},
            {'name': '管理员访问', 'code': 'admin_access', 'description': '访问管理员界面'},
            {'name': '超级管理员访问', 'code': 'super_admin_access', 'description': '超级管理员专属权限'},
            {'name': '工程师访问', 'code': 'engineer_access', 'description': '工程师专属权限'},
            {'name': '修改所有用户', 'code': 'modify_all_users', 'description': '修改所有用户的权限'},
        ]
        
        print("\n1. 确保必要权限存在...")
        permissions_created = 0
        for perm_data in required_permissions:
            perm = Permission.query.filter_by(code=perm_data['code']).first()
            if not perm:
                perm = Permission(
                    name=perm_data['name'],
                    code=perm_data['code'],
                    description=perm_data['description']
                )
                db.session.add(perm)
                permissions_created += 1
                print(f"   添加权限: {perm_data['name']} ({perm_data['code']})")
            else:
                print(f"   权限已存在: {perm_data['name']} ({perm_data['code']})")
        
        if permissions_created > 0:
            db.session.commit()
            print(f"   成功添加 {permissions_created} 个新权限")
        
        # 2. 创建必要的角色
        roles_to_create = [
            {'name': 'super_admin', 'level': 0, 'description': '超级管理员'},
            {'name': 'admin', 'level': 1, 'description': '高级管理员'},
            {'name': 'engineer', 'level': 2, 'description': '工程师'},
            {'name': 'user', 'level': 3, 'description': '普通用户'},
            {'name': 'trainee', 'level': 4, 'description': '实习员工'},
        ]
        
        print("\n2. 创建角色...")
        roles_created = 0
        role_objects = {}
        
        for role_data in roles_to_create:
            role = Role.query.filter_by(name=role_data['name']).first()
            if not role:
                role = Role(name=role_data['name'], level=role_data['level'])
                db.session.add(role)
                roles_created += 1
                print(f"   创建角色: {role_data['name']} (级别: {role_data['level']})")
            else:
                print(f"   角色已存在: {role_data['name']} (级别: {role.level})")
                # 确保级别正确
                if role.level != role_data['level']:
                    role.level = role_data['level']
                    print(f"   更新角色级别: {role_data['name']} 设为 {role_data['level']}")
            role_objects[role_data['name']] = role
        
        if roles_created > 0 or any(role.level != role_data['level'] for role_data, role in zip(roles_to_create, role_objects.values())):
            db.session.commit()
            print(f"   成功创建/更新 {roles_created} 个角色")
        
        # 3. 为每个角色分配权限
        print("\n3. 分配权限给角色...")
        
        # 定义角色权限映射
        role_permissions_map = {
            'super_admin': ['admin_access', 'super_admin_access', 'user_management', 'project_management', 
                           'document_management', 'system_configuration', 'engineer_management', 'modify_all_users'],
            'admin': ['admin_access', 'user_management', 'project_management', 'document_management', 
                     'engineer_management'],
            'engineer': ['engineer_access', 'project_management', 'document_management'],
            'user': ['document_management'],
            'trainee': []
        }
        
        permissions_added = 0
        for role_name, perm_codes in role_permissions_map.items():
            if role_name in role_objects:
                role = role_objects[role_name]
                # 获取当前角色已有的权限代码
                current_perm_codes = {p.code for p in role.permissions}
                
                # 找出需要添加的权限
                for perm_code in perm_codes:
                    if perm_code not in current_perm_codes:
                        perm = Permission.query.filter_by(code=perm_code).first()
                        if perm:
                            role.permissions.append(perm)
                            permissions_added += 1
                            print(f"   为角色 {role_name} 添加权限: {perm_code}")
        
        if permissions_added > 0:
            db.session.commit()
            print(f"   成功为角色添加 {permissions_added} 个权限")
        
        # 4. 验证修复结果
        print("\n4. 验证修复结果:")
        
        # 检查角色
        roles = Role.query.all()
        print(f"   角色数量: {len(roles)}")
        
        # 检查每个角色的权限
        for role in roles:
            perm_codes = [p.code for p in role.permissions]
            print(f"   角色 {role.name} (级别: {role.level}) 拥有 {len(perm_codes)} 个权限: {', '.join(perm_codes) if perm_codes else '无'}")
        
        # 检查用户
        users = User.query.all()
        print(f"\n   用户数量: {len(users)}")
        for user in users:
            print(f"   用户 {user.username}: 角色={user.role}, 级别={user.role_level}")
            # 验证用户角色是否在角色表中存在
            role_exists = any(r.name == user.role for r in roles)
            print(f"     用户角色 '{user.role}' 在角色表中 {'存在' if role_exists else '不存在'}")
        
        print("\n======== 权限系统修复完成 ========")

if __name__ == '__main__':
    fix_permissions()