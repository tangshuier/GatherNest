#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库初始化脚本
使用绝对路径确保数据库正确创建在instance目录
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
from datetime import datetime
import time

# 获取项目根目录的绝对路径
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(PROJECT_ROOT, 'instance')
DB_PATH = os.path.join(INSTANCE_DIR, 'database.db')
# 使用临时文件名
TEMP_DB_PATH = os.path.join(INSTANCE_DIR, 'database_new.db')

# 创建Flask应用实例
app = Flask(__name__)
# 使用临时文件路径
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{TEMP_DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 初始化数据库
db = SQLAlchemy(app)

print(f"临时数据库路径配置: {app.config['SQLALCHEMY_DATABASE_URI']}")

# 数据模型定义（简化版本，只包含必要的表）
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    role_level = db.Column(db.Integer, default=4, index=True)
    role_detail = db.Column(db.String(20), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    active_session_id = db.Column(db.String(20), nullable=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref='admin_profile', uselist=False)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 创建数据库和初始化数据
def init_database():
    with app.app_context():
        print(f"当前工作目录: {os.getcwd()}")
        print(f"项目根目录: {PROJECT_ROOT}")
        print(f"实例目录: {INSTANCE_DIR}")
        print(f"临时数据库文件: {TEMP_DB_PATH}")
        print(f"目标数据库文件: {DB_PATH}")
        
        # 确保instance目录存在
        os.makedirs(INSTANCE_DIR, exist_ok=True)
        print(f"确保实例目录存在: {INSTANCE_DIR}")
        
        # 删除旧的临时文件（如果存在）
        if os.path.exists(TEMP_DB_PATH):
            try:
                print(f"删除旧的临时数据库文件: {TEMP_DB_PATH}")
                os.remove(TEMP_DB_PATH)
            except Exception as e:
                print(f"删除临时文件失败: {e}")
        
        # 创建所有表
        print("创建数据库表...")
        db.create_all()
        print("数据库表创建完成")
        
        # 配置SQLite优化参数
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text('PRAGMA foreign_keys = ON'))
            conn.execute(text('PRAGMA journal_mode = WAL'))
            print("SQLite优化参数配置完成")
        
        # 创建超级管理员
        print("创建超级管理员账户...")
        create_super_admin()
        
        print("临时数据库初始化完成！")
        print(f"临时数据库文件已创建: {TEMP_DB_PATH}")
        print(f"文件大小: {os.path.getsize(TEMP_DB_PATH) / 1024:.2f} KB")
        
        # 尝试重命名文件
        try:
            # 先尝试删除目标文件（如果存在）
            if os.path.exists(DB_PATH):
                print(f"尝试删除目标数据库文件: {DB_PATH}")
                # 等待一会儿再尝试删除
                time.sleep(2)
                os.remove(DB_PATH)
                print("目标文件删除成功")
            
            # 重命名临时文件为目标文件
            print(f"尝试重命名临时文件到目标位置...")
            os.rename(TEMP_DB_PATH, DB_PATH)
            print(f"数据库文件重命名成功: {DB_PATH}")
            print(f"最终数据库文件大小: {os.path.getsize(DB_PATH) / 1024:.2f} KB")
        except Exception as e:
            print(f"重命名数据库文件失败: {e}")
            print(f"临时数据库已创建在: {TEMP_DB_PATH}")
            print("请手动将临时文件重命名为database.db")

def create_super_admin():
    # 创建超级管理员用户
    admin_username = 'admin'
    admin_password = 'admin123'
    
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
    print(f"创建用户成功: {admin_username}")
    
    # 创建管理员资料
    admin_profile = Admin(
        user_id=admin_user.id,
        name='系统管理员'
    )
    db.session.add(admin_profile)
    db.session.commit()
    print(f"创建管理员资料成功")
    
    print(f"超级管理员账户已创建: 用户名={admin_username}, 密码={admin_password}")
    print("注意：请在首次登录后修改密码！")

if __name__ == '__main__':
    init_database()