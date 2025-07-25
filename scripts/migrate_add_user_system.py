#!/usr/bin/env python3
"""
数据库迁移脚本：添加用户系统

这个脚本将：
1. 创建users表
2. 为现有表添加user_id字段
3. 创建默认系统用户
4. 将现有数据关联到系统用户
"""

import sys
import os
import uuid
import hashlib
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import text, inspect
from app.database import engine, get_db_session, Base, User
from app.services.user_service import user_service

def create_default_system_user(db):
    """创建默认系统用户"""
    system_user_id = "system-user-" + str(uuid.uuid4())
    
    # 检查是否已存在系统用户
    existing_user = db.query(User).filter(User.email == "system@admin.com").first()
    if existing_user:
        print(f"系统用户已存在: {existing_user.id}")
        return existing_user.id
    
    # 创建系统用户
    system_user = User(
        id=system_user_id,
        username="system",
        email="system@admin.com",
        phone="00000000000",
        password_hash=hashlib.sha256("system123456".encode()).hexdigest(),
        full_name="系统管理员",
        is_active=True,
        is_superuser=True
    )
    
    db.add(system_user)
    db.commit()
    db.refresh(system_user)
    
    print(f"已创建系统用户: {system_user_id}")
    return system_user_id

def add_user_id_columns(db):
    """为现有表添加user_id字段"""
    inspector = inspect(engine)
    
    # 需要添加user_id字段的表
    tables_to_update = [
        ("documents", "用户ID添加到文档表"),
        ("query_history", "用户ID添加到查询历史表"),
        ("knowledge_bases", "用户ID添加到知识库表"),
        ("conversations", "用户ID添加到对话表")
    ]
    
    for table_name, description in tables_to_update:
        if not inspector.has_table(table_name):
            print(f"表 {table_name} 不存在，跳过")
            continue
            
        # 检查user_id字段是否已存在
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        if 'user_id' in columns:
            print(f"表 {table_name} 已有user_id字段，跳过")
            continue
        
        # 添加user_id字段
        try:
            if engine.dialect.name == 'postgresql':
                db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id VARCHAR(255)"))
            elif engine.dialect.name == 'sqlite':
                db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id VARCHAR(255)"))
            else:
                print(f"不支持的数据库类型: {engine.dialect.name}")
                continue
                
            print(f"✅ {description}")
        except Exception as e:
            print(f"❌ 添加 {table_name}.user_id 字段失败: {e}")
            continue

def update_existing_data(db, system_user_id):
    """将现有数据关联到系统用户"""
    
    # 更新documents表
    try:
        result = db.execute(text("UPDATE documents SET user_id = :user_id WHERE user_id IS NULL"), 
                          {"user_id": system_user_id})
        print(f"✅ 更新了 {result.rowcount} 条文档记录")
    except Exception as e:
        print(f"❌ 更新documents表失败: {e}")
    
    # 更新query_history表
    try:
        result = db.execute(text("UPDATE query_history SET user_id = :user_id WHERE user_id IS NULL"), 
                          {"user_id": system_user_id})
        print(f"✅ 更新了 {result.rowcount} 条查询历史记录")
    except Exception as e:
        print(f"❌ 更新query_history表失败: {e}")
    
    # 更新knowledge_bases表
    try:
        result = db.execute(text("UPDATE knowledge_bases SET user_id = :user_id WHERE user_id IS NULL"), 
                          {"user_id": system_user_id})
        print(f"✅ 更新了 {result.rowcount} 条知识库记录")
    except Exception as e:
        print(f"❌ 更新knowledge_bases表失败: {e}")
    
    # 更新conversations表
    try:
        result = db.execute(text("UPDATE conversations SET user_id = :user_id WHERE user_id IS NULL"), 
                          {"user_id": system_user_id})
        print(f"✅ 更新了 {result.rowcount} 条对话记录")
    except Exception as e:
        print(f"❌ 更新conversations表失败: {e}")

def add_constraints(db):
    """添加外键约束（仅适用于PostgreSQL）"""
    if engine.dialect.name != 'postgresql':
        print("SQLite数据库，跳过外键约束添加")
        return
    
    constraints = [
        ("documents", "fk_documents_user_id", "user_id", "users(id)"),
        ("query_history", "fk_query_history_user_id", "user_id", "users(id)"),
        ("knowledge_bases", "fk_knowledge_bases_user_id", "user_id", "users(id)"),
        ("conversations", "fk_conversations_user_id", "user_id", "users(id)")
    ]
    
    for table_name, constraint_name, column, reference in constraints:
        try:
            # 首先设置字段为NOT NULL
            db.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN {column} SET NOT NULL"))
            
            # 然后添加外键约束
            db.execute(text(f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} FOREIGN KEY ({column}) REFERENCES {reference}"))
            print(f"✅ 为 {table_name} 添加外键约束")
        except Exception as e:
            print(f"❌ 为 {table_name} 添加外键约束失败: {e}")

def main():
    """主迁移函数"""
    print("🚀 开始数据库迁移：添加用户系统")
    
    # 获取数据库会话
    db = get_db_session()
    
    try:
        # 1. 创建所有表（包括新的users表）
        print("\n1️⃣ 创建数据库表...")
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建完成")
        
        # 2. 创建默认系统用户
        print("\n2️⃣ 创建默认系统用户...")
        system_user_id = create_default_system_user(db)
        
        # 3. 为现有表添加user_id字段
        print("\n3️⃣ 为现有表添加user_id字段...")
        add_user_id_columns(db)
        db.commit()
        
        # 4. 将现有数据关联到系统用户
        print("\n4️⃣ 更新现有数据...")
        update_existing_data(db, system_user_id)
        db.commit()
        
        # 5. 添加外键约束（仅PostgreSQL）
        print("\n5️⃣ 添加外键约束...")
        add_constraints(db)
        db.commit()
        
        print("\n🎉 数据库迁移完成!")
        print("\n📝 迁移摘要:")
        print(f"   - 创建了系统用户: {system_user_id}")
        print("   - 为相关表添加了user_id字段")
        print("   - 将现有数据关联到系统用户")
        print("   - 添加了必要的约束")
        
        print("\n🔑 默认系统用户信息:")
        print("   - 邮箱: system@admin.com")
        print("   - 密码: system123456")
        print("   - 权限: 超级用户")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main() 