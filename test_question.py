#!/usr/bin/env python3
"""
测试脚本 - 用于验证RAG系统功能
"""

from query_rag import ForexRAGQuerySystem

def test_forex_rag():
    """测试外汇交易RAG系统"""
    
    # 初始化系统
    query_system = ForexRAGQuerySystem()
    
    if not query_system.initialize_system():
        print("系统初始化失败")
        return
    
    # 测试问题列表
    test_questions = [
        "什么是锤子线形态？它有什么市场意义？",
        "请解释看涨吞没形态和看跌吞没形态的区别",
        "在蜡烛图技术中，十字星代表什么含义？",
        "什么是乌云盖顶形态？如何识别？",
        "请说明早晨之星和黄昏之星的区别",
    ]
    
    print("开始测试外汇交易RAG系统...")
    print("=" * 60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n测试问题 {i}: {question}")
        result = query_system.ask_question(question)
        response = query_system.format_response(result)
        print(response)
        print("=" * 60)

if __name__ == "__main__":
    test_forex_rag()