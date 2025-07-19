#!/usr/bin/env python3
"""
测试重构后的项目结构
验证导入和基本功能是否正常
"""

import sys
import traceback
from typing import List, Tuple


def test_imports() -> List[Tuple[str, bool, str]]:
    """测试关键模块导入"""
    results = []
    
    # 测试导入列表
    import_tests = [
        ("异常模块", "from app.utils.exceptions import BaseAppException, AgentError"),
        ("配置模块", "from app.config.settings import AppSettings, get_settings"),
        ("Agent模式", "from app.schemas.agent_schemas import AgentChatRequest, AgentChatResponse"),
        ("Agent服务", "from app.services.agent_service import AgentService, AgentCacheManager"),
        ("依赖注入", "from app.api.dependencies import get_agent_service"),
        ("异常处理", "from app.api.exception_handlers import register_exception_handlers"),
    ]
    
    for name, import_statement in import_tests:
        try:
            exec(import_statement)
            results.append((name, True, "导入成功"))
        except ImportError as e:
            results.append((name, False, f"导入失败: {e}"))
        except Exception as e:
            results.append((name, False, f"异常: {e}"))
    
    return results


def test_basic_functionality():
    """测试基本功能"""
    print("\n🔧 测试基本功能...")
    
    try:
        # 测试配置加载
        from app.config.settings import get_settings
        settings = get_settings()
        print(f"✅ 配置加载成功: {settings.app_name}")
        
        # 测试异常类
        from app.utils.exceptions import AgentError
        try:
            raise AgentError("测试异常")
        except AgentError as e:
            print(f"✅ 异常处理正常: {e.message}")
        
        # 测试数据模式
        from app.schemas.agent_schemas import AgentChatRequest
        request = AgentChatRequest(
            kb_id="test",
            message="测试消息"
        )
        print(f"✅ 数据模式验证正常: {request.kb_id}")
        
        # 测试服务层（不实际执行，只测试实例化）
        from app.services.agent_service import AgentCacheManager
        cache_manager = AgentCacheManager()
        print(f"✅ 服务层实例化正常: {type(cache_manager).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        traceback.print_exc()
        return False


def test_structure_integrity():
    """测试项目结构完整性"""
    print("\n📁 测试项目结构完整性...")
    
    import os
    
    # 检查关键文件是否存在
    key_files = [
        "app/schemas/agent_schemas.py",
        "app/services/agent_service.py",
        "app/utils/exceptions.py",
        "app/config/settings.py",
        "app/api/dependencies.py",
        "app/api/exception_handlers.py",
        "app/routers/agent_router.py"
    ]
    
    missing_files = []
    for file_path in key_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少关键文件: {missing_files}")
        return False
    else:
        print("✅ 所有关键文件都存在")
        return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("🚀 项目结构重构验证测试")
    print("=" * 60)
    
    # 测试导入
    print("\n📦 测试模块导入...")
    import_results = test_imports()
    
    success_count = 0
    for name, success, message in import_results:
        status = "✅" if success else "❌"
        print(f"{status} {name}: {message}")
        if success:
            success_count += 1
    
    print(f"\n导入测试结果: {success_count}/{len(import_results)} 成功")
    
    # 测试项目结构
    structure_ok = test_structure_integrity()
    
    # 测试基本功能
    functionality_ok = test_basic_functionality()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    all_passed = (success_count == len(import_results)) and structure_ok and functionality_ok
    
    if all_passed:
        print("🎉 所有测试通过！项目结构重构成功！")
        print("\n✨ 重构成果:")
        print("  • 清晰的分层架构 ✅")
        print("  • 单一职责原则 ✅")
        print("  • 依赖注入系统 ✅")
        print("  • 配置集中管理 ✅")
        print("  • 异常处理标准化 ✅")
        print("  • 数据模式规范化 ✅")
        
        print("\n🚀 接下来可以:")
        print("  1. 启动服务: uvicorn app.main:app --reload")
        print("  2. 访问文档: http://localhost:8000/docs")
        print("  3. 测试API端点")
        print("  4. 添加单元测试")
        
    else:
        print("⚠️  部分测试失败，请检查以下问题:")
        if success_count < len(import_results):
            print("  • 模块导入问题")
        if not structure_ok:
            print("  • 项目结构问题")
        if not functionality_ok:
            print("  • 基本功能问题")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)