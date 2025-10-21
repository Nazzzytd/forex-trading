# 使用示例
def main():
    # 初始化组件
    coordinator = EnhancedTradingCoordinator(config)
    rag_retriever = ForexRAGRetriever()
    react_agent = ReActForexAgent(coordinator, rag_retriever)
    
    # 复杂问题解答
    question = "为什么今天USD/JPY大涨？"
    
    initial_state = {
        "question": question,
        "reasoning_steps": [],
        "retrieved_knowledge": [],
        "economic_data": {},
        "technical_analysis": {},
        "news_analysis": {},
        "final_answer": ""
    }
    
    # 执行ReAct推理链
    result = react_agent.graph.invoke(initial_state)
    
    print("推理过程:", result["reasoning_steps"])
    print("最终答案:", result["final_answer"])

# 预期输出推理链：
# 1. 提取实体：识别USD/JPY、今天、大涨等关键信息
# 2. 检索知识：查找历史上USD/JPY大涨的类似案例和分析框架
# 3. 分析经济：检查今日美国/日本经济数据发布、央行言论
# 4. 分析技术：查看价格走势、关键技术位突破
# 5. 综合回答：基于所有信息生成专业分析报告

# UltraRAG能够提供：
# knowledge_context = {
#     "historical_cases": "类似历史行情的分析",
#     "economic_theory": "利率平价理论、购买力平价等",
#     "market_mechanisms": "央行干预、套息交易等机制",
#     "analytical_frameworks": "专业分析方法和模型"
# }