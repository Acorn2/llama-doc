#!/usr/bin/env python3
"""
数据库迁移脚本：为documents表添加sync_status字段
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_document_sync_status_column():
    """为documents表添加sync_status字段"""
    try:
        with engine.connect() as conn:
            # 检查字段是否已存在
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name = 'sync_status'
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            
            if 'sync_status' not in existing_columns:
                logger.info("添加 sync_status 字段...")
                conn.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN sync_status VARCHAR DEFAULT 'available' NOT NULL
                """))
                
                # 为已完成的文档设置为available状态，其他保持默认
                conn.execute(text("""
                    UPDATE documents 
                    SET sync_status = 'available' 
                    WHERE status = 'completed'
                """))
                
                # 为未完成的文档设置为unavailable状态
                conn.execute(text("""
                    UPDATE documents 
                    SET sync_status = 'unavailable' 
                    WHERE status != 'completed'
                """))
                
                logger.info("✅ sync_status 字段添加成功")
            else:
                logger.info("sync_status 字段已存在")
            
            # 添加索引
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_sync_status 
                    ON documents(sync_status)
                """))
                logger.info("✅ sync_status 索引添加成功")
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_status_sync_status 
                    ON documents(status, sync_status)
                """))
                logger.info("✅ status_sync_status 复合索引添加成功")
            except Exception as e:
                logger.warning(f"索引可能已存在: {e}")
            
            conn.commit()
            logger.info("🎉 数据库迁移完成！")
            
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise

def main():
    """主函数"""
    logger.info("🚀 开始数据库迁移：添加文档同步状态字段")
    logger.info("=" * 60)
    
    try:
        add_document_sync_status_column()
        logger.info("=" * 60)
        logger.info("✅ 迁移成功完成！")
        
        logger.info("\n📝 迁移说明:")
        logger.info("1. 为 documents 表添加了 sync_status 字段")
        logger.info("2. 已完成的文档被标记为 'available' 状态")
        logger.info("3. 未完成的文档被标记为 'unavailable' 状态")
        logger.info("4. 添加了相应的数据库索引")
        logger.info("5. sync_status 状态说明:")
        logger.info("   - available: 可同步到知识库")
        logger.info("   - unavailable: 不可同步（文档未完成处理）")
        logger.info("   - syncing: 正在同步中")
        logger.info("   - synced: 已同步")
        logger.info("   - sync_failed: 同步失败")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()