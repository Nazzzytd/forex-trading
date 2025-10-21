# react_forex_agent.py
from langgraph import StateGraph, END
from typing import TypedDict, List, Annotated
import operator

class ForexState(TypedDict):
    question: str
    currency_pair: str
    reasoning_steps: List[str]
    retrieved_knowledge: List[Dict]
    economic_data: Dict
    technical_analysis: Dict
    news_analysis: Dict
    final_answer: str
    next_action: str

class ReActForexAgent:
    def __init__(self, coordinator, rag_retriever):
        self.coordinator = coordinator
        self.rag = rag_retriever
        self.graph = self._build_react_graph()
    
    def _build_react_graph(self):
        """构建ReAct推理图"""
        workflow = StateGraph(ForexState)
        
        # 定义节点
        workflow.add_node("extract_entities", self.extract_entities)
        workflow.add_node("retrieve_background", self.retrieve_background_knowledge)
        workflow.add_node("analyze_economic", self.analyze_economic_factors)
        workflow.add_node("analyze_technical", self.analyze_technical_factors)
        workflow.add_node("synthesize_answer", self.synthesize_final_answer)
        
        # 定义边
        workflow.set_entry_point("extract_entities")
        workflow.add_edge("extract_entities", "retrieve_background")
        workflow.add_edge("retrieve_background", "analyze_economic")
        workflow.add_edge("analyze_economic", "analyze_technical")
        workflow.add_edge("analyze_technical", "synthesize_answer")
        workflow.add_edge("synthesize_answer", END)
        
        return workflow.compile()
    
    def extract_entities(self, state: ForexState) -> ForexState:
        """提取问题中的关键实体"""
        question = state["question"]
        
        # 使用RAG检索实体识别的最佳实践
        entity_recognition_knowledge = self.rag.query_forex_knowledge(
            "如何从外汇问题中提取关键实体和货币对"
        )
        
        # 实现实体提取逻辑
        currency_pair = self._extract_currency_pair(question)
        time_frame = self._extract_time_frame(question)
        event_type = self._extract_event_type(question)
        
        state.update({
            "currency_pair": currency_pair,
            "time_frame": time_frame,
            "event_type": event_type,
            "reasoning_steps": ["提取了问题中的关键实体信息"]
        })
        return state
    
    def retrieve_background_knowledge(self, state: ForexState) -> ForexState:
        """检索相关背景知识"""
        question = state["question"]
        currency_pair = state["currency_pair"]
        
        # 使用UltraRAG检索相关知识
        knowledge_results = self.rag.query_forex_knowledge(
            query=question,
            currency_pair=currency_pair
        )
        
        # 检索特定类型的知识
        specific_queries = [
            f"{currency_pair} 大涨原因分析框架",
            "央行政策对外汇市场影响机制",
            "经济数据发布对汇率影响模式",
            "技术面突破与基本面结合分析方法"
        ]
        
        all_knowledge = []
        for query in specific_queries:
            results = self.rag.query_forex_knowledge(query, currency_pair)
            all_knowledge.extend(results["relevant_documents"])
        
        state.update({
            "retrieved_knowledge": all_knowledge,
            "reasoning_steps": state["reasoning_steps"] + [
                "检索了相关历史案例和分析框架"
            ]
        })
        return state
    
    def analyze_economic_factors(self, state: ForexState) -> ForexState:
        """分析经济因素"""
        currency_pair = state["currency_pair"]
        time_frame = state["time_frame"]
        
        # 获取经济日历数据
        economic_data = self.coordinator.economic_calendar.get_events(
            currency_pair, time_frame
        )
        
        # 使用RAG知识增强分析
        analysis_context = {
            "economic_data": economic_data,
            "background_knowledge": state["retrieved_knowledge"]
        }
        
        enhanced_analysis = self._enhance_economic_analysis(analysis_context)
        
        state.update({
            "economic_data": enhanced_analysis,
            "reasoning_steps": state["reasoning_steps"] + [
                "分析了经济数据和央行政策影响"
            ]
        })
        return state
    
    def analyze_technical_factors(self, state: ForexState) -> ForexState:
        """分析技术因素"""
        currency_pair = state["currency_pair"]
        
        # 获取技术分析数据
        technical_data = self.coordinator.technical_analyzer.ai_enhanced_analysis(
            currency_pair=currency_pair
        )
        
        # 结合RAG知识进行深度分析
        technical_context = {
            "technical_data": technical_data,
            "historical_patterns": self._extract_technical_patterns(
                state["retrieved_knowledge"]
            )
        }
        
        state.update({
            "technical_analysis": technical_context,
            "reasoning_steps": state["reasoning_steps"] + [
                "结合历史模式分析了技术面因素"
            ]
        })
        return state
    
    def synthesize_final_answer(self, state: ForexState) -> ForexState:
        """综合生成最终答案"""
        # 基于所有分析结果和RAG知识生成专业回答
        final_answer = self._generate_comprehensive_answer(state)
        
        state.update({
            "final_answer": final_answer,
            "reasoning_steps": state["reasoning_steps"] + [
                "综合所有因素生成最终分析报告"
            ]
        })
        return state