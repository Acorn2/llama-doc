#!/usr/bin/env python3
"""
测试文档同步流程
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from app.database import get_db_session, Document, KnowledgeBaseDocument
from sqlalchemy import and_

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_document_sync_flow():
    """测试文档同步流程"""
    logger.info("🚀 开始测试文档同步流程")
    
    db = get_db_session()
    try:
        # 1. 查看所有文档的状态
        logger.info("\n📋 当前文档状态:")
        documents = db.query(Document).all()
        for doc in documents:
            logger.info(f"  文档 {doc.id[:8]}... - status: {doc.status}, sync_status: {doc.sync_status}")
        
        # 2. 查看知识库文档关联的同步状态
        logger.info("\n📋 知识库文档关联同步状态:")
        kb_docs = db.query(KnowledgeBaseDocument).all()
        for kb_doc in kb_docs:
            logger.info(f"  KB {kb_doc.kb_id[:8]}... - 文档 {kb_doc.document_id[:8]}... - vector_sync_status: {kb_doc.vector_sync_status}")
        
        # 3. 查找可同步的文档
        logger.info("\n🔍 查找可同步的文档:")
        syncable_records = db.query(KnowledgeBaseDocument).join(
            Document, KnowledgeBaseDocument.document_id == Document.id
        ).filter(
            and_(
                KnowledgeBaseDocument.vector_sync_status == "pending",
                Document.status == "completed",
                Document.sync_status == "available"
            )
        ).all()
        
        logger.info(f"  找到 {len(syncable_records)} 个可同步的记录")
        for record in syncable_records:
            logger.info(f"    KB {record.kb_id[:8]}... - 文档 {record.document_id[:8]}...")
        
        # 4. 查找已完成但未关联到知识库的文档
        logger.info("\n📄 已完成但可添加到知识库的文档:")
        available_docs = db.query(Document).filter(
            and_(
                Document.status == "completed",
                Document.sync_status == "available"
            )
        ).all()
        
        logger.info(f"  找到 {len(available_docs)} 个可添加到知识库的文档")
        for doc in available_docs:
            logger.info(f"    文档 {doc.id[:8]}... - {doc.filename}")
        
        logger.info("\n🎉 文档同步流程测试完成！")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        raise
    finally:
        db.close()

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("文档同步流程测试")
    logger.info("=" * 60)
    
    try:
        test_document_sync_flow()
        logger.info("\n✅ 所有测试通过！")
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()