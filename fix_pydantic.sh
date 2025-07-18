#!/bin/bash

echo "修复pydantic版本冲突问题..."

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 卸载当前版本的pydantic
echo "卸载当前版本的pydantic..."
pip uninstall -y pydantic

# 安装兼容版本的pydantic
echo "安装兼容版本的pydantic..."
pip install pydantic==1.10.8
pip install pydantic-settings>=2.0.0

# 安装llama-index相关包
echo "安装llama-index相关包..."
pip install llama-index-core>=0.10.0
pip install llama-index-readers-file>=0.1.4

echo "修复完成！请尝试重新启动应用。" 