from contextlib import contextmanager
from routes.models import db, Product, Engineer, Document
from functools import wraps
from flask import redirect, request, flash
from contextlib import contextmanager

@contextmanager
def db_transaction():
    try:
        yield
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

# 添加常用数据库操作函数

def get_product(product_id):
    return Product.query.get(product_id)

def get_products(page=1, per_page=10, search_query='', engineer_id=''):
    query = Product.query.outerjoin(Engineer).outerjoin(Document)

    if search_query:
        query = query.filter((Product.name.like(f'%{search_query}%')) | (Product.id.like(f'%{search_query}%')))

    if engineer_id:
        query = query.filter(Product.assigned_engineer_id == engineer_id)

    total = query.count()
    products = query.order_by(Product.id.desc()).limit(per_page).offset((page-1)*per_page).all()
    return products, total

# 数据库事务装饰器
def db_transaction_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            flash(f'操作失败: {str(e)}')
            return redirect(request.referrer or '/')
    return decorated_function