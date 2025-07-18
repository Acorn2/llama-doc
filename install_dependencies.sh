#!/bin/bash

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 先卸载可能冲突的包
echo "卸载可能冲突的包..."
pip uninstall -y pydantic

# 安装基本依赖
echo "安装项目依赖..."
pip install -r requirements.txt

# 确保安装了正确版本的pydantic
echo "确保安装了正确版本的pydantic..."
pip install pydantic==1.10.8
pip install pydantic-settings>=2.0.0

# 特别安装llama-index相关包
echo "安装llama-index相关包..."
pip install llama-index-core>=0.10.0
pip install llama-index-readers-file>=0.1.4

echo "依赖安装完成！" 