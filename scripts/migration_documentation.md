# 命名统一迁移文档

## 迁移概述
本脚本将系统中所有的 `product_id` 统一为 `project_id`，解决命名不一致问题。

## 数据库变更
未发现需要更新的表结构。

## 代码文件变更
共更新了 4 个文件：
- `routes\product_legacy.py`
- `templates\products.html`
- `templates\products_add.html`
- `数据库脚本\修复数据库.py`

## 注意事项
1. 数据库已备份到 `instance/database_backup.db`
2. 迁移后请彻底测试系统功能，确保所有功能正常工作
3. 如遇问题，可以恢复备份的数据库并回滚代码更改
