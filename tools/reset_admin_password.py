import os
import sys
from flask import Flask
from routes.models import db, User

# 创建Flask应用实例
app = Flask(__name__)

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 重置管理员密码的函数
def reset_admin_password():
    with app.app_context():
        # 查找超级管理员账号
        admin_user = User.query.filter_by(role='super_admin').first()
        
        if admin_user:
            print(f"找到超级管理员账号: {admin_user.username}")
            
            # 设置新密码
            new_password = 'admin123'
            admin_user.set_password(new_password)
            
            # 清除会话ID，强制重新登录
            admin_user.active_session_id = None
            
            # 提交更改
            db.session.commit()
            
            print(f"超级管理员密码已重置为: {new_password}")
            print("请使用此密码登录系统，并在登录后立即修改密码")
        else:
            # 尝试查找role_level为0的用户（也可能是超级管理员）
            admin_user = User.query.filter_by(role_level=0).first()
            
            if admin_user:
                print(f"找到疑似超级管理员账号: {admin_user.username} (role_level=0)")
                
                # 设置新密码
                new_password = 'admin123'
                admin_user.set_password(new_password)
                
                # 清除会话ID
                admin_user.active_session_id = None
                
                # 提交更改
                db.session.commit()
                
                print(f"账号密码已重置为: {new_password}")
                print("请使用此密码登录系统，并在登录后立即修改密码")
            else:
                print("未找到超级管理员账号!")
                print("正在检查数据库中的所有用户...")
                
                # 获取所有用户
                all_users = User.query.all()
                
                if all_users:
                    print(f"找到 {len(all_users)} 个用户账号:")
                    for user in all_users:
                        print(f"- 用户名: {user.username}, 角色: {user.role}, 角色级别: {user.role_level}")
                    
                    print("\n您可以修改此脚本以重置特定用户的密码")
                else:
                    print("数据库中没有找到任何用户!")
                    print("请运行数据库初始化脚本创建管理员账号")

# 检查数据库文件是否存在
def check_database():
    db_path = os.path.join('instance', 'database.db')
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        print("请先运行数据库初始化脚本")
        return False
    return True

if __name__ == '__main__':
    print("====== 超级管理员密码重置工具 ======\n")
    
    if check_database():
        reset_admin_password()
    
    print("\n操作完成！")