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

def diagnose():
    """诊断数据库中的角色和权限情况"""
    with app.app_context():
        print("======== 权限系统诊断报告 ========")
        
        # 检查用户表
        print("\n1. 用户信息:")
        users = User.query.all()
        if users:
            print(f"   找到 {len(users)} 个用户:")
            for i, user in enumerate(users, 1):
                print(f"   {i}. 用户名: {user.username}, 角色: {user.role}, 权限级别: {user.role_level}, 角色详情: {user.role_detail}")
        else:
            print("   未找到任何用户")
        
        # 检查角色表
        print("\n2. 角色信息:")
        roles = Role.query.all()
        if roles:
            print(f"   找到 {len(roles)} 个角色:")
            for i, role in enumerate(roles, 1):
                perm_count = len(role.permissions)
                print(f"   {i}. 角色名称: {role.name}, 角色级别: {role.level}, 权限数: {perm_count}")
                if perm_count > 0:
                    perm_codes = [p.code for p in role.permissions]
                    print(f"      权限列表: {', '.join(perm_codes)}")
        else:
            print("   未找到任何角色")
        
        # 检查权限表
        print("\n3. 权限信息:")
        permissions = Permission.query.all()
        if permissions:
            print(f"   找到 {len(permissions)} 个权限:")
            for i, perm in enumerate(permissions, 1):
                role_count = len(perm.roles)
                role_names = [r.name for r in perm.roles]
                print(f"   {i}. 权限名称: {perm.name}, 权限代码: {perm.code}, 拥有角色数: {role_count}")
                if role_count > 0:
                    print(f"      拥有角色: {', '.join(role_names)}")
        else:
            print("   未找到任何权限")
        
        # 检查用户和角色的对应关系
        print("\n4. 用户角色映射分析:")
        # 统计用户表中使用的所有角色值
        user_roles = db.session.query(User.role).distinct().all()
        user_roles = [r[0] for r in user_roles]
        
        print(f"   用户表中使用的角色值: {', '.join(user_roles) if user_roles else '无'}")
        
        # 检查哪些用户角色在角色表中不存在
        if roles:
            db_role_names = [r.name for r in roles]
            missing_roles = [role for role in user_roles if role not in db_role_names]
            if missing_roles:
                print(f"   警告: 以下用户角色在角色表中不存在: {', '.join(missing_roles)}")
            else:
                print("   所有用户角色都在角色表中有对应记录")
        
        # 检查权限关联表
        print("\n5. 权限关联检查:")
        # 尝试直接查询role_permissions表
        try:
            from sqlalchemy import text
            result = db.session.execute(text("SELECT COUNT(*) FROM role_permissions")).fetchone()
            if result:
                print(f"   角色权限关联记录数: {result[0]}")
            else:
                print("   未找到角色权限关联记录")
        except Exception as e:
            print(f"   查询角色权限关联记录时出错: {str(e)}")
        
        print("\n======== 诊断完成 ========")

if __name__ == '__main__':
    diagnose()