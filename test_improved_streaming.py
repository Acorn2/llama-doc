#!/usr/bin/env python3

"""
测试改进后的流式打字机效果
验证随机字符数输出和真正的流式处理
"""

import asyncio
import json
import time
from app.utils.streaming_utils import (
    TypewriterStreamer, 
    StreamingPresets,
    RealTimeStreamer,
    StreamingResponseBuilder
)


async def test_random_typewriter():
    """测试随机字符数的打字机效果"""
    print("=== 测试随机字符数打字机效果 ===")
    
    text = "这是一个测试随机字符数输出的例子。它会随机输出1-3个字符，让打字效果更加自然。你会看到有时输出一个字，有时输出两三个字。"
    
    # 使用自然打字预设
    typewriter = TypewriterStreamer(**StreamingPresets.NATURAL)
    
    print("开始随机输出:")
    start_time = time.time()
    
    async for chunk in typewriter.stream_text(text):
        if chunk.type.value == "content":
            print(f"[{len(chunk.content)}字] {chunk.content}", end='', flush=True)
            # 显示每次输出的字符数
        elif chunk.type.value == "final":
            print(f"\n\n随机输出完成，耗时: {time.time() - start_time:.2f}秒")


async def test_different_natural_presets():
    """测试不同的自然预设"""
    print("\n=== 测试不同自然预设 ===")
    
    text = "人工智能技术正在快速发展，为各行各业带来了革命性的变化。"
    
    presets = {
        "快速自然": StreamingPresets.FAST_NATURAL,
        "标准自然": StreamingPresets.NATURAL,
        "慢速自然": StreamingPresets.SLOW
    }
    
    for preset_name, preset_config in presets.items():
        print(f"\n--- {preset_name} ---")
        typewriter = TypewriterStreamer(**preset_config)
        
        start_time = time.time()
        output_chunks = []
        
        async for chunk in typewriter.stream_text(text):
            if chunk.type.value == "content":
                output_chunks.append(len(chunk.content))
                print(chunk.content, end='', flush=True)
            elif chunk.type.value == "final":
                avg_chunk_size = sum(output_chunks) / len(output_chunks) if output_chunks else 0
                print(f" [耗时: {time.time() - start_time:.2f}s, 平均块大小: {avg_chunk_size:.1f}字]")


async def simulate_llm_stream():
    """模拟LLM的流式输出"""
    text = "根据您的问题，我来为您详细解答。首先，这个问题涉及到多个方面的考虑。其次，我们需要从技术角度来分析。最后，我会给出具体的建议和解决方案。"
    
    # 模拟LLM按句子输出
    import re
    sentences = re.split(r'([。！？])', text)
    
    for i in range(0, len(sentences), 2):
        if i + 1 < len(sentences):
            chunk = sentences[i] + sentences[i + 1]
        else:
            chunk = sentences[i]
        
        if chunk.strip():
            yield {
                "chunk": chunk,
                "is_final": False
            }
            await asyncio.sleep(0.5)  # 模拟LLM生成延迟
    
    # 最终块
    yield {
        "chunk": "",
        "is_final": True,
        "sources": ["测试来源1", "测试来源2"],
        "processing_time": 2.5
    }


async def test_realtime_streaming():
    """测试真正的实时流式处理"""
    print("\n=== 测试真正的实时流式处理 ===")
    
    conversation_id = "test-conv-realtime"
    
    # 创建实时流式处理器
    typewriter = TypewriterStreamer(**StreamingPresets.NATURAL)
    realtime_streamer = RealTimeStreamer(typewriter)
    
    print("模拟LLM实时输出:")
    start_time = time.time()
    
    # 模拟LLM流式生成器
    llm_stream = simulate_llm_stream()
    
    async for sse_data in realtime_streamer.process_llm_stream(
        llm_stream, conversation_id, {"test": True}
    ):
        # 解析SSE数据
        if sse_data.startswith("data: "):
            json_data = sse_data[6:].strip()
            try:
                chunk_data = json.loads(json_data)
                if chunk_data["type"] == "content":
                    print(chunk_data["content"], end='', flush=True)
                elif chunk_data["type"] == "final":
                    print(f"\n\n实时流式完成，总耗时: {time.time() - start_time:.2f}秒")
                    print(f"元数据: {chunk_data['metadata']}")
                elif chunk_data["type"] == "metadata":
                    print(f"开始处理，元数据: {chunk_data['metadata']}")
            except json.JSONDecodeError:
                pass


async def test_comparison():
    """对比测试：固定vs随机输出"""
    print("\n=== 对比测试：固定 vs 随机输出 ===")
    
    text = "这是一个对比测试，展示固定字符输出和随机字符输出的区别。"
    
    # 固定输出
    print("\n固定输出（每次1个字符）:")
    fixed_config = {
        "chunk_size": 1,
        "delay": 0.05,
        "enable_random": False,
        "enable_smart_delay": False
    }
    typewriter_fixed = TypewriterStreamer(**fixed_config)
    
    start_time = time.time()
    async for chunk in typewriter_fixed.stream_text(text):
        if chunk.type.value == "content":
            print(chunk.content, end='', flush=True)
        elif chunk.type.value == "final":
            print(f" [固定输出耗时: {time.time() - start_time:.2f}s]")
    
    # 随机输出
    print("\n随机输出（1-3个字符）:")
    typewriter_random = TypewriterStreamer(**StreamingPresets.NATURAL)
    
    start_time = time.time()
    chunk_sizes = []
    async for chunk in typewriter_random.stream_text(text):
        if chunk.type.value == "content":
            chunk_sizes.append(len(chunk.content))
            print(chunk.content, end='', flush=True)
        elif chunk.type.value == "final":
            avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
            print(f" [随机输出耗时: {time.time() - start_time:.2f}s, 平均: {avg_size:.1f}字/次]")


async def test_smart_delay():
    """测试智能延迟效果"""
    print("\n=== 测试智能延迟效果 ===")
    
    text = "这是第一句话。这是第二句话！这是第三句话？\n\n这是新的段落，用来测试段落延迟。"
    
    typewriter = TypewriterStreamer(**StreamingPresets.NATURAL)
    
    print("智能延迟输出（注意句子和段落后的停顿）:")
    start_time = time.time()
    
    async for chunk in typewriter.stream_text(text):
        if chunk.type.value == "content":
            print(chunk.content, end='', flush=True)
        elif chunk.type.value == "final":
            print(f"\n\n智能延迟完成，耗时: {time.time() - start_time:.2f}秒")


async def main():
    """主测试函数"""
    print("🎯 改进后的流式打字机效果测试")
    print("=" * 60)
    
    # 运行所有测试
    await test_random_typewriter()
    await test_different_natural_presets()
    await test_realtime_streaming()
    await test_comparison()
    await test_smart_delay()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("\n🎉 改进效果:")
    print("- ✨ 支持随机字符数输出（1-3个字符）")
    print("- ⚡ 真正的实时流式处理")
    print("- 🧠 智能延迟调整")
    print("- 🎨 更自然的打字效果")
    print("- 🔧 多种预设配置")


if __name__ == "__main__":
    asyncio.run(main())