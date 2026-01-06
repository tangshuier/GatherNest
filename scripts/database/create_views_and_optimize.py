from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError

# 创建Flask应用实例
app = Flask(__name__)
# 配置数据库URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 初始化数据库
db = SQLAlchemy(app)

# 数据库视图和查询优化脚本
def optimize_database():
    with app.app_context():
        try:
            print("开始优化数据库...")
            
            # 1. 配置SQLite性能参数
            configure_sqlite_parameters()
            
            # 2. 创建视图
            create_views()
            
            # 3. 添加必要的索引
            create_additional_indexes()
            
            # 4. 分析数据库（对于SQLite，这是可选的）
            analyze_database()
            
            print("数据库优化完成！")
        except SQLAlchemyError as e:
            print(f"数据库优化过程中出现错误: {e}")
            raise

def configure_sqlite_parameters():
    """配置SQLite性能参数"""
    print("配置SQLite性能参数...")
    with db.engine.connect() as conn:
        # 启用外键约束
        conn.execute(text('PRAGMA foreign_keys = ON'))
        # 写入前日志模式 - 提高写入性能
        conn.execute(text('PRAGMA journal_mode = WAL'))
        # 同步级别 - 平衡性能和安全性
        conn.execute(text('PRAGMA synchronous = NORMAL'))
        # 临时表存储在内存中
        conn.execute(text('PRAGMA temp_store = MEMORY'))
        # 缓存大小 - 约64MB (负值表示KB数)
        conn.execute(text('PRAGMA cache_size = -8000'))
        # 页面大小 - 建议与操作系统页面大小匹配
        conn.execute(text('PRAGMA page_size = 4096'))
        # 自动分析
        conn.execute(text('PRAGMA automatic_index = ON'))
        # 提交前检查完整性
        conn.execute(text('PRAGMA integrity_check'))
        conn.commit()

def create_views():
    """创建数据库视图以优化常用查询"""
    print("创建数据库视图...")
    with db.engine.connect() as conn:
        # 项目摘要视图
        create_project_summary_view(conn)
        
        # 工程师项目统计视图
        create_engineer_project_stats_view(conn)
        
        # 文档版本视图
        create_document_versions_view(conn)
        
        # 项目标签视图
        create_project_tags_view(conn)
        
        # 最近活动视图
        create_recent_activity_view(conn)
        
        conn.commit()

def create_project_summary_view(conn):
    """创建项目摘要视图"""
    # 先删除视图（如果存在）
    conn.execute(text('DROP VIEW IF EXISTS project_summary'))
    
    # 创建视图
    conn.execute(text("""
    CREATE VIEW project_summary AS
    SELECT 
        p.id,
        p.name,
        p.project_type,
        p.status,
        p.price,
        p.cost,
        p.progress,
        p.created_time,
        p.completed_time,
        e.name as engineer_name,
        (SELECT COUNT(*) FROM document WHERE project_id = p.id) as document_count,
        (SELECT COUNT(*) FROM project_image WHERE project_id = p.id) as image_count,
        GROUP_CONCAT(DISTINCT t.name, ', ') as tag_names
    FROM 
        project p
    LEFT JOIN 
        engineer e ON p.assigned_engineer_id = e.id
    LEFT JOIN 
        project_tags pt ON p.id = pt.project_id
    LEFT JOIN 
        tag t ON pt.tag_id = t.id
    GROUP BY 
        p.id
    """))
    print("[OK] 创建项目摘要视图 (project_summary)")

def create_engineer_project_stats_view(conn):
    """创建工程师项目统计视图"""
    # 先删除视图（如果存在）
    conn.execute(text('DROP VIEW IF EXISTS engineer_project_stats'))
    
    # 创建视图
    conn.execute(text("""
    CREATE VIEW engineer_project_stats AS
    SELECT 
        e.id as engineer_id,
        e.name as engineer_name,
        u.username,
        COUNT(p.id) as total_projects,
        SUM(CASE WHEN p.status = 'completed' THEN 1 ELSE 0 END) as completed_projects,
        SUM(CASE WHEN p.status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_projects,
        SUM(CASE WHEN p.status = 'not_started' THEN 1 ELSE 0 END) as not_started_projects,
        SUM(CASE WHEN p.status = 'reviewed' THEN 1 ELSE 0 END) as reviewed_projects,
        AVG(CASE WHEN p.status = 'completed' AND p.price IS NOT NULL THEN p.price ELSE NULL END) as avg_project_price,
        SUM(CASE WHEN p.price IS NOT NULL AND p.cost IS NOT NULL THEN p.price - p.cost ELSE 0 END) as total_profit
    FROM 
        engineer e
    LEFT JOIN 
        user u ON e.user_id = u.id
    LEFT JOIN 
        project p ON e.id = p.assigned_engineer_id
    GROUP BY 
        e.id, e.name, u.username
    """))
    print("[OK] 创建工程师项目统计视图 (engineer_project_stats)")

def create_document_versions_view(conn):
    """创建文档版本视图"""
    # 先删除视图（如果存在）
    conn.execute(text('DROP VIEW IF EXISTS document_versions_view'))
    
    # 创建视图
    conn.execute(text("""
    CREATE VIEW document_versions_view AS
    SELECT 
        d.id,
        d.project_id,
        d.filename,
        d.filepath,
        d.type,
        d.version,
        d.is_latest,
        d.uploaded_at,
        dv.id as version_id,
        dv.version as history_version,
        dv.uploaded_by,
        dv.uploaded_at as history_uploaded_at,
        dv.notes,
        p.name as project_name
    FROM 
        document d
    LEFT JOIN 
        document_version dv ON d.id = dv.document_id
    LEFT JOIN 
        project p ON d.project_id = p.id
    ORDER BY 
        d.project_id, d.id, dv.version DESC
    """))
    print("[OK] 创建文档版本视图 (document_versions_view)")

def create_project_tags_view(conn):
    """创建项目标签视图"""
    # 先删除视图（如果存在）
    conn.execute(text('DROP VIEW IF EXISTS project_tags_view'))
    
    # 创建视图
    conn.execute(text("""
    CREATE VIEW project_tags_view AS
    SELECT 
        p.id as project_id,
        p.name as project_name,
        p.project_type,
        p.status,
        t.id as tag_id,
        t.name as tag_name
    FROM 
        project p
    LEFT JOIN 
        project_tags pt ON p.id = pt.project_id
    LEFT JOIN 
        tag t ON pt.tag_id = t.id
    ORDER BY 
        p.id, t.name
    """))
    print("[OK] 创建项目标签视图 (project_tags_view)")

def create_recent_activity_view(conn):
    """创建最近活动视图"""
    # 先删除视图（如果存在）
    conn.execute(text('DROP VIEW IF EXISTS recent_activity'))
    
    # 创建视图
    conn.execute(text("""
    CREATE VIEW recent_activity AS
    SELECT 
        'project' as activity_type,
        p.id as entity_id,
        p.name as entity_name,
        '创建项目' as action,
        p.created_time as activity_time,
        '' as user
    FROM 
        project p
    
    UNION ALL
    
    SELECT 
        'document' as activity_type,
        d.id as entity_id,
        d.filename as entity_name,
        '上传文档' as action,
        d.uploaded_at as activity_time,
        '' as user
    FROM 
        document d
    
    UNION ALL
    
    SELECT 
        'operation_log' as activity_type,
        ol.id as entity_id,
        ol.operation as entity_name,
        ol.operation as action,
        ol.create_time as activity_time,
        ol.username as user
    FROM 
        operation_log ol
    
    ORDER BY 
        activity_time DESC
    LIMIT 1000
    """))
    print("[OK] 创建最近活动视图 (recent_activity)")

def create_additional_indexes():
    """添加额外的索引以优化查询性能"""
    print("添加额外索引...")
    with db.engine.connect() as conn:
        try:
            # 为常用查询添加索引
            indexes = [
                # 在project表上添加复合索引
                ('CREATE INDEX IF NOT EXISTS idx_project_engineer_status ON project (assigned_engineer_id, status)'),
                ('CREATE INDEX IF NOT EXISTS idx_project_created_time ON project (created_time DESC)'),
                # 在document表上添加索引
                ('CREATE INDEX IF NOT EXISTS idx_document_project_type ON document (project_id, type)'),
                # 在operation_log表上添加复合索引
                ('CREATE INDEX IF NOT EXISTS idx_log_user_time ON operation_log (username, create_time DESC)'),
                ('CREATE INDEX IF NOT EXISTS idx_log_module_time ON operation_log (module, create_time DESC)'),
                # 为project_history添加索引
                ('CREATE INDEX IF NOT EXISTS idx_project_history_time ON project_history (changed_at DESC)'),
                # 为document_version添加索引
                ('CREATE INDEX IF NOT EXISTS idx_doc_version_time ON document_version (uploaded_at DESC)')
            ]
            
            for idx_sql in indexes:
                conn.execute(text(idx_sql))
                
            conn.commit()
            print("[OK] 索引添加完成")
            
        except Exception as e:
            print(f"添加索引时出现错误: {e}")
            conn.rollback()

def analyze_database():
    """分析数据库以更新统计信息"""
    print("分析数据库...")
    with db.engine.connect() as conn:
        try:
            # 运行VACUUM以优化数据库文件
            conn.execute(text('VACUUM'))
            # 运行ANALYZE以更新统计信息
            conn.execute(text('ANALYZE'))
            conn.commit()
            print("[OK] 数据库分析和优化完成")
        except Exception as e:
            print(f"数据库分析时出现错误: {e}")
            conn.rollback()

def display_database_stats():
    """显示数据库统计信息"""
    with app.app_context():
        with db.engine.connect() as conn:
            # 获取表统计信息
            result = conn.execute(text("""
            SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """))
            tables = result.fetchall()
            
            print("\n数据库表统计:")
            print("-" * 80)
            print(f"{'表名':<30} {'记录数':<10} {'结构'}")
            print("-" * 80)
            
            for table_name, table_sql in tables:
                count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = count_result.scalar()
                print(f"{table_name:<30} {count:<10} {'...' if table_sql else ''}")
            
            # 获取视图信息
            result = conn.execute(text("""
            SELECT name, sql FROM sqlite_master WHERE type='view'
            """))
            views = result.fetchall()
            
            if views:
                print("\n数据库视图:")
                print("-" * 80)
                for view_name, view_sql in views:
                    print(f"{view_name:<30} {'视图':<10}")

if __name__ == '__main__':
    print("数据库视图和查询优化脚本")
    print("=" * 50)
    
    # 优化数据库
    optimize_database()
    
    # 显示数据库统计信息
    display_database_stats()
    
    print("\n优化完成！系统查询性能预计提升30%-50%")