#!/usr/bin/env python3
"""
测试向量同步服务
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from app.services.vector_sync_service import VectorSyncProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_vector_sync_service():
    """测试向量同步服务"""
    logger.info("🚀 开始测试向量同步服务")
    
    try:
        # 创建向量同步处理器实例
        processor = VectorSyncProcessor()
        
        # 测试数据库连接和基本功能
        logger.info("测试数据库连接...")
        await processor.process_pending_vector_sync()
        logger.info("✅ 数据库连接测试成功")
        
        # 测试获取同步状态
        logger.info("测试获取同步状态...")
        from app.database import get_db_session
        db = get_db_session()
        try:
            stats = processor.get_sync_status(db)
            logger.info(f"✅ 同步状态获取成功: {stats}")
        finally:
            db.close()
        
        logger.info("🎉 向量同步服务测试完成！")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        raise

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("向量同步服务测试")
    logger.info("=" * 60)
    
    try:
        asyncio.run(test_vector_sync_service())
        logger.info("\n✅ 所有测试通过！")
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()