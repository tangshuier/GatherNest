#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复管理员账户脚本
用于检查和重置超级管理员账户
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys

# 创建Flask应用实例
app = Flask(__name__)

# 配置数据库URI，使用绝对路径
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///f:\\资料整理网站\\instance\\database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 确保instance目录存在
os.makedirs(app.instance_path, exist_ok=True)

# 初始化数据库
db = SQLAlchemy(app)

# 简化的User模型，只包含必要的字段和方法
class User(db.Model):
    __tablename__ = 'user'  # 明确指定表名以确保正确映射
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    role_level = db.Column(db.Integer, default=4)
    role_detail = db.Column(db.String(20), nullable=True)
    active_session_id = db.Column(db.String(20), nullable=True)

    def set_password(self, password):
        """设置密码（使用werkzeug.security生成哈希）"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password, password)

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True)
    name = db.Column(db.String(50), nullable=False)

def fix_admin_account():
    """检查并修复超级管理员账户"""
    with app.app_context():
        print("开始检查管理员账户...")
        
        # 列出所有用户，查看当前状态
        all_users = User.query.all()
        print(f"当前数据库中有 {len(all_users)} 个用户账户")
        
        if all_users:
            print("用户列表:")
            for user in all_users:
                print(f"  - ID: {user.id}, 用户名: {user.username}, 角色: {user.role}, 级别: {user.role_level}")
        else:
            print("数据库中没有用户账户")
        
        # 查找超级管理员账户
        admin_username = 'admin'
        admin_user = User.query.filter_by(username=admin_username).first()
        
        if admin_user:
            print(f"找到管理员账户: {admin_username}")
            print(f"当前角色: {admin_user.role}, 级别: {admin_user.role_level}")
            
            # 检查管理员资料是否存在
            admin_profile = Admin.query.filter_by(user_id=admin_user.id).first()
            if not admin_profile:
                print("警告: 管理员账户存在，但缺少管理员资料")
                # 创建管理员资料
                admin_profile = Admin(user_id=admin_user.id, name='系统管理员')
                db.session.add(admin_profile)
                db.session.commit()
                print("已创建管理员资料")
            
            # 重置密码
            new_password = 'admin123'
            admin_user.set_password(new_password)
            admin_user.role = 'super_admin'
            admin_user.role_level = 0
            admin_user.role_detail = '超级管理员'
            admin_user.active_session_id = None  # 清除会话ID以允许重新登录
            db.session.commit()
            print(f"已重置管理员密码为: {new_password}")
            print(f"已确保用户角色为: super_admin, 级别为: 0")
        else:
            print(f"未找到管理员账户 {admin_username}，正在创建...")
            # 创建新的超级管理员用户
            admin_user = User(
                username=admin_username,
                role='super_admin',
                role_level=0,
                role_detail='超级管理员'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print(f"已创建管理员用户: {admin_username}")
            
            # 创建管理员资料
            admin_profile = Admin(
                user_id=admin_user.id,
                name='系统管理员'
            )
            db.session.add(admin_profile)
            db.session.commit()
            print("已创建管理员资料")
        
        print("\n修复完成！请使用以下信息登录:")
        print(f"用户名: {admin_username}")
        print(f"密码: admin123")
        print("\n重要提示: 请在首次登录后立即修改密码")

if __name__ == '__main__':
    try:
        fix_admin_account()
        print("\n操作成功完成")
    except Exception as e:
        print(f"\n操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)