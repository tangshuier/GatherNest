from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, logout_user
from routes.models import User, Admin, Engineer, Project, CustomerService, Trainee, TrainingMaterial, db
from sqlalchemy import text
from routes.decorators import admin_required, super_admin_required
from routes.forms import EditSuperAdminForm, EditUserForm  
from datetime import datetime, timedelta

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/')
@login_required
def user_panel():
    # 用户面板逻辑
    if current_user.role == 'super_admin':
        return redirect(url_for('admin.admin_panel'))
    
    # 根据用户角色重定向到相应的面板
    if hasattr(current_user, 'role_level'):
        if current_user.role_level == 3:
            if getattr(current_user, 'role_detail', '') == 'customer_service':
                return redirect(url_for('user.customer_service_panel'))
            elif getattr(current_user, 'role_detail', '') == 'engineer':
                return redirect(url_for('user.engineer_panel'))
        elif current_user.role_level == 4:
            return redirect(url_for('user.trainee_panel'))
    
    # 原始工程师面板逻辑作为后备
    engineer = Engineer.query.filter_by(user_id=current_user.id).first()
    assigned_products = Project.query.filter_by(assigned_engineer_id=engineer.id).filter(Project.status != 'completed').all() if engineer else []
    completed_products = Project.query.filter_by(assigned_engineer_id=engineer.id, status='completed').all() if engineer else []
    
    return render_template('user.html', 
                          engineer=engineer, 
                          assigned_products=assigned_products, 
                          completed_products=completed_products)

@user_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id=None):
    # 如果没有提供user_id，默认使用当前登录用户的id
    if user_id is None:
        user_id = current_user.id
    
    # 检查是否有权限编辑该用户
    if user_id != current_user.id:
        # 确保用户只能编辑比自己权限低的用户
        target_user = User.query.get(user_id)
        if not target_user:
            flash('用户不存在')
            return redirect(url_for('user.profile', user_id=user_id))
        
        # 检查权限: 超级管理员可以编辑所有人，管理员只能编辑工程师
        if not (current_user.role == 'super_admin'):
            flash('您没有权限编辑此用户')
            return redirect(url_for('user.profile', user_id=user_id))
    
    user = User.query.get(user_id)
    if not user:
        flash('用户不存在')
        return redirect(url_for('user.profile', user_id=user_id))

    # 获取用户详细信息
    if user.role == 'admin':
        user_info = Admin.query.filter_by(user_id=user_id).first()
    else:
        user_info = Engineer.query.filter_by(user_id=user_id).first()

    form = EditUserForm(obj=user)
    if user_info:
        form.new_name.data = user_info.name

    # 不依赖表单验证，直接从request.form获取数据
    if request.method == 'POST':
        # 打印所有POST数据
        print(f"所有POST数据: {dict(request.form)}")
        
        # 直接从request.form获取数据
        new_name = request.form.get('new_name', '').strip()
        new_password = request.form.get('new_password', '').strip()
        
        print(f"从request.form直接获取 - new_name: '{new_name}'")
        print(f"从request.form直接获取 - new_password: '{new_password}'")

        try:
            # 使用直接的SQLAlchemy方法确保数据更新
            if user_info:
                # 直接更新数据库记录
                print(f"直接更新用户ID {user_id} 的姓名: 从 '{user_info.name}' 到 '{new_name}'")
                # 方法1: 直接设置属性并显式添加到会话
                user_info.name = new_name
                db.session.merge(user_info)  # 使用merge确保对象被正确处理
                
                # 方法2: 执行原生SQL更新作为备选
                if user.role == 'admin':
                    db.session.execute(
                        text("UPDATE admin SET name = :name WHERE user_id = :user_id"),
                        {"name": new_name, "user_id": user_id}
                    )
                else:
                    db.session.execute(
                        text("UPDATE engineer SET name = :name WHERE user_id = :user_id"),
                        {"name": new_name, "user_id": user_id}
                    )

            # 更新密码（如果填写）
            password_updated = False
            if new_password:
                print(f"更新用户ID {user_id} 的密码")
                user.set_password(new_password)
                db.session.merge(user)
                
                # 同时执行原生SQL更新密码
                db.session.execute(
                    text("UPDATE user SET password_hash = :password_hash WHERE id = :user_id"),
                    {"password_hash": user.password_hash, "user_id": user_id}
                )
                flash('密码更新成功')
                password_updated = True

            # 强制提交并刷新会话
            print(f"强制提交数据库变更")
            db.session.commit()
            print(f"数据库提交成功")
            
            # 强制重新加载数据以确保缓存被清除
            db.session.expire_all()
            
            # 重新查询验证更新
            if user.role == 'admin':
                updated_user_info = Admin.query.filter_by(user_id=user_id).first()
            else:
                updated_user_info = Engineer.query.filter_by(user_id=user_id).first()
            
            print(f"更新后重新查询: 用户姓名为 '{updated_user_info.name}'")
            flash('用户信息更新成功')
            
            # 根据用户角色决定跳转目标
            if current_user.role == 'super_admin':
                # 管理员修改后跳转到用户管理页面
                target_url = url_for('admin.admin_users')
            else:
                # 用户自己修改后跳转到用户主页
                target_url = url_for('user.user_panel')
            
            # 如果密码被修改且是当前用户，强制退出登录
            if password_updated and user_id == current_user.id:
                logout_user()
                flash('密码已修改，请重新登录')
                return redirect(url_for('auth.login'))
            
            return redirect(target_url)
        except Exception as e:
            print(f"更新异常: {str(e)}")
            db.session.rollback()
            flash(f'更新失败: {str(e)}')
            return redirect(url_for('user.edit_user', user_id=user_id))

    # 使用profile.html模板作为修改用户信息的界面
    return render_template('profile.html', form=form, user_info=user_info, user_id=user_id, user=user)
    
@user_bp.route('/edit_super_admin', methods=['GET', 'POST'])
@login_required
@super_admin_required
def edit_super_admin():
    user = User.query.get(current_user.id)
    admin_info = Admin.query.filter_by(user_id=current_user.id).first()
    
    if not user or not admin_info:
        flash('管理员信息不存在')
        return redirect('/admin')
    
    form = EditSuperAdminForm(obj=user)
    form.new_name.data = admin_info.name
    
    if form.validate_on_submit():
        # 更新用户名
        if form.new_username.data != user.username:
            existing_user = User.query.filter_by(username=form.new_username.data).first()
            if existing_user:
                flash('用户名已存在')
                return redirect('/edit_super_admin')
            user.username = form.new_username.data
        
        # 更新姓名
        admin_info.name = form.new_name.data
        
        # 更新密码（非空时）
        if form.new_password.data:
            user.set_password(form.new_password.data)
        
        try:
            db.session.commit()
            flash('超级管理员信息更新成功')
            return redirect('/admin')
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}')
            return redirect('/edit_super_admin')
    
    return render_template('edit_super_admin.html', form=form)

@user_bp.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    # 更新用户个人资料的逻辑
    user = current_user
    
    form = EditUserForm()
    
    # 预填充表单
    if user.role == 'admin':
        admin_info = Admin.query.filter_by(user_id=user.id).first()
        form.new_name.data = admin_info.name if admin_info else ''
    elif hasattr(user, 'role_detail'):
        if user.role_detail == 'customer_service':
            cs_info = CustomerService.query.filter_by(user_id=user.id).first()
            form.new_name.data = cs_info.name if cs_info else ''
        elif user.role_detail == 'trainee':
            trainee_info = Trainee.query.filter_by(user_id=user.id).first()
            form.new_name.data = trainee_info.name if trainee_info else ''
        else:
            engineer_info = Engineer.query.filter_by(user_id=user.id).first()
            form.new_name.data = engineer_info.name if engineer_info else ''
    else:
        engineer_info = Engineer.query.filter_by(user_id=user.id).first()
        form.new_name.data = engineer_info.name if engineer_info else ''
    
    if form.validate_on_submit():
        try:
            new_name = form.new_name.data.strip()
            entity_type = None
            table_name = None
            
            # 确定实体类型和表名
            if user.role == 'admin':
                entity_type = 'admin'
                table_name = 'admin'
            elif hasattr(user, 'role_detail'):
                if user.role_detail == 'customer_service':
                    entity_type = 'customer_service'
                    table_name = 'customer_service'
                elif user.role_detail == 'trainee':
                    entity_type = 'trainee'
                    table_name = 'trainee'
                else:
                    entity_type = 'engineer'
                    table_name = 'engineer'
            else:
                entity_type = 'engineer'
                table_name = 'engineer'
            
            print(f"update_profile - 准备更新用户ID {user.id} 的姓名为 '{new_name}'，实体类型: {entity_type}")
            
            # 方法1: 执行原生SQL更新（直接操作数据库）
            db.session.execute(
                text(f"UPDATE {table_name} SET name = :name WHERE user_id = :user_id"),
                {"name": new_name, "user_id": user.id}
            )
            print(f"update_profile - 已执行原生SQL更新 {table_name} 表")
            
            # 方法2: 同时使用ORM方式确保对象状态一致
            if entity_type == 'admin':
                admin_info = Admin.query.filter_by(user_id=user.id).first()
                if admin_info:
                    admin_info.name = new_name
                    db.session.merge(admin_info)
            elif entity_type == 'customer_service':
                cs_info = CustomerService.query.filter_by(user_id=user.id).first()
                if cs_info:
                    cs_info.name = new_name
                    db.session.merge(cs_info)
            elif entity_type == 'trainee':
                trainee_info = Trainee.query.filter_by(user_id=user.id).first()
                if trainee_info:
                    trainee_info.name = new_name
                    db.session.merge(trainee_info)
            else:  # engineer
                engineer_info = Engineer.query.filter_by(user_id=user.id).first()
                if engineer_info:
                    engineer_info.name = new_name
                    db.session.merge(engineer_info)
            
            # 如果提供了新密码，则更新密码
            if form.new_password.data:
                new_password = form.new_password.data.strip()
                # 检查新密码是否与当前密码相同
                if user.check_password(new_password):
                    flash('新密码不能与当前密码相同')
                    return redirect(url_for('user.update_profile'))
                
                print(f"update_profile - 更新用户ID {user.id} 的密码")
                user.set_password(new_password)
                db.session.merge(user)
                
                # 同时执行原生SQL更新密码
                db.session.execute(
                    text("UPDATE user SET password_hash = :password_hash WHERE id = :user_id"),
                    {"password_hash": user.password_hash, "user_id": user.id}
                )
                flash('密码更新成功，请重新登录')
                
                print(f"update_profile - 强制提交密码更新")
                db.session.commit()
                db.session.expire_all()  # 清除缓存
                print(f"update_profile - 密码更新提交成功")
                # 密码修改成功后退出登录
                logout_user()
                return redirect(url_for('auth.login'))
                
            # 更新用户信息
            if user_info:
                user_info.name = new_name
                user_info.updated_at = datetime.utcnow()
                user_info.updated_by = current_user.id
                
                # 同时更新user表的updated_by字段
                user.updated_by = current_user.id
            
            # 强制提交并清除缓存
            print(f"update_profile - 强制提交姓名更新")
            db.session.commit()
            db.session.expire_all()  # 清除所有缓存，确保下次查询获取最新数据
            print(f"update_profile - 姓名更新提交成功")
            
            # 重新查询数据库验证更新
            if entity_type == 'admin':
                updated_info = Admin.query.filter_by(user_id=user.id).first()
            elif entity_type == 'customer_service':
                updated_info = CustomerService.query.filter_by(user_id=user.id).first()
            elif entity_type == 'trainee':
                updated_info = Trainee.query.filter_by(user_id=user.id).first()
            else:
                updated_info = Engineer.query.filter_by(user_id=user.id).first()
            
            if updated_info:
                print(f"update_profile - 更新后验证: 用户姓名为 '{updated_info.name}'")
            
            flash('个人资料已更新')
        except Exception as e:
            print(f"update_profile - 更新异常: {str(e)}")
            db.session.rollback()
            flash(f'更新失败: {str(e)}')
        
        # 根据用户角色重定向到相应的面板
        if hasattr(user, 'role_level'):
            if user.role_level == 3:
                if user.role_detail == 'customer_service':
                    return redirect(url_for('user.customer_service_panel'))
                elif user.role_detail == 'engineer':
                    return redirect(url_for('user.engineer_panel'))
            elif user.role_level == 4:
                return redirect(url_for('user.trainee_panel'))
        return redirect(url_for('user.user_panel'))
    
    # 使用现有的profile.html模板代替缺失的update_profile.html模板
    # 获取用户详细信息
    if user.role == 'admin':
        user_info = Admin.query.filter_by(user_id=user.id).first()
    elif hasattr(user, 'role_detail'):
        if user.role_detail == 'customer_service':
            user_info = CustomerService.query.filter_by(user_id=user.id).first()
        elif user.role_detail == 'trainee':
            user_info = Trainee.query.filter_by(user_id=user.id).first()
        else:
            user_info = Engineer.query.filter_by(user_id=user.id).first()
    else:
        user_info = Engineer.query.filter_by(user_id=user.id).first()
    
    return render_template('profile.html', form=form, user=user, user_info=user_info)

@user_bp.route('/engineer_projects')
@login_required
def engineer_projects():
    # 工程师项目管理页面
    user = current_user
    
    # 更宽松的工程师角色检查，确保各种工程师角色都能访问
    if user.role == 'engineer' or \
       (hasattr(user, 'role_detail') and getattr(user, 'role_detail', '') == 'engineer') or \
       (hasattr(user, 'role_level') and user.role_level == 3):
        # 获取工程师相关数据
        engineer_info = Engineer.query.filter_by(user_id=user.id).first()
        if not engineer_info:
            # 如果没有找到工程师信息，尝试创建一个
            engineer_info = Engineer(user_id=user.id, name=user.username)
            db.session.add(engineer_info)
            db.session.commit()
        
        # 获取分配给该工程师的所有项目
        projects = Project.query.filter_by(assigned_engineer_id=engineer_info.id).all()
        
        return render_template('engineer_products.html', engineer=engineer_info, projects=projects)
    else:
        flash(f'您没有权限访问此页面，当前角色: {user.role}, 角色详情: {getattr(user, "role_detail", "无")}, 角色级别: {getattr(user, "role_level", "无")}')
        return redirect(url_for('user.user_panel'))

@user_bp.route('/completed_projects')
@login_required
def completed_projects():
    # 工程师已完成项目页面
    user = current_user
    
    # 更宽松的工程师角色检查，确保各种工程师角色都能访问
    if user.role == 'engineer' or \
       (hasattr(user, 'role_detail') and getattr(user, 'role_detail', '') == 'engineer') or \
       (hasattr(user, 'role_level') and user.role_level == 3):
        # 获取工程师相关数据
        engineer_info = Engineer.query.filter_by(user_id=user.id).first()
        if not engineer_info:
            # 如果没有找到工程师信息，尝试创建一个
            engineer_info = Engineer(user_id=user.id, name=user.username)
            db.session.add(engineer_info)
            db.session.commit()
        
        # 获取该工程师已完成的项目
        completed_products = Project.query.filter_by(assigned_engineer_id=engineer_info.id, status='completed').all()
        
        # 确保模板路径正确
        return render_template('user/completed.html', engineer=engineer_info, completed_products=completed_products)
    else:
        flash(f'您没有权限访问此页面，当前角色: {user.role}, 角色详情: {getattr(user, "role_detail", "无")}, 角色级别: {getattr(user, "role_level", "无")}')
        return redirect(url_for('user.user_panel'))

@user_bp.route('/engineer_panel')
@login_required
def engineer_panel():
    # 工程师面板
    user = current_user
    
    # 更宽松的工程师角色检查，确保各种工程师角色都能访问
    if not (user.role == 'engineer' or \
           (hasattr(user, 'role_detail') and getattr(user, 'role_detail', '') == 'engineer') or \
           (hasattr(user, 'role_level') and user.role_level == 3)):
        flash(f'您没有权限访问此页面，当前角色: {user.role}, 角色详情: {getattr(user, "role_detail", "无")}, 角色级别: {getattr(user, "role_level", "无")}')
        return redirect(url_for('user.user_panel'))
    
    # 获取工程师相关数据
    engineer_info = Engineer.query.filter_by(user_id=user.id).first()
    assigned_products = Project.query.filter_by(assigned_engineer_id=engineer_info.id).filter(Project.status != 'completed').all() if engineer_info else []
    completed_products = Project.query.filter_by(assigned_engineer_id=engineer_info.id, status='completed').all() if engineer_info else []
    
    return render_template('engineer_panel.html', engineer=engineer_info, assigned_products=assigned_products, completed_products=completed_products)

@user_bp.route('/customer_service_panel')
@login_required
def customer_service_panel():
    # 客服面板
    user = current_user
    
    # 确保只有客服角色可以访问
    if not (hasattr(user, 'role_level') and user.role_level == 3 and getattr(user, 'role_detail', '') == 'customer_service'):
        flash('您没有权限访问此页面')
        return redirect(url_for('user.user_panel'))
    
    # 获取客服相关数据
    cs_info = CustomerService.query.filter_by(user_id=user.id).first()
    
    return render_template('customer_service_panel.html', customer_service=cs_info)

@user_bp.route('/trainee_panel')
@login_required
def trainee_panel():
    # 试岗员工面板
    user = current_user
    
    # 确保只有试岗员工角色可以访问
    if not (hasattr(user, 'role_level') and user.role_level == 4):
        flash('您没有权限访问此页面')
        return redirect(url_for('user.user_panel'))
    
    # 获取试岗员工相关数据
    trainee_info = Trainee.query.filter_by(user_id=user.id).first()
    
    return render_template('trainee_panel.html', trainee=trainee_info)

@user_bp.route('/training_materials')
@login_required
def training_materials():
    # 培训资料页面
    user = current_user
    
    # 获取搜索关键词和选中的类别
    search_query = request.args.get('search', '').strip()
    selected_category = request.args.get('category', '').strip()
    search_performed = bool(search_query)
    category_selected = bool(selected_category)
    
    # 确保用户是工程师或试岗员工
    if not (user.role == 'engineer' or 
           (hasattr(user, 'role_detail') and getattr(user, 'role_detail', '') == 'engineer') or 
           (hasattr(user, 'role_level') and (user.role_level == 3 or user.role_level == 4))):
        flash('您没有权限访问此页面')
        return redirect(url_for('user.user_panel'))
    
    # 获取所有培训资料，按类别和显示顺序排序
    all_materials = TrainingMaterial.query.order_by(
        TrainingMaterial.category,
        TrainingMaterial.display_order
    ).all()
    
    # 添加默认类别选择逻辑
    if not search_performed and not category_selected and all_materials:
        # 创建类别集合，确保每个类别只出现一次且去除空白字符
        categories = set()
        for material in all_materials:
            if material.category and material.category.strip():
                categories.add(material.category.strip())
        
        # 如果存在类别，按字母顺序排序并选择第一个
        if categories:
            sorted_categories = sorted(categories)
            first_category = sorted_categories[0]
            # 使用重定向确保URL反映当前选中的类别
            return redirect(url_for('user.training_materials', category=first_category))
    
    # 根据搜索关键词和类别过滤资料
    materials_to_display = all_materials
    
    if search_query:
        materials_to_display = [
            m for m in materials_to_display 
            if search_query.lower() in m.title.lower() or 
               search_query.lower() in (m.description or '').lower() or 
               search_query.lower() in m.category.lower()
        ]
    
    if selected_category:
        materials_to_display = [
            m for m in materials_to_display 
            if m.category and m.category.strip() == selected_category.strip()
        ]
    
    # 构建类别信息
    categories_dict = {}
    for material in all_materials:
        if material.category and material.category.strip() not in categories_dict:
            categories_dict[material.category.strip()] = {
                'name': material.category.strip(),
                'is_required': material.is_required,
                'is_basic': getattr(material, 'is_basic', False),
                'badge_text': '必学' if material.is_required else ('基础' if getattr(material, 'is_basic', False) else '进阶')
            }
    
    # 按类别组织要显示的资料
    materials_by_category_dict = {}
    for material in materials_to_display:
        cat_key = material.category.strip() if material.category else '未分类'
        if cat_key not in materials_by_category_dict:
            materials_by_category_dict[cat_key] = []
        materials_by_category_dict[cat_key].append({
            'id': material.id,
            'title': material.title,
            'description': material.description,
            'file_path': material.file_path,
            'file_type': material.file_type,
            'is_required': material.is_required
        })
    
    # 准备模板所需数据
    category_list = sorted(categories_dict.values(), key=lambda x: x['name'])
    formatted_materials = []
    
    # 根据是否选择了特定类别来构建数据
    if category_selected:
        # 如果选择了特定类别，只构建该类别的数据
        if selected_category in categories_dict:
            category = categories_dict[selected_category]
            category_materials = materials_by_category_dict.get(selected_category, [])
            formatted_materials.append({
                'name': selected_category,
                'materials': category_materials,
                'is_required': category['is_required'],
                'is_basic': category['is_basic'],
                'badge_text': category['badge_text']
            })
    else:
        # 如果没有选择特定类别，构建所有类别的数据
        for category in category_list:
            category_materials = materials_by_category_dict.get(category['name'], [])
            formatted_materials.append({
                'name': category['name'],
                'materials': category_materials,
                'is_required': category['is_required'],
                'is_basic': category['is_basic'],
                'badge_text': category['badge_text']
            })
    
    # 确保处理未分类的资料
    uncategorized_materials = [
        m for m in materials_to_display 
        if not m.category or not m.category.strip()
    ]
    
    # 计算总资料数
    total_materials = len(materials_to_display)
    if uncategorized_materials:
        uncategorized_formatted = [
            {
                'id': m.id,
                'title': m.title,
                'description': m.description,
                'file_path': m.file_path,
                'file_type': m.file_type,
                'is_required': m.is_required
            }
            for m in uncategorized_materials
        ]
        formatted_materials.append({
            'name': '未分类',
            'materials': uncategorized_formatted
        })
    
    # 确保至少传递一个空数组而不是None
    formatted_materials = formatted_materials or []
    category_list = category_list or []
    
    return render_template(
        'training_materials.html',
        materials_by_category=formatted_materials,
        categories=category_list,
        total_materials=total_materials,
        search_performed=search_performed,
        selected_category=selected_category,
        category_selected=category_selected
    )

@user_bp.route('/customer_inquiries')
@login_required
def customer_inquiries():
    # 客户咨询页面
    user = current_user
    
    # 确保用户是客服
    if not (hasattr(user, 'role_level') and user.role_level == 3 and getattr(user, 'role_detail', '') == 'customer_service'):
        flash('您没有权限访问此页面')
        return redirect(url_for('user.user_panel'))
    
    return render_template('customer_inquiries.html')

@user_bp.route('/project_search')
@login_required
def project_search():
    """项目查询页面"""
    user = current_user
    
    # 验证用户是否为客服、管理员或超级管理员
    if not (user.role == 'customer_service' or 
           (hasattr(user, 'role_detail') and getattr(user, 'role_detail', '') == 'customer_service') or 
           user.role == 'admin' or 
           user.role == 'super_admin'):
        flash('您没有权限访问此页面')
        return redirect(url_for('user.user_panel'))
    
    # 获取所有项目用于查询
    projects = Project.query.all()
    
    return render_template('product_search.html', projects=projects)

@user_bp.route('/update_project_progress', methods=['POST'])    
@login_required
def update_project_progress():
    # 工程师更新项目进度
    user = current_user
    
    # 验证用户权限
    if not (user.role == 'engineer' or 
           (hasattr(user, 'role_detail') and getattr(user, 'role_detail', '') == 'engineer') or 
           (hasattr(user, 'role_level') and user.role_level == 3)):
        flash('您没有权限执行此操作')
        return redirect(url_for('user.user_panel'))
    
    try:
        # 获取请求数据
        project_id = request.form.get('project_id', type=int)
        new_progress = request.form.get('progress')
        
        if not project_id or not new_progress:
            flash('参数无效')
            return redirect(url_for('user.engineer_projects'))
        
        # 获取工程师信息
        engineer_info = Engineer.query.filter_by(user_id=user.id).first()
        if not engineer_info:
            flash('工程师信息不存在')
            return redirect(url_for('user.engineer_projects'))
        
        # 获取项目并验证权限
        project = Project.query.get(project_id)
        if not project:
            flash('项目不存在')
            return redirect(url_for('user.engineer_projects'))
        
        # 验证该项目是否分配给当前工程师
        if project.assigned_engineer_id != engineer_info.id:
            flash('您无权修改此项目的进度')
            return redirect(url_for('user.engineer_projects'))
        
        # 工程师可操作的进度选项（允许在这些进度之间任意修改）
        engineer_allowed_progresses = ['制作中', '完成待确认', '确认不发货', '确认待发货', '已完成']
        
        # 检查是否为结单状态且需要特殊处理
        if project.progress == '结单':
            flash('结单状态需要向管理员申请修改')
            return redirect(url_for('user.engineer_projects'))
        
        # 验证新进度是否在允许范围内
        if new_progress not in engineer_allowed_progresses:
            flash('无效的进度状态')
            return redirect(url_for('user.engineer_projects'))
        
        # 更新进度
        project.progress = new_progress
        
        # 根据进度更新完成时间
        if new_progress == '已完成' or new_progress == '完成待确认':
            project.completed_time = datetime.utcnow()
        elif new_progress == '制作中':
            # 保持完成时间不变，仅更新进度
            pass
        
        db.session.commit()
        flash('项目进度更新成功')
    except Exception as e:
        db.session.rollback()
        flash(f'更新进度时出错: {str(e)}')
    return redirect(url_for('user.engineer_projects'))

@user_bp.route('/profile')
@login_required
def profile_redirect():
    return redirect(url_for('user.update_profile'))

# 移除重复的/profile路由定义，避免路由冲突

@user_bp.route('/completed')
@login_required
def completed_redirect():
    # 重定向到已完成项目页面
    return redirect(url_for('user.completed_projects'))

@user_bp.route('/user/completed')
@login_required
def user_completed_redirect():
    # 重定向到已完成项目页面 - 解决侧边栏链接问题
    return redirect(url_for('user.completed_projects'))

# 已合并到profile_redirect路由，避免重复定义导致的路由冲突

@user_bp.route('/request_progress_change/<int:project_id>', methods=['GET', 'POST'])
@login_required
def request_progress_change(project_id):
    # 工程师申请修改结单项目的进度
    user = current_user
    
    # 验证用户权限
    if not (user.role == 'engineer' or 
           (hasattr(user, 'role_detail') and getattr(user, 'role_detail', '') == 'engineer') or 
           (hasattr(user, 'role_level') and user.role_level == 3)):
        flash('您没有权限执行此操作')
        return redirect(url_for('user.user_panel'))
    
    # 获取工程师信息
    engineer_info = Engineer.query.filter_by(user_id=user.id).first()
    if not engineer_info:
        flash('工程师信息不存在')
        return redirect(url_for('user.engineer_projects'))
    
    # 获取项目并验证权限
    project = Project.query.get(project_id)
    if not project:
        flash('项目不存在')
        return redirect(url_for('user.engineer_projects'))
    
    # 验证该项目是否分配给当前工程师
    if project.assigned_engineer_id != engineer_info.id:
        flash('您无权修改此项目的进度')
        return redirect(url_for('user.engineer_projects'))
    
    # 验证项目是否为结单状态
    if project.progress != '结单':
        flash('只有结单状态的项目需要申请修改')
        return redirect(url_for('user.engineer_projects'))
    
    if request.method == 'POST':
        try:
            # 获取申请信息
            requested_progress = request.form.get('requested_progress')
            reason = request.form.get('reason')
            
            if not requested_progress or not reason:
                flash('请填写完整的申请信息')
                return redirect(url_for('user.request_progress_change', project_id=project_id))
            
            # 验证请求的进度是否在允许范围内
            allowed_progresses = ['制作中', '完成待确认', '确认不发货', '确认待发货', '已完成']
            if requested_progress not in allowed_progresses:
                flash('无效的进度状态')
                return redirect(url_for('user.request_progress_change', project_id=project_id))
            
            # 创建申请记录
            new_request = ProgressChangeRequest(
                project_id=project.id,
                engineer_id=engineer_info.id,
                requested_progress=requested_progress,
                reason=reason,
                status='pending'
            )
            
            db.session.add(new_request)
            db.session.commit()
            flash('进度修改申请已提交，请等待管理员审核')
            return redirect(url_for('user.engineer_projects'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'提交申请时出错: {str(e)}')
    
    # 渲染申请页面
    allowed_progresses = ['制作中', '完成待确认', '确认不发货', '确认待发货', '已完成']
    return render_template('request_progress_change.html', project=project, allowed_progresses=allowed_progresses)

@user_bp.route('/profile/<int:user_id>')
@login_required
def profile(user_id=None):
    # 如果没有提供user_id，默认使用当前登录用户的id
    if user_id is None:
        user_id = current_user.id
    
    # 检查是否有权限查看该用户资料
    if user_id != current_user.id and not (current_user.role == 'super_admin'):
        flash('您没有权限查看此用户资料')
        return redirect(url_for('user.profile', user_id=current_user.id))
    
    user = User.query.get(user_id)
    if not user:
        flash('用户不存在')
        return redirect(url_for('user.user_panel'))

    # 获取用户详细信息
    if user.role == 'admin':
        user_info = Admin.query.filter_by(user_id=user_id).first()
    else:
        user_info = Engineer.query.filter_by(user_id=user_id).first()
    
    # 创建表单对象并预填充数据
    form = EditUserForm(obj=user)
    if user_info:
        form.new_name.data = user_info.name
    
    return render_template('profile.html', user=user, user_info=user_info, form=form)