#!/usr/bin/env python3
"""
数据库迁移脚本：为kb_documents表添加向量同步状态字段
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import get_db, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_vector_sync_columns():
    """添加向量同步相关字段"""
    try:
        with engine.connect() as conn:
            # 检查字段是否已存在
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'kb_documents' 
                AND column_name IN ('vector_sync_status', 'vector_sync_time', 'vector_sync_error')
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            
            if 'vector_sync_status' not in existing_columns:
                logger.info("添加 vector_sync_status 字段...")
                conn.execute(text("""
                    ALTER TABLE kb_documents 
                    ADD COLUMN vector_sync_status VARCHAR DEFAULT 'pending' NOT NULL
                """))
                
                # 为现有记录设置为completed状态（假设它们已经同步过）
                conn.execute(text("""
                    UPDATE kb_documents 
                    SET vector_sync_status = 'completed' 
                    WHERE vector_sync_status = 'pending'
                """))
                logger.info("✅ vector_sync_status 字段添加成功")
            else:
                logger.info("vector_sync_status 字段已存在")
            
            if 'vector_sync_time' not in existing_columns:
                logger.info("添加 vector_sync_time 字段...")
                conn.execute(text("""
                    ALTER TABLE kb_documents 
                    ADD COLUMN vector_sync_time TIMESTAMP WITH TIME ZONE
                """))
                logger.info("✅ vector_sync_time 字段添加成功")
            else:
                logger.info("vector_sync_time 字段已存在")
            
            if 'vector_sync_error' not in existing_columns:
                logger.info("添加 vector_sync_error 字段...")
                conn.execute(text("""
                    ALTER TABLE kb_documents 
                    ADD COLUMN vector_sync_error TEXT
                """))
                logger.info("✅ vector_sync_error 字段添加成功")
            else:
                logger.info("vector_sync_error 字段已存在")
            
            # 添加索引
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_vector_sync_status 
                    ON kb_documents(vector_sync_status)
                """))
                logger.info("✅ 向量同步状态索引添加成功")
            except Exception as e:
                logger.warning(f"索引可能已存在: {e}")
            
            conn.commit()
            logger.info("🎉 数据库迁移完成！")
            
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise

def main():
    """主函数"""
    logger.info("🚀 开始数据库迁移：添加向量同步字段")
    logger.info("=" * 60)
    
    try:
        add_vector_sync_columns()
        logger.info("=" * 60)
        logger.info("✅ 迁移成功完成！")
        
        logger.info("\n📝 迁移说明:")
        logger.info("1. 为 kb_documents 表添加了向量同步状态字段")
        logger.info("2. 现有记录被标记为 'completed' 状态")
        logger.info("3. 新的文档关联将使用 'pending' 状态，由定时任务处理")
        logger.info("4. 添加了相应的数据库索引")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()