#!/usr/bin/env python3
"""
测试语法修复是否有效
"""
import ast
import sys

def check_syntax(file_path):
    """检查文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # 解析AST
        ast.parse(source)
        print(f"✅ {file_path} - 语法正确")
        return True
    except SyntaxError as e:
        print(f"❌ {file_path} - 语法错误: {e}")
        print(f"   行 {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"⚠️ {file_path} - 其他错误: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 检查用户活动记录功能相关文件的语法...")
    
    files_to_check = [
        "app/database.py",
        "app/schemas.py",
        "app/services/activity_service.py",
        "app/utils/activity_logger.py",
        "app/routers/user_routes.py",
        "app/routers/document_routes.py",
        "app/routers/knowledge_base_routes.py",
        "app/routers/agent_router.py",
        "app/routers/conversation_routes.py"
    ]
    
    all_passed = True
    
    for file_path in files_to_check:
        if not check_syntax(file_path):
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 所有文件语法检查通过！")
        print("现在可以尝试重启服务了。")
    else:
        print("⚠️ 部分文件存在语法错误，请修复后再重启服务。")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)