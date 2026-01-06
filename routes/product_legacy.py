from flask import Blueprint, render_template, current_app, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import math
import os
import pandas as pd
from .models import Project, Engineer, User, Document, ProjectImage, db
from .decorators import admin_required, role_required, engineer_required
import re
from flask import send_from_directory, abort
from werkzeug.utils import secure_filename

# 统一使用project_bp作为蓝图名称
project_bp = Blueprint('project', __name__)

VALID_PROGRESS_OPTIONS = [
    '无方案', '需要方案', '方案未确认', '确认方案不制作',
    '待制作', '制作中', '完成待确认', '确认不发货',
    '确认待发货', '已完成', '结单', '售后修改'
]

@project_bp.route('/projects')
@login_required
def projects_redirect():
    """重定向到项目管理页面"""
    return redirect(url_for('project.projects_management'))

@project_bp.route('/projects/add')
@login_required
@role_required('admin')
def projects_add_redirect():
    """重定向到添加项目页面"""
    edit_project_id = request.args.get('edit', type=int)
    if edit_project_id:
        return redirect(url_for('project.projects_add', edit=edit_project_id))
    return redirect(url_for('project.projects_add'))

@project_bp.route('/fix_project_data')
@login_required
@admin_required
def fix_project_data():
    """修复项目数据中的问题"""
    try:
        # 查找没有名称的项目
        nameless_projects = Project.query.filter_by(name='').all()
        for project in nameless_projects:
            project.name = f'未命名项目-{project.id}'
        
        # 查找价格为None的项目
        price_none_projects = Project.query.filter_by(price=None).all()
        for project in price_none_projects:
            project.price = 0
        
        # 修复文档路径问题
        documents = Document.query.all()
        for doc in documents:
            # 检查文件路径是否存在
            if not os.path.exists(doc.filepath):
                # 更新为正确的路径格式
                basedir = os.path.abspath(os.path.dirname(__file__))
                project = Project.query.get(doc.project_id)
                if project:
                    new_filepath = os.path.join(basedir, os.pardir, 'static', 'uploads', 'documents', f"{project.name}{os.path.splitext(doc.filename)[1]}")
                    if os.path.exists(new_filepath):
                        doc.filepath = new_filepath
        
        db.session.commit()
        flash('数据修复完成')
        return redirect(url_for('project_management.projects_list'))
    except Exception as e:
        db.session.rollback()
        flash(f'数据修复失败: {str(e)}')
        return redirect(url_for('project.projects_management'))

@project_bp.route('/projects/management')
@login_required
def projects_management():
    """项目管理页面，显示所有项目并提供搜索和筛选功能"""
    # 获取工程师列表
    engineers = Engineer.query.all()
    
    # 获取搜索参数
    search_query = request.args.get('search', '').strip()
    engineer_id = request.args.get('engineer_id', '')
    project_type = request.args.get('project_type', 'custom')
    status = request.args.get('status', '')
    progress = request.args.get('progress', '')
    
    # 构建查询
    query = Project.query
    
    # 应用搜索条件
    if search_query:
        query = query.filter(Project.name.like(f'%{search_query}%'))
    
    if engineer_id:
        query = query.filter_by(assigned_engineer_id=engineer_id)
    
    if project_type:
        query = query.filter_by(project_type=project_type)
    
    if status:
        query = query.filter_by(status=status)
    
    if progress:
        query = query.filter_by(progress=progress)
    
    # 按创建时间降序排序
    query = query.order_by(Project.created_time.desc())
    
    # 分页
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # 获取当前页的数据
    projects = pagination.items
    
    # 计算总页数
    total_pages = pagination.pages
    total_projects = pagination.total
    
    # 获取当前页码
    current_page = page
    
    from datetime import timedelta
    
    # 渲染模板
    return render_template('projects_management.html',
                          projects=projects,
                          engineers=engineers,
                          search_query=search_query,
                          engineer_id=engineer_id,
                          product_type=project_type,
                          status=status,
                          progress=progress,
                          current_page=current_page,
                          per_page=per_page,
                          total_pages=total_pages,
                          total_projects=total_projects,
                          timedelta=timedelta)
    
    for project in projects:
        # 检查项目是否有文档并且文档文件是否存在
        if project.documents:
            # 获取第一个文档（假设每个项目只有一个文档）
            doc = project.documents[0]
            if not os.path.exists(doc.filepath):
                # 如果文档文件不存在，删除文档记录
                db.session.delete(doc)
                db.session.commit()
    
    from datetime import timedelta
    # 确保查询所有工程师
    all_engineers = Engineer.query.all()
    print(f"Engineers count: {len(all_engineers)}")  # 用于调试
    
    return render_template('projects_management.html', 
                          projects=projects, 
                          engineers=all_engineers,
                          search_query=search_query,
                          engineer_id=engineer_id,
                          project_type=project_type,
                          progress=progress,
                          current_page=page,
                          per_page=per_page,
                          total_pages=total_pages,
                          total_projects=total,
                          timedelta=timedelta)

@project_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def projects_add():
    edit_project = None
    edit_project_id = request.args.get('edit', type=int)
    if edit_project_id:
        edit_project = Project.query.get(edit_project_id)
        if not edit_project:
            flash('项目不存在', 'danger')
            return redirect(url_for('project_management.projects_list'))
    
    from datetime import timedelta
    engineers = Engineer.query.all()
    
    return render_template('projects_add.html',
                          engineers=engineers,
                          timedelta=timedelta,
                          edit_project=edit_project)

        # 保存原始值用于比较
        original_name = project.name
        original_price = project.price
        original_engineer_id = project.assigned_engineer_id
        original_requirements = project.requirements
        original_cost = project.cost
        original_unit_price = project.unit_price
        original_group_name = project.group_name
        original_progress = getattr(project, 'progress', None)
        
        # 处理文档上传
        document_file = request.files.get('document')
        
        # 直接从请求中获取所有字段，确保名称与表单一致
        new_name = request.form.get('name', '').strip()
        new_price_str = request.form.get('price', '').strip()
        new_engineer_id_str = request.form.get('engineer_id', '').strip()
        new_description = request.form.get('description', '').strip()
        new_cost_str = request.form.get('cost', '').strip()
        new_unit_price_str = request.form.get('unit_price', '').strip()
        new_group_name = request.form.get('group_name', '').strip()
        new_project_type = request.form.get('product_type', project.product_type)
        
        # 更新项目名称
        if new_name:
            project.name = new_name
            current_app.logger.info(f"用户: {current_user.username}")
        
        # 直接从请求中获取product_id
        project_id = request.form.get('project_id', type=int)
        
        # 基本验证
        if not project_id:
            flash('项目ID无效', 'danger')
            return redirect(url_for('project.projects_management'))
        
        # 查找项目
        product = Project.query.get(project_id)
        if not product:
            flash('项目不存在', 'danger')
            return redirect(url_for('project.projects_management'))
        
        # 保存原始值用于比较
        original_name = product.name
        original_price = product.price
        original_engineer_id = product.assigned_engineer_id
        original_requirements = product.requirements
        original_cost = product.cost
        original_unit_price = product.unit_price
        original_group_name = product.group_name
        original_progress = getattr(product, 'progress', None)
        
        # 处理文档上传
        document_file = request.files.get('document')
        
        # 直接从请求中获取所有字段，确保名称与表单一致
        new_name = request.form.get('name', '').strip()
        new_price_str = request.form.get('price', '').strip()
        new_engineer_id_str = request.form.get('engineer_id', '').strip()
        new_description = request.form.get('description', '').strip()
        new_cost_str = request.form.get('cost', '').strip()
        new_unit_price_str = request.form.get('unit_price', '').strip()
        new_group_name = request.form.get('group_name', '').strip()
        new_product_type = request.form.get('product_type', product.product_type)
        
        # 更新产品名称
        if new_name:
            product.name = new_name
        
        # 处理文档上传（如果有新文件）
        if document_file and document_file.filename:
            # 删除旧文档（如果有）
            if product.documents:
                for doc in product.documents:
                    if os.path.exists(doc.filepath):
                        try:
                            os.remove(doc.filepath)
                        except Exception as e:
                            current_app.logger.error(f"删除旧文档失败: {str(e)}")
                    db.session.delete(doc)
            
            # 保存新文档
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(product.id))
            os.makedirs(upload_dir, exist_ok=True)
            
            filename = secure_filename(document_file.filename)
            filepath = os.path.join(upload_dir, filename)
            document_file.save(filepath)
            
            # 创建新文档记录
            new_document = Document(
                project_id=product.id,
                filename=filename,
                filepath=filepath
            )
            db.session.add(new_document)
        
        # 更新产品类型
        product.product_type = new_product_type
        
        # 更新价格
        if new_price_str:
            try:
                product.price = float(new_price_str)
            except ValueError:
                flash('价格格式不正确', 'danger')
                return redirect(url_for('product.products_add', edit=project_id))
        
        # 更新工程师分配
        if new_engineer_id_str:
            try:
                new_engineer_id = int(new_engineer_id_str)
                if product.assigned_engineer_id != new_engineer_id:
                    product.assigned_engineer_id = new_engineer_id
                    product.assigned_time = datetime.utcnow()
            except ValueError:
                product.assigned_engineer_id = None
                product.assigned_time = None
        else:
            product.assigned_engineer_id = None
            product.assigned_time = None
        
        # 更新描述
        product.requirements = new_description
        
        # 更新成本
        if new_cost_str:
            try:
                product.cost = float(new_cost_str)
            except ValueError:
                flash('成本格式不正确', 'danger')
                return redirect(url_for('product.products_add', edit=project_id))
        else:
            product.cost = None
        
        # 更新单价
        if new_unit_price_str:
            try:
                product.unit_price = float(new_unit_price_str)
            except ValueError:
                flash('单价格式不正确', 'danger')
                return redirect(url_for('product.products_add', edit=project_id))
        else:
            product.unit_price = None
        
        # 更新群名（仅针对定制产品）
        if product.product_type == 'custom':
            product.group_name = new_group_name
        
        # 更新进度字段
        new_progress = request.form.get('progress')
        if new_progress:
            # 基础进度选项
            basic_progresses = ['无方案', '方案未确认', '需要方案', '确认方案不制作', '待制作']
            # 扩展进度选项（仅管理员和工程师可设置）
            extended_progresses = ['制作中', '完成待确认', '确认不发货', '确认待发货', '已完成', '售后修改', '结单']
            
            # 检查权限
            if current_user.role in ['admin', 'engineer'] or new_progress in basic_progresses:
                product.progress = new_progress
        
        # 处理图片上传（如果有新图片）
        images = request.files.getlist('images')
        if images and any(img.filename for img in images):
            # 计算现有图片数量，用于新图片的排序
            existing_images_count = ProductImage.query.filter_by(project_id=product.id).count()
            
            for idx, image in enumerate(images):
                if image and image.filename and allowed_image_file(image.filename):
                    image_info = save_product_image(image, product.id)
                    if image_info:
                        new_image = ProductImage(
                            project_id=product.id,
                            filename=image_info['filename'],
                            filepath=image_info['filepath'],
                            order_index=existing_images_count + idx
                        )
                        db.session.add(new_image)
        
        # 立即提交更改到数据库
        db.session.commit()
        
        # 记录更新信息
        updated_fields = []
        if product.name != original_name:
            updated_fields.append(f"名称: {original_name} → {product.name}")
        if product.price != original_price:
            updated_fields.append(f"价格: {original_price} → {product.price}")
        if product.assigned_engineer_id != original_engineer_id:
            updated_fields.append(f"工程师ID: {original_engineer_id} → {product.assigned_engineer_id}")
        if product.requirements != original_requirements:
            updated_fields.append("描述已更新")
        if product.cost != original_cost:
            updated_fields.append(f"成本: {original_cost} → {product.cost}")
        if product.unit_price != original_unit_price:
            updated_fields.append(f"单价: {original_unit_price} → {product.unit_price}")
        if product.group_name != original_group_name:
            updated_fields.append(f"群名: {original_group_name} → {product.group_name}")
        
        if updated_fields and current_app:
            current_app.logger.info(f"产品 {project_id} 更新了以下字段: {', '.join(updated_fields)}")
        
        # 重定向到产品管理页面
        flash('产品信息更新成功', 'success')
        return redirect(url_for('project_management.projects_list'))
        
    except Exception as e:
        # 确保回滚事务
        db.session.rollback()
        error_msg = f'更新产品失败: {str(e)}'
        if current_app:
            current_app.logger.error(error_msg, exc_info=True)
        flash(error_msg, 'danger')
        return redirect(url_for('project_management.projects_list'))

# 图片上传相关配置
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_image_file(filename):
    """检查文件扩展名是否在允许的列表中"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def save_project_image(file, project_id):
    """保存项目图片到指定目录"""
    if not allowed_image_file(file.filename):
        return None
    
    # 确保上传目录存在
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(project_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # 生成安全的文件名
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_dir, filename)
    
    # 保存文件
    try:
        file.save(filepath)
        return {
            'filename': filename,
            'filepath': filepath
        }
    except Exception as e:
        current_app.logger.error(f'保存图片失败: {e}')
        return None

@project_bp.route('/add_product_manual', methods=['POST'])
@login_required
@admin_required
def add_product_manual():
    # 注意：虽然函数名包含product，但实际操作的是Project模型，保持与数据库一致
    try:
        # 添加完整的请求表单数据日志，用于调试
        if current_app:
            current_app.logger.info(f"收到产品添加请求，表单数据: {dict(request.form)}")
            current_app.logger.info(f"文件数据: {[file.filename for file in request.files.values()]}")
            current_app.logger.info(f"用户: {current_user.username}")
        
        # 获取产品类型
        product_type = request.form.get('product_type', 'custom')  # 默认定制
        
        # 获取并验证产品名称
        name = request.form.get('name', '').strip()
        if not name:
            flash('产品名称不能为空', 'danger')
            return redirect(url_for('product.products_add'))
        
        # 根据产品类型进行特定验证和字段获取
        if product_type == 'custom':
            # 定制产品：验证必填字段
            group_name = request.form.get('group_name', '').strip()
            price_str = request.form.get('price', '').strip()
            
            if not group_name:
                flash('定制产品必须填写群名', 'danger')
                return redirect(url_for('product.products_add'))
            
            if not price_str:
                flash('定制产品必须填写产品总价', 'danger')
                return redirect(url_for('product.products_add'))
            
            # 验证价格格式
            try:
                price_value = float(price_str)
            except ValueError:
                flash('价格格式不正确，请输入数字', 'danger')
                return redirect(url_for('product.products_add'))
                
            # 处理成本和单价
            cost_str = request.form.get('cost', '').strip()
            cost = float(cost_str) if cost_str else None
            
            unit_price_str = request.form.get('unit_price', '').strip()
            unit_price = float(unit_price_str) if unit_price_str else None
        else:
            # 成品产品：只验证名称，价格可选
            price_str = request.form.get('price', '').strip()
            try:
                price_value = float(price_str) if price_str else 0
            except ValueError:
                flash('价格格式不正确，请输入数字', 'danger')
                return redirect(url_for('product.products_add'))
                
            cost = None
            unit_price = None
            group_name = None
        
        # 获取其他通用字段
        description = request.form.get('description', '').strip()
        engineer_id_str = request.form.get('engineer_id', '').strip()
        document_file = request.files.get('document')
        
        # 获取进度字段（默认为'无方案'）
        progress = request.form.get('progress', '无方案')
        
        # 处理工程师ID
        engineer_id = None
        if engineer_id_str:
            try:
                engineer_id = int(engineer_id_str)
            except ValueError:
                flash('工程师ID格式不正确', 'warning')
        
        # 检查文件类型（如果有文件上传）
        if document_file and document_file.filename:
            allowed_extensions = {'doc', 'docx', 'pdf', 'jpg', 'jpeg', 'png', 'gif'}
            if '.' not in document_file.filename:
                flash('文件格式不支持', 'danger')
                return redirect(url_for('product.products_add'))
            file_ext = document_file.filename.rsplit('.', 1)[1].lower()
            if file_ext not in allowed_extensions:
                flash('需求文件只支持Word、PDF和图片文件', 'danger')
                return redirect(url_for('product.products_add'))
        
        # 创建产品对象
        new_product = Product(
            name=name,
            product_type=product_type,
            price=price_value,
            assigned_engineer_id=engineer_id,
            progress=progress,
            created_time=datetime.utcnow(),
            assigned_time=datetime.utcnow() if engineer_id else None,
            cost=cost,
            unit_price=unit_price,
            requirements=description,
            group_name=group_name
        )

        db.session.add(new_product)
        db.session.commit()

        # 保存上传的需求文件（如果有）
        if document_file and document_file.filename:
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(new_product.id))
            os.makedirs(upload_dir, exist_ok=True)

            filename = secure_filename(document_file.filename)
            filepath = os.path.join(upload_dir, filename)
            document_file.save(filepath)

            # 创建文档记录
            new_document = Document(
                project_id=new_product.id,
                filename=filename,
                filepath=filepath
            )
            db.session.add(new_document)
            db.session.commit()
        
        # 保存上传的产品图片（如果有）
        images = request.files.getlist('images')
        if images:
            for idx, image in enumerate(images):
                if image and image.filename and allowed_image_file(image.filename):
                    image_info = save_product_image(image, new_product.id)
                    if image_info:
                        new_image = ProductImage(
                            project_id=new_product.id,
                            filename=image_info['filename'],
                            filepath=image_info['filepath'],
                            order_index=idx
                        )
                        db.session.add(new_image)
            db.session.commit()

        flash('产品添加成功', 'success')
        return redirect(url_for('project_management.projects_list'))
    except Exception as e:
        db.session.rollback()
        flash(f'添加失败: {str(e)}', 'danger')
        return redirect(url_for('product.products_add'))

@project_bp.route('/add_product_upload', methods=['POST'])
@login_required
@admin_required
def add_product_upload():
    try:
        if 'product_file' not in request.files:
            flash('没有文件上传')
            return redirect(url_for('project_management.projects_list'))

        file = request.files['product_file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(url_for('project_management.projects_list'))

        # 检查文件类型
        allowed_extensions = {'xlsx', 'xls', 'csv', 'doc', 'docx', 'pdf'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            flash('只支持Excel、CSV、Word和PDF文件')
            return redirect(url_for('project_management.projects_list'))

        # 根据文件类型处理
        file_ext = file.filename.rsplit('.', 1)[1].lower()

        # 创建上传目录
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'product_imports')
        os.makedirs(upload_dir, exist_ok=True)

        # 保存文件
        filename = file.filename
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        if file_ext in {'xlsx', 'xls'}:
            try:
                df = pd.read_excel(filepath)
            except ImportError:
                flash('缺少Excel读取库，请安装openpyxl: pip install openpyxl')
                return redirect(url_for('project_management.projects_list'))
            except Exception as e:
                flash(f'读取Excel文件失败: {str(e)}')
                return redirect(url_for('project_management.projects_list'))
        elif file_ext == 'csv':
            df = pd.read_csv(filepath)
        else:  # Word或PDF文件
            # 从文件名解析产品信息
            file_basename = os.path.splitext(filename)[0]
            pattern = r'^\d{3}-[\s\S]*$'

            if re.match(pattern, file_basename):
                product_name = file_basename
                product_number = product_name[:3]

                # 检查编号是否重复
                existing_product = Product.query.filter(Product.name.like(f'{product_number}-%')).first()
                if existing_product:
                    flash(f'产品编号 {product_number} 已存在')
                    return redirect(url_for('project_management.projects_list'))

                # 创建产品
                new_product = Product(
                    name=product_name,
                    created_time=datetime.utcnow()
                )

                db.session.add(new_product)
                db.session.commit()

                # 将上传的文档关联到产品
                product_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(new_product.id))
                os.makedirs(product_upload_dir, exist_ok=True)
                product_filepath = os.path.join(product_upload_dir, filename)

                # 移动文件到产品目录
                os.rename(filepath, product_filepath)

                # 创建文档记录
                new_document = Document(
                    project_id=new_product.id,
                    filename=filename,
                    filepath=product_filepath
                )

                db.session.add(new_document)
                db.session.commit()

                flash(f'产品 {product_name} 添加成功，并关联了文档')
            else:
                flash(f'文件 {filename} 已上传成功，但文件名格式不正确（应为：001-产品名），无法自动创建产品')
            return redirect(url_for('project_management.projects_list'))

        # 检查列是否存在（仅针对Excel和CSV）
        required_columns = ['编号', '产品名']
        for col in required_columns:
            if col not in df.columns:
                flash(f'文件缺少必要的列: {col}')
                return redirect(url_for('project_management.projects_list'))

        # 处理每一行数据
        success_count = 0
        error_count = 0
        error_messages = []

        for index, row in df.iterrows():
            try:
                # 获取数据
                product_number = str(row['编号']).strip().zfill(3)  # 确保是3位数字
                product_name = str(row['产品名']).strip()
                full_product_name = f'{product_number}-{product_name}'

                # 检查价格
                price = row.get('价格')
                price_value = float(price) if pd.notna(price) else None

                # 检查工程师ID
                engineer_id = row.get('工程师ID')
                engineer_id = int(engineer_id) if pd.notna(engineer_id) else None

                # 检查编号是否重复
                existing_product = Product.query.filter(Product.name.like(f'{product_number}-%')).first()
                if existing_product:
                    error_count += 1
                    error_messages.append(f'行 {index+1}: 产品编号 {product_number} 已存在')
                    continue

                # 创建产品
                new_product = Product(
                    name=full_product_name,
                    price=price_value,
                    assigned_engineer_id=engineer_id,
                    created_time=datetime.utcnow(),
                    assigned_time=datetime.utcnow() if engineer_id else None
                )

                db.session.add(new_product)
                db.session.commit()

                # 创建文档记录（关联上传的Excel/CSV文件）
                new_document = Document(
                    project_id=new_product.id,
                    filename=filename,
                    filepath=filepath
                )

                db.session.add(new_document)
                success_count += 1
            except Exception as e:
                error_count += 1
                error_messages.append(f'行 {index+1}: {str(e)}')

        # 提交更改
        db.session.commit()

        # 显示结果
        flash(f'文件上传完成: 成功添加 {success_count} 个产品, 失败 {error_count} 个')
        for msg in error_messages:
            flash(msg)

        return redirect(url_for('project_management.projects_list'))
    except Exception as e:
        db.session.rollback()
        flash(f'上传失败: {str(e)}')
        return redirect(url_for('project_management.projects_list'))

@project_bp.route('/assign_engineer/<int:project_id>', methods=['POST'])
@login_required
@role_required('admin')
def assign_engineer(project_id):
    product = Product.query.get_or_404(project_id)
    engineer_id = request.form.get('engineer_id')

    if not engineer_id:
        flash('请选择工程师', 'danger')
        return redirect(url_for('project_management.projects_list'))

    # 修复工程师检查逻辑
    engineer = Engineer.query.get(engineer_id)
    if not engineer:
        flash('无效的工程师', 'danger')
        return redirect(url_for('project_management.projects_list'))
    
    # 确保产品有基本信息
    # 只在产品名称确实为空时才设置默认名称，不覆盖已有名称
    if not product.name or product.name.strip() == '':
        product.name = f'未命名产品-{product.id}'
    
    # 只有在price为None时才设置默认值
    if product.price is None:
        product.price = 0

    product.assigned_engineer_id = engineer_id
    # 使用progress字段而不是status字段
    if product.progress == '无方案':
        product.progress = '方案未确认'  # 更合理的初始进度
    product.assigned_time = datetime.utcnow()  # 添加分配时间
    db.session.commit()

    flash(f'已成功分配工程师 {engineer.username}', 'success')
    return redirect(url_for('product.products_management'))

@project_bp.route('/mark_completed/<int:project_id>', methods=['POST'])
@login_required
@role_required('admin', 'engineer')
def mark_completed(project_id):
    product = Product.query.get_or_404(project_id)

    # 检查是否分配了工程师
    if not product.assigned_engineer_id:
        return jsonify({'error': '请先分配工程师'}), 400

    # 检查是否有文档
    doc = Document.query.filter_by(project_id=project_id).first()
    if not doc:
        return jsonify({'error': '请先上传文档'}), 400

    # 检查价格是否设置
    if not product.price:
        return jsonify({'error': '请先设置价格'}), 400

    product.status = 'pending_review'  # 改为待审核状态
    product.completed_time = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': '产品已标记为完成，等待审核'})

@project_bp.route('/projects/update_progress', methods=['POST'])
@login_required
@admin_required
def update_progress():
    project_id = request.form.get('project_id')
    new_progress = request.form.get('new_progress')
    
    if not project_id or not new_progress:
        return jsonify({'error': '缺少必要参数'}), 400
    
    product = Product.query.get_or_404(project_id)
    
    # 验证进度值
    if new_progress not in VALID_PROGRESS_OPTIONS:
        return jsonify({'error': '无效的进度值'}), 400
    
    # 更新进度
    product.progress = new_progress
    
    # 根据进度更新完成时间
    if new_progress in ['已完成', '结单', '完成待确认']:
        product.completed_time = datetime.utcnow()
    else:
        product.completed_time = None
        product.reviewed_time = None
    
    db.session.commit()
    return jsonify({'success': True, 'message': '产品进度已更新'})

@project_bp.route('/restart_project/<int:project_id>', methods=['POST'])
@login_required
@admin_required
def restart_product(project_id):
    try:
        product = Product.query.get(project_id)
        if not product:
            flash('产品不存在')
            return redirect(url_for('project_management.projects_list'))

        # 重置为初始进度状态
        product.progress = '待制作' if product.assigned_engineer_id else '需要方案'
        product.completed_time = None
        product.reviewed_time = None
        db.session.commit()

        flash('产品已重新开始')
        return redirect(url_for('project_management.projects_list'))
    except Exception as e:
        db.session.rollback()
        flash(f'操作失败: {str(e)}')
        return redirect(url_for('product.products_management'))

@project_bp.route('/update_price/<int:project_id>', methods=['POST'])
@login_required
@admin_required
def update_price(project_id):
    try:
        new_price = request.form.get('price')
        # 价格验证
        price_value = float(new_price) if new_price.strip() else None

        product = Product.query.get(project_id)
        if product:
            product.price = price_value
            db.session.commit()
        else:
            flash('产品不存在')
            return redirect(url_for('project_management.projects_list'))

        flash('价格更新成功')
        return redirect(url_for('product.products_management'))
    except ValueError:
        flash('价格必须是数字')
        return redirect(url_for('product.products_management'))
    except Exception as e:
        db.session.rollback()
        flash(f'更新失败: {str(e)}')
        return redirect(url_for('product.products_management'))

@project_bp.route('/update_document/<int:project_id>', methods=['POST'])
@login_required
@role_required('admin', 'engineer')
def update_document(project_id):
    product = Product.query.get_or_404(project_id)
    
    # 检查权限
    if current_user.role != 'admin':
        if current_user.role == 'engineer':
            engineer = Engineer.query.filter_by(user_id=current_user.id).first()
            if not engineer or product.assigned_engineer_id != engineer.id:
                abort(403)
        else:
            abort(403)
    
    # 处理文件上传
    if 'document' not in request.files:
        flash('没有文件上传', 'danger')
        return redirect(url_for('product.products_management'))
    
    file = request.files['document']
    if file.filename == '':
        flash('没有选择文件', 'danger')
        return redirect(url_for('product.products_management'))
    
    if file:
        # 生成与产品名称一致的文件名
        file_ext = os.path.splitext(file.filename)[1]
        filename = f"{product.name}{file_ext}"
        
        # 确保文件名安全
        filename = secure_filename(filename)
        
        # 保存路径
        basedir = os.path.abspath(os.path.dirname(__file__))
        upload_dir = os.path.join(basedir, os.pardir, 'static', 'uploads', 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        
        # 保存文件
        file.save(filepath)
        
        # 删除旧文档
        old_docs = Document.query.filter_by(project_id=project_id).all()
        for doc in old_docs:
            if os.path.exists(doc.filepath):
                try:
                    os.remove(doc.filepath)
                except Exception as e:
                    current_app.logger.error(f'删除旧文档失败: {e}')
            db.session.delete(doc)
        
        # 创建新文档记录
        new_doc = Document(project_id=project_id, filename=filename, filepath=filepath)
        db.session.add(new_doc)
        
        # 更新产品状态
        product.status = 'pending_review'
        product.completed_time = datetime.utcnow()
        
        db.session.commit()
        flash('文档更新成功', 'success')
        return redirect(url_for('product.products_management'))

@project_bp.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
@admin_required
def delete_project(project_id):
    try:
        # 检查项目是否存在
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404

        # 删除关联文档
        documents = Document.query.filter_by(project_id=project_id).all()
        for doc in documents:
            if os.path.exists(doc.filepath):
                try:
                    os.remove(doc.filepath)
                except Exception as e:
                    current_app.logger.error(f'删除文档文件失败: {e}')
            db.session.delete(doc)

        # 删除项目
        db.session.delete(project)
        db.session.commit()

        return jsonify({'success': True, 'message': '项目及关联文档已删除'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

@project_bp.route('/batch_assign_engineer', methods=['POST'])
@login_required
@admin_required
def batch_assign_engineer():
    try:
        import json
        product_ids = json.loads(request.form.get('product_ids', '[]'))
        engineer_id = request.form.get('engineer_id')

        if not product_ids or not engineer_id:
            flash('请选择产品和工程师')
            return redirect(url_for('project_management.projects_list'))

        # 检查工程师是否存在
        engineer = Engineer.query.get(engineer_id)
        if not engineer:
            flash('工程师不存在')
            return redirect(url_for('project_management.projects_list'))

        # 批量更新产品的工程师分配
        for project_id in product_ids:
            product = Product.query.get(project_id)
            if product:
                product.assigned_engineer_id = engineer_id
                product.assigned_time = datetime.utcnow()
                product.status = 'in_progress'
                product.completed_time = None
                product.reviewed_time = None

        db.session.commit()

        flash(f'成功分配 {len(product_ids)} 个产品给工程师')
        return redirect(url_for('product.products_management'))
    except Exception as e:
        db.session.rollback()
        flash(f'分配失败: {str(e)}')
        return redirect(url_for('product.products_management'))

@project_bp.route('/delete_all_documents/<int:project_id>', methods=['POST'])
@login_required
@role_required('admin', 'engineer')
def delete_all_documents(project_id):
    product = Product.query.get_or_404(project_id)
    docs = Document.query.filter_by(project_id=project_id).all()
    if not docs:
        flash('该产品没有文档可删除', 'info')
        return redirect(url_for('product.products_management'))

    for doc in docs:
        if os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                app.logger.error(f'删除文档文件失败: {e}')
        db.session.delete(doc)

    db.session.commit()
    flash('所有文档已成功删除', 'success')
    return redirect(url_for('product.products_management'))

@project_bp.route('/review_project/<int:project_id>', methods=['POST'])
@login_required
@admin_required
def review_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            flash('项目不存在')
            return redirect(url_for('project_management.projects_list'))

        if project.progress != '完成待确认':
            flash('只有完成待确认的项目才能进行审核')
            return redirect(url_for('project_management.projects_list'))

        project.progress = '已完成'
        project.reviewed_time = datetime.utcnow()
        db.session.commit()

        flash('项目审核通过')
        return redirect(url_for('product.products_management'))
    except Exception as e:
        db.session.rollback()
        flash(f'审核失败: {str(e)}')
        return redirect(url_for('product.products_management'))

@project_bp.route('/check_project_integrity')
@login_required
@admin_required
def check_project_integrity():
    # 查找没有文档的项目
    projects_without_docs = []
    all_projects = Project.query.all()
    marked_count = 0
    
    for project in all_projects:
        if not Document.query.filter_by(project_id=project.id).first():
            # 标记为异常状态
            project.progress = '确认方案不制作'  # 使用系统已有的进度状态
            marked_count += 1
            projects_without_docs.append(project)
    
    # 查找没有项目的文档
    docs_without_projects = []
    all_docs = Document.query.all()
    for doc in all_docs:
        if not Project.query.get(doc.project_id):
            docs_without_projects.append(doc)
            
    # 删除没有项目的文档
    for doc in docs_without_projects:
        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)
        db.session.delete(doc)
    
    db.session.commit()
    
    flash(f'成功标记 {marked_count} 个无文档项目为异常状态')
    return render_template('products_management.html',
                          products=all_projects,
                          engineers=Engineer.query.all(),
                          search_query='',
                          engineer_id='',
                          product_type='custom',
                          current_page=1,
                          per_page=10,
                          total_pages=1,
                          total_products=len(all_projects),
                          timedelta=timedelta)

@project_bp.route('/view_document/<int:project_id>')
@login_required
@role_required('admin', 'engineer')
def view_document(project_id):
    project = Project.query.get_or_404(project_id)
    doc = Document.query.filter_by(project_id=project_id).first()
    if not doc:
        flash('该项目没有关联文档', 'info')
        return redirect(url_for('project.projects_management'))

    if not os.path.exists(doc.filepath):
        flash('文档文件不存在', 'danger')
        return redirect(url_for('project.projects_management'))

    return send_from_directory(os.path.dirname(doc.filepath), doc.filename, as_attachment=False)

# 将第二个view_document函数重命名为view_document_by_id
@project_bp.route('/unmark_completed', methods=['POST'])
@login_required
@role_required('admin', 'engineer')
def unmark_completed():
    try:
        project_id = request.form.get('project_id')
        if not project_id:
            flash('无效的项目ID')
            return redirect(url_for('user.user_panel'))
            
        project = Project.query.get(project_id)
        if not project:
            flash('项目不存在')
            return redirect(url_for('user.user_panel'))
            
        # 检查权限
        if current_user.role != 'admin':
            if current_user.role == 'engineer':
                engineer = Engineer.query.filter_by(user_id=current_user.id).first()
                if not engineer or project.assigned_engineer_id != engineer.id:
                    flash('您没有权限执行此操作')
                    return redirect(url_for('user.user_panel'))
            else:
                flash('您没有权限执行此操作')
                return redirect(url_for('user.user_panel'))
                
        # 将项目进度改回进行中
        project.progress = '制作中'
        project.completed_time = None
        project.reviewed_time = None
        db.session.commit()
        
        flash('已成功取消完成状态')
        return redirect(url_for('user.user_panel'))
    except Exception as e:
        db.session.rollback()
        flash(f'操作失败: {str(e)}')
        return redirect(url_for('user.user_panel'))

@project_bp.route('/view_document_by_id/<int:document_id>')
@login_required
@role_required('admin', 'engineer')  # 添加适当的权限装饰器
def view_document_by_id(document_id):
    document = Document.query.get_or_404(document_id)
    project = Project.query.get(document.project_id)  # 使用正确的外键名称

    # 检查权限
    if current_user.role != 'admin':
        if current_user.role == 'engineer':
            engineer = Engineer.query.filter_by(user_id=current_user.id).first()
            if not engineer or project.assigned_engineer_id != engineer.id:
                abort(403)
        else:
            abort(403)

    # 检查文件是否存在
    if not os.path.exists(document.filepath):
        flash('文件不存在')
        return redirect(url_for('project.projects_management'))

    # 获取文件目录和文件名
    file_dir = os.path.dirname(document.filepath)
    filename = document.filename  # 使用文档记录中的原始文件名

    # 使用正确的文件名返回文件
    try:
        return send_from_directory(file_dir, filename, as_attachment=False)
    except Exception as e:
        flash(f'查看文档失败: {str(e)}', 'danger')
        return redirect(url_for('project.projects_management'))

@project_bp.route('/download_document/<int:document_id>')
@login_required
@role_required('admin', 'engineer')
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    product = Product.query.get(document.project_id)

    # 检查权限
    if current_user.role != 'admin':
        if current_user.role == 'engineer':
            engineer = Engineer.query.filter_by(user_id=current_user.id).first()
            if not engineer or product.assigned_engineer_id != engineer.id:
                abort(403)
        else:
            abort(403)

    # 检查文件是否存在
    if not os.path.exists(document.filepath):
        flash('文件不存在')
        return redirect(url_for('product.products_management'))

    # 获取文件目录和文件名
    file_dir = os.path.dirname(document.filepath)
    filename = document.filename  # 使用文档记录中的原始文件名

    # 直接使用send_from_directory，确保as_attachment=True用于下载
    try:
        response = send_from_directory(file_dir, filename, as_attachment=True)
        # 确保中文文件名正确编码
        response.headers['Content-Disposition'] = f'attachment; filename*=UTF-8''{filename}'
        return response
    except Exception as e:
        flash(f'下载文档失败: {str(e)}', 'danger')
        return redirect(url_for('product.products_management'))