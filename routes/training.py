from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
import re
import time
from .utils import allowed_file, validate_filename
from .decorators import role_required
from .models import db, TrainingMaterial

# 创建培训资料管理蓝图
training_bp = Blueprint('training', __name__)

# 文档上传目录
DOCUMENT_UPLOAD_FOLDER = os.path.join('static', 'uploads', 'documents')
VIDEO_UPLOAD_FOLDER = os.path.join('static', 'uploads', 'videos')

# 确保上传目录存在
if not os.path.exists(DOCUMENT_UPLOAD_FOLDER):
    os.makedirs(DOCUMENT_UPLOAD_FOLDER, exist_ok=True)

if not os.path.exists(VIDEO_UPLOAD_FOLDER):
    os.makedirs(VIDEO_UPLOAD_FOLDER, exist_ok=True)

@training_bp.route('/training_materials_manage', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def training_materials_manage():
    """管理员管理培训资料"""
    # 获取所有培训资料，按类别和显示顺序排序
    materials = TrainingMaterial.query.order_by(
        TrainingMaterial.category, 
        TrainingMaterial.display_order
    ).all()
    
    # 获取所有唯一的类别
    categories = db.session.query(TrainingMaterial.category).distinct().all()
    categories = [category[0] for category in categories]
    
    return render_template('manage_training_materials.html', 
                         materials=materials, 
                         categories=categories)

@training_bp.route('/add_training_material', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_training_material():
    """添加新的培训资料"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            category = request.form.get('category')
            title = request.form.get('title')
            description = request.form.get('description')
            file_type = request.form.get('file_type')
            is_required = request.form.get('is_required') == 'on'
            display_order = request.form.get('display_order', 0, type=int)
            
            # 检查文件是否上传
            file_path = None
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename != '':
                    try:
                        # 确保文件名安全
                        filename = secure_filename(file.filename)
                        filename = validate_filename(filename)
                        
                        # 根据文件类型选择保存目录
                        if file_type == 'mp4' or file_type == 'avi' or file_type == 'mov' or file_type == 'wmv':
                            save_dir = VIDEO_UPLOAD_FOLDER
                        else:
                            save_dir = DOCUMENT_UPLOAD_FOLDER
                        
                        # 确保保存目录存在
                        os.makedirs(save_dir, exist_ok=True)
                        
                        # 保存文件
                        file_path = os.path.join(save_dir, filename)
                        file.save(file_path)
                        print(f"文件保存路径: {file_path}")
                    except Exception as e:
                        print(f"文件保存错误: {str(e)}")
                        flash(f'文件上传失败: {str(e)}', 'danger')
                        return redirect(url_for('training.add_training_material'))
            
            # 创建新的培训资料
            new_material = TrainingMaterial(
                category=category,
                title=title,
                description=description,
                file_path=file_path,
                file_type=file_type,
                is_required=is_required,
                display_order=display_order
            )
            
            # 添加到数据库
            db.session.add(new_material)
            db.session.commit()
            
            flash('培训资料添加成功', 'success')
            return redirect(url_for('training.training_materials_manage'))
        except Exception as e:
            db.session.rollback()
            print(f"添加培训资料错误: {str(e)}")
            flash(f'添加培训资料失败: {str(e)}', 'danger')
            return redirect(url_for('training.add_training_material'))
    
    # 获取所有已有的类别
    categories = db.session.query(TrainingMaterial.category).distinct().all()
    categories = [category[0] for category in categories]
    
    return render_template('add_training_material.html', categories=categories)

@training_bp.route('/edit_training_material/<int:material_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_training_material(material_id):
    """编辑培训资料"""
    material = TrainingMaterial.query.get_or_404(material_id)
    
    if request.method == 'POST':
        # 更新表单数据
        material.category = request.form.get('category')
        material.title = request.form.get('title')
        material.description = request.form.get('description')
        material.file_type = request.form.get('file_type')
        material.is_required = request.form.get('is_required') == 'on'
        material.display_order = request.form.get('display_order', 0, type=int)
        
        # 检查是否上传了新文件
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                # 自定义的中文文件名处理逻辑，更好地保留原始中文名称
                # 首先获取文件扩展名
                original_name, ext = os.path.splitext(file.filename)
                
                # 仅移除文件名中的非法字符，保留中文和其他安全字符
                # 这比使用secure_filename更好，因为它不会移除中文字符
                safe_name = re.sub(r'[\\/:*?"<>|]', '', original_name)
                
                # 如果处理后文件名为空，则使用时间戳作为默认名称
                if not safe_name:
                    safe_name = str(int(time.time()))
                
                # 确保扩展名格式正确
                ext = ext.lower()
                if not ext:
                    # 根据文件类型设置默认扩展名
                    if material.file_type == 'mp4' or material.file_type == 'avi' or material.file_type == 'mov' or material.file_type == 'wmv':
                        ext = '.' + material.file_type
                    else:
                        ext = '.txt'
                
                # 重新组合文件名
                filename = f"{safe_name}{ext}"
                
                # 应用自定义的文件名验证
                filename = validate_filename(filename)
                
                # 根据文件类型选择保存目录
                if material.file_type == 'mp4' or material.file_type == 'avi' or material.file_type == 'mov' or material.file_type == 'wmv':
                    save_dir = VIDEO_UPLOAD_FOLDER
                else:
                    save_dir = DOCUMENT_UPLOAD_FOLDER
                
                # 保存文件
                file.save(os.path.join(save_dir, filename))
                material.file_path = os.path.join(save_dir, filename)
        
        # 保存更改
        db.session.commit()
        
        flash('培训资料更新成功', 'success')
        return redirect(url_for('training.training_materials_manage'))
    
    # 获取所有已有的类别
    categories = db.session.query(TrainingMaterial.category).distinct().all()
    categories = [category[0] for category in categories]
    
    return render_template('edit_training_material.html', material=material, categories=categories)

@training_bp.route('/delete_training_material/<int:material_id>')
@login_required
@role_required('admin')
def delete_training_material(material_id):
    """删除培训资料"""
    material = TrainingMaterial.query.get_or_404(material_id)
    
    # 如果有文件，删除文件
    if material.file_path and os.path.exists(material.file_path):
        os.remove(material.file_path)
    
    # 从数据库中删除
    db.session.delete(material)
    db.session.commit()
    
    flash('培训资料已删除', 'success')
    return redirect(url_for('training.training_materials_manage'))

@training_bp.route('/add_training_category', methods=['POST'])
@login_required
@role_required('admin')
def add_training_category():
    """添加新的培训类别"""
    new_category = request.form.get('new_category')
    
    if new_category:
        # 检查类别是否已存在
        existing_category = db.session.query(TrainingMaterial).filter_by(category=new_category).first()
        if not existing_category:
            # 创建一个临时材料来保存新类别
            temp_material = TrainingMaterial(
                category=new_category,
                title='临时条目',
                description='请编辑或删除此条目',
                file_type='txt',
                display_order=0
            )
            db.session.add(temp_material)
            db.session.commit()
            flash(f'类别 "{new_category}" 添加成功', 'success')
        else:
            flash(f'类别 "{new_category}" 已存在，请直接在该类别下添加资料', 'warning')
    
    return redirect(url_for('training.training_materials_manage'))