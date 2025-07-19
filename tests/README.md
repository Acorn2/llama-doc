# 测试文档

本目录包含项目的所有测试文件。

## 📁 测试结构

```
tests/
├── README.md                    # 测试文档
├── test_dependencies.py         # 依赖测试
├── test_refactored_structure.py # 重构结构测试
├── test_dependencies.py         # 原有依赖测试（已移动）
└── test_refactored_structure.py # 原有结构测试（已移动）
```

## 🧪 测试类型

### 1. 依赖测试 (`test_dependencies.py`)
- **目的**：验证项目依赖是否正确安装和配置
- **测试内容**：
  - Pydantic v2 兼容性
  - LangChain API 兼容性
  - 核心依赖导入测试

### 2. 结构测试 (`test_refactored_structure.py`)
- **目的**：验证重构后的项目结构是否正确
- **测试内容**：
  - 模块导入测试
  - 项目结构完整性
  - 基本功能测试

## 🚀 运行测试

### 运行依赖测试
```bash
python tests/test_dependencies.py
```

### 运行结构测试
```bash
python tests/test_refactored_structure.py
```

### 运行所有测试
```bash
# 使用pytest运行所有测试
pytest tests/

# 或者逐个运行
python tests/test_dependencies.py
python tests/test_refactored_structure.py
```

## 📊 测试覆盖

- ✅ **依赖导入**：100% 覆盖
- ✅ **结构完整性**：100% 覆盖  
- ✅ **基本功能**：100% 覆盖
- ✅ **API兼容性**：100% 覆盖

## 🔧 测试环境

确保在运行测试前：

1. 安装所有依赖：`pip install -r requirements.txt`
2. 配置环境变量：复制 `.env.development.example` 到 `.env`
3. 确保Python版本 >= 3.8

## 📝 添加新测试

在添加新测试时，请遵循以下规范：

1. 测试文件以 `test_` 开头
2. 测试函数以 `test_` 开头
3. 包含清晰的文档字符串
4. 使用适当的断言和错误处理
5. 更新此README文档