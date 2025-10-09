import os
import sys
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from dotenv import load_dotenv
import logging
from typing import List, Dict, Any

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")

class ForexRAGQuerySystem:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.vectorstore = None
        self.embeddings = None
        self.llm = None
        self.retriever = None
        
    def initialize_system(self) -> bool:
        """初始化系统组件"""
        try:
            # 检查向量数据库是否存在
            if not os.path.exists(self.persist_directory):
                logger.error(f"向量数据库目录不存在: {self.persist_directory}")
                return False
            
            # 设置环境变量，确保使用自定义基础URL
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            
            if base_url:
                os.environ["OPENAI_API_BASE"] = base_url
            
            # 初始化嵌入模型
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=api_key
            )
            
            # 加载向量数据库 - 使用兼容方式
            try:
                # 尝试新版本导入
                from langchain_chroma import Chroma
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            except ImportError:
                # 回退到旧版本
                from langchain_community.vectorstores import Chroma
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            
            # 创建检索器
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            # 初始化LLM - 移除不支持的参数
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1,
                # 移除 max_tokens 参数，因为您的API端点不支持
                openai_api_key=api_key,
                openai_api_base=base_url
            )
            
            logger.info("系统初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"系统初始化失败: {str(e)}")
            return False
    
    def get_relevant_documents(self, question: str) -> List[Document]:
        """获取相关文档 - 使用兼容的方法"""
        try:
            # 尝试使用新方法
            if hasattr(self.retriever, 'invoke'):
                docs = self.retriever.invoke(question)
            else:
                # 回退到旧方法
                docs = self.retriever.get_relevant_documents(question)
            return docs
        except Exception as e:
            logger.error(f"检索文档时出错: {str(e)}")
            return []
    
    def format_context(self, docs: List[Document]) -> str:
        """格式化上下文信息"""
        if not docs:
            return "暂无相关上下文信息。"
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source_file', '未知文档')
            page = doc.metadata.get('page', 0)
            content = doc.page_content.strip()
            
            context_parts.append(f"[文档{i}] 来源: {source} (第{int(page)+1}页)\n内容: {content}")
        
        return "\n\n".join(context_parts)
    
    def build_enhanced_prompt(self, question: str, context: str) -> str:
        """构建增强的提示词"""
        return f"""您是一个专业的外汇交易分析师，请基于以下提供的交易知识上下文来回答问题。

上下文信息：
{context}

请按照以下要求回答：
1. 严格基于上下文信息回答问题
2. 如果上下文信息不足，请说明哪些方面信息不足
3. 对于交易技术分析，请详细说明形态特征和市场意义
4. 回答要专业、准确、实用

问题：{question}

请给出专业、详细的回答："""

    def ask_question(self, question: str) -> Dict[str, Any]:
        """提问并获取答案"""
        try:
            logger.info(f"处理问题: {question}")
            
            # 1. 检索相关文档
            docs = self.get_relevant_documents(question)
            context = self.format_context(docs)
            
            # 2. 构建增强的Prompt
            prompt = self.build_enhanced_prompt(question, context)
            
            # 3. 调用LLM生成答案
            response = self.llm.invoke(prompt)
            
            # 4. 整理结果
            result = {
                "question": question,
                "answer": response.content,
                "source_documents": docs,
                "context_used": context
            }
            
            logger.info("问题处理完成")
            return result
            
        except Exception as e:
            logger.error(f"处理问题时出错: {str(e)}")
            return {
                "question": question,
                "answer": f"抱歉，处理问题时出现错误: {str(e)}",
                "source_documents": [],
                "context_used": ""
            }
    
    def format_response(self, result: Dict[str, Any]) -> str:
        """格式化响应结果"""
        response = f"🤖 问题: {result['question']}\n\n"
        response += f"💡 回答:\n{result['answer']}\n\n"
        
        if result['source_documents']:
            response += "📚 参考来源:\n"
            for i, doc in enumerate(result['source_documents'][:3], 1):
                source = doc.metadata.get('source_file', '未知文档')
                page = doc.metadata.get('page', 0)
                content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                
                response += f"{i}. {source} (第{int(page)+1}页)\n"
                response += f"   片段: {content_preview}\n\n"
        
        return response

def interactive_mode(query_system: ForexRAGQuerySystem):
    """交互式查询模式"""
    print("\n" + "=" * 60)
    print("           外汇交易RAG智能问答系统")
    print("=" * 60)
    print("💡 您可以询问关于：")
    print("   • 蜡烛图技术（锤子线、吞没形态等）")
    print("   • 技术分析指标")
    print("   • 交易策略")
    print("   • 风险管理")
    print("输入 'quit' 或 '退出' 结束程序")
    print("-" * 60)
    
    while True:
        try:
            question = input("\n💬 请输入您的问题: ").strip()
            
            if question.lower() in ['quit', '退出', 'exit', 'q']:
                print("👋 感谢使用，再见！")
                break
                
            if not question:
                continue
                
            # 执行查询
            result = query_system.ask_question(question)
            response = query_system.format_response(result)
            print(f"\n{response}")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\n👋 程序被用户中断，再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")

def main():
    """主函数"""
    # 初始化查询系统
    query_system = ForexRAGQuerySystem()
    
    if not query_system.initialize_system():
        print("❌ 系统初始化失败，请检查：")
        print("   1. 是否已运行 build_rag.py 构建知识库")
        print("   2. OPENAI_API_KEY 环境变量是否正确设置")
        print("   3. 向量数据库目录是否存在")
        sys.exit(1)
    
    # 根据命令行参数选择模式
    if len(sys.argv) > 1:
        # 单次查询模式
        question = " ".join(sys.argv[1:])
        result = query_system.ask_question(question)
        response = query_system.format_response(result)
        print(response)
    else:
        # 交互式模式
        interactive_mode(query_system)

if __name__ == "__main__":
    main()