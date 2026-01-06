from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

# 创建Flask应用
app = Flask(__name__)

# 配置数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, '../instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 定义必要的模型类
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 定义关联表
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id', ondelete='CASCADE'), primary_key=True)
)

# 为Role模型添加permissions关系
Role.permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                              backref=db.backref('roles', lazy=True))

def update_permissions():
    """更新数据库中的权限"""
    with app.app_context():
        print("开始更新权限...")
        
        # 要添加的新权限
        new_permissions = [
            {'name': '管理员访问', 'code': 'admin_access', 'description': '管理员访问权限'},
            {'name': '超级管理员访问', 'code': 'super_admin_access', 'description': '超级管理员访问权限'},
            {'name': '工程师访问', 'code': 'engineer_access', 'description': '工程师访问权限'},
            {'name': '修改所有用户', 'code': 'modify_all_users', 'description': '修改所有用户权限'}
        ]
        
        # 添加新权限
        added_count = 0
        for perm_data in new_permissions:
            existing_perm = Permission.query.filter_by(code=perm_data['code']).first()
            if not existing_perm:
                perm = Permission(
                    name=perm_data['name'], 
                    code=perm_data['code'], 
                    description=perm_data['description']
                )
                db.session.add(perm)
                added_count += 1
                print(f"添加权限: {perm_data['name']} ({perm_data['code']})")
            else:
                print(f"权限已存在: {perm_data['name']} ({perm_data['code']})")
        
        # 提交权限添加
        if added_count > 0:
            db.session.commit()
            print(f"成功添加 {added_count} 个新权限")
        
        # 为超级管理员角色分配所有权限
        print("\n更新超级管理员权限...")
        super_admin_role = Role.query.filter_by(name='超级管理员').first()
        if super_admin_role:
            all_permissions = Permission.query.all()
            super_admin_role.permissions = all_permissions
            db.session.commit()
            print(f"已为超级管理员角色分配所有权限，共 {len(all_permissions)} 个")
        else:
            print("未找到超级管理员角色")
        
        # 为管理员角色分配管理员访问权限
        print("\n更新管理员角色权限...")
        admin_role = Role.query.filter_by(name='高级管理员').first()
        if admin_role:
            admin_permission = Permission.query.filter_by(code='admin_access').first()
            engineer_permission = Permission.query.filter_by(code='engineer_access').first()
            
            # 添加基本的管理员权限
            if admin_permission and admin_permission not in admin_role.permissions:
                admin_role.permissions.append(admin_permission)
                print("已为高级管理员角色添加管理员访问权限")
            
            if engineer_permission and engineer_permission not in admin_role.permissions:
                admin_role.permissions.append(engineer_permission)
                print("已为高级管理员角色添加工程师访问权限")
            
            db.session.commit()
        else:
            print("未找到高级管理员角色")
        
        # 为工程师角色分配工程师访问权限
        print("\n更新工程师权限...")
        # 尝试查找工程师相关角色
        for role_name in ['普通员工', 'engineer']:
            engineer_role = Role.query.filter_by(name=role_name).first()
            if engineer_role:
                engineer_permission = Permission.query.filter_by(code='engineer_access').first()
                if engineer_permission and engineer_permission not in engineer_role.permissions:
                    engineer_role.permissions.append(engineer_permission)
                    print(f"已为{role_name}角色添加工程师访问权限")
                    db.session.commit()
                break
        else:
            print("未找到工程师相关角色")
        
        print("\n权限更新完成！")
        
        # 显示当前所有权限
        print("\n当前系统权限列表:")
        all_permissions = Permission.query.all()
        for i, perm in enumerate(all_permissions, 1):
            print(f"{i}. {perm.name} ({perm.code})")
        print(f"\n总权限数: {len(all_permissions)}")

if __name__ == '__main__':
    update_permissions()