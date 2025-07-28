#!/usr/bin/env python3
"""
创建用户活动记录表的迁移脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from app.database import create_tables, get_db_session, engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_user_activities_table():
    """创建用户活动记录表"""
    try:
        logger.info("开始创建用户活动记录表...")
        
        # 创建所有表（包括新的user_activities表）
        create_tables()
        
        # 验证表是否创建成功
        db = get_db_session()
        try:
            result = db.execute(text("SELECT COUNT(*) FROM user_activities"))
            logger.info("用户活动记录表创建成功，当前记录数: 0")
        except Exception as e:
            logger.error(f"验证表创建失败: {str(e)}")
            raise
        finally:
            db.close()
        
        logger.info("用户活动记录表创建完成！")
        
    except Exception as e:
        logger.error(f"创建用户活动记录表失败: {str(e)}")
        raise

if __name__ == "__main__":
    create_user_activities_table()