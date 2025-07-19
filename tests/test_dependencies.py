#!/usr/bin/env python3
"""
测试依赖修复是否成功
"""

import sys
import traceback

def test_imports():
    """测试关键导入是否正常"""
    print("开始测试依赖导入...")
    
    tests = [
        ("Pydantic v2", lambda: __import__('pydantic')),
        ("LangChain Core", lambda: __import__('langchain_core')),
        ("LangChain Community", lambda: __import__('langchain_community')),
        ("LangChain OpenAI", lambda: __import__('langchain_openai')),
        ("LangChain Main", lambda: __import__('langchain')),
        ("FastAPI", lambda: __import__('fastapi')),
        ("Qdrant Client", lambda: __import__('qdrant_client')),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for name, import_func in tests:
        try:
            import_func()
            print(f"✅ {name}: 导入成功")
            success_count += 1
        except ImportError as e:
            print(f"❌ {name}: 导入失败 - {e}")
        except Exception as e:
            print(f"⚠️  {name}: 导入异常 - {e}")
    
    print(f"\n测试结果: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("🎉 所有依赖导入测试通过！")
        return True
    else:
        print("⚠️  部分依赖导入失败，请检查安装")
        return False

def test_langchain_api():
    """测试LangChain API兼容性"""
    print("\n开始测试LangChain API兼容性...")
    
    try:
        # 测试新的导入路径
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.embeddings import Embeddings
        from langchain_core.documents import Document
        
        print("✅ LangChain Core API: 导入成功")
        
        # 测试基本功能
        prompt = ChatPromptTemplate.from_template("Hello {name}")
        parser = StrOutputParser()
        
        print("✅ LangChain 基本功能: 测试通过")
        return True
        
    except Exception as e:
        print(f"❌ LangChain API测试失败: {e}")
        traceback.print_exc()
        return False

def test_pydantic_v2():
    """测试Pydantic v2兼容性"""
    print("\n开始测试Pydantic v2兼容性...")
    
    try:
        from pydantic import BaseModel, Field
        
        class TestModel(BaseModel):
            name: str = Field(..., description="测试字段")
            value: int = Field(default=0, description="数值字段")
        
        # 测试模型创建
        model = TestModel(name="test", value=42)
        
        # 测试序列化
        data = model.model_dump()
        
        print("✅ Pydantic v2: 基本功能测试通过")
        print(f"   模型数据: {data}")
        return True
        
    except Exception as e:
        print(f"❌ Pydantic v2测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("依赖修复验证测试")
    print("=" * 50)
    
    all_passed = True
    
    # 测试导入
    if not test_imports():
        all_passed = False
    
    # 测试LangChain API
    if not test_langchain_api():
        all_passed = False
    
    # 测试Pydantic v2
    if not test_pydantic_v2():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！依赖修复成功！")
        print("\n接下来可以:")
        print("1. 运行 pip install -r requirements.txt 安装依赖")
        print("2. 启动服务测试Agent功能")
        print("3. 访问 /docs 查看新的Agent API")
    else:
        print("⚠️  部分测试失败，请检查依赖配置")
        print("\n建议:")
        print("1. 检查 requirements.txt 中的版本配置")
        print("2. 重新安装依赖: pip install -r requirements.txt")
        print("3. 检查Python环境是否正确")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)