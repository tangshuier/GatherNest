# 数据库初始化与优化指南

## 项目概述

本文档提供了项目数据库的初始化、优化和维护指南，适用于需要从头开始规划项目数据库的场景。通过执行本文档中的脚本，可以确保项目数据模型的一致性、完整性和性能优化。

## 数据模型设计

### 核心数据模型

本项目的数据模型经过优化，包含以下主要实体：

1. **用户管理相关**
   - `User`: 系统用户基本信息
   - `Engineer`: 工程师信息
   - `Admin`: 管理员信息
   - `CustomerService`: 客服信息
   - `Trainee`: 试岗员工信息

2. **项目管理相关**
   - `Project`: 项目基本信息
   - `ProjectImage`: 项目图片
   - `Document`: 项目文档
   - `Tag`: 项目标签
   - `project_tags`: 项目-标签关联表

3. **权限控制相关**
   - `Role`: 角色定义
   - `Permission`: 权限定义
   - `user_permissions`: 用户-权限关联表
   - `role_permissions`: 角色-权限关联表

4. **审计与历史记录相关**
   - `DocumentVersion`: 文档版本历史
   - `ProjectHistory`: 项目变更历史
   - `OperationLog`: 系统操作日志

5. **培训相关**
   - `TrainingMaterial`: 培训资料
   - `TagRequest`: 标签申请

### 数据模型优化特点

1. **规范化设计**：遵循数据库规范化原则，减少数据冗余
2. **外键约束**：全面使用外键约束确保数据一致性
3. **索引优化**：在常用查询字段上添加索引，提高查询性能
4. **级联操作**：合理设置级联删除规则，确保数据完整性
5. **历史记录**：关键实体支持版本历史，便于审计和回溯

## 数据库初始化流程

### 1. 准备工作

确保项目环境已安装必要的依赖：

```bash
pip install flask flask-sqlalchemy werkzeug
```

### 2. 初始化数据库

执行数据库初始化脚本，创建数据表结构并初始化基础数据：

```bash
cd scripts/database
python init_database.py
```

此脚本将：
- 删除旧的数据库文件（如果存在）
- 创建所有数据表
- 配置SQLite性能参数
- 创建系统角色和权限
- 创建超级管理员账户（默认用户名：admin，密码：admin123）

### 3. 数据库优化

执行数据库视图创建和优化脚本：

```bash
python create_views_and_optimize.py
```

此脚本将：
- 配置SQLite性能参数
- 创建优化查询的视图
- 添加额外索引
- 分析数据库并执行VACUUM操作

## 数据库视图说明

系统创建了以下视图以优化常用查询：

1. **project_summary**: 项目摘要视图，包含项目基本信息、关联工程师、文档数、图片数和标签
2. **engineer_project_stats**: 工程师项目统计视图，显示每位工程师的项目数量和状态分布
3. **document_versions_view**: 文档版本视图，便于查看文档的版本历史
4. **project_tags_view**: 项目标签视图，用于快速查询项目的标签信息
5. **recent_activity**: 最近活动视图，汇总系统中的各种操作记录

## 数据一致性保障措施

### 1. 外键约束

所有关联关系都使用外键约束，确保引用完整性：

- 项目与工程师的关联
- 文档与项目的关联
- 用户与角色的关联
- 等等

### 2. 级联操作

合理设置级联删除规则：

- 用户删除时，级联删除关联的个人资料
- 项目删除时，级联删除关联的文档和图片
- 标签删除时，级联删除项目-标签关联

### 3. 事务处理

使用数据库事务确保操作的原子性，避免部分操作成功导致的数据不一致。

### 4. 历史记录

重要实体变更时记录历史，便于审计和问题排查：

- 文档版本历史
- 项目变更历史
- 系统操作日志

## 性能优化建议

### 1. 查询优化

- 优先使用创建的视图进行查询，避免复杂的联表查询
- 针对频繁执行的查询添加适当的索引
- 避免在大型表上执行没有索引的全表扫描

### 2. 数据维护

- 定期执行VACUUM操作优化数据库文件
- 定期备份数据库
- 监控和清理不再需要的历史数据

### 3. SQLite特定优化

- 使用WAL模式提高并发性能
- 适当配置缓存大小
- 对于大型查询，考虑分批处理结果

## 安全建议

1. **密码管理**：首次登录后立即修改默认密码
2. **权限控制**：根据用户角色分配最小必要权限
3. **敏感数据**：避免在日志中记录敏感信息
4. **备份策略**：建立定期备份机制

## 数据库维护工具

### 1. 备份数据库

```python
# 备份数据库示例代码
import shutil
import os
from datetime import datetime

def backup_database():
    db_path = os.path.join('instance', 'database.db')
    if os.path.exists(db_path):
        # 创建备份目录
        backup_dir = os.path.join('backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'database_backup_{timestamp}.db')
        
        # 复制数据库文件
        shutil.copy2(db_path, backup_path)
        print(f"数据库备份完成: {backup_path}")
```

### 2. 数据导出

```python
# 数据导出示例代码
import csv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

def export_projects_to_csv():
    with app.app_context():
        projects = db.session.execute('SELECT * FROM project_summary').fetchall()
        
        with open('projects_export.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = projects[0].keys() if projects else []
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for project in projects:
                writer.writerow(dict(project))
            
        print("项目数据导出完成")
```

## 常见问题排查

### 1. 数据库连接错误

- 检查数据库文件路径是否正确
- 确保instance目录存在且可写入
- 检查SQLite数据库是否被锁定

### 2. 权限问题

- 确保用户有正确的权限执行操作
- 检查数据库文件的读写权限

### 3. 性能问题

- 使用创建的视图进行查询
- 检查是否缺少必要的索引
- 考虑优化复杂查询

## 后续维护计划

1. 定期审查数据模型，根据业务需求进行调整
2. 监控查询性能，必要时添加新索引
3. 定期清理历史数据，避免数据库过大
4. 考虑在用户量增长时迁移到更强大的数据库系统（如PostgreSQL）

---

**注意**：本指南中的脚本和建议应根据实际项目需求进行适当调整。在生产环境部署前，请确保进行充分的测试。