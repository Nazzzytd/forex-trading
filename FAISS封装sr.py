# 1. 最简单的FAISS使用
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
import os

# 设置OpenAI API密钥（请替换为你的密钥）
api_key=os.environ.get("OPENAI_API_KEY")
base_url=os.environ.get("OPENAI_BASE_URL")
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

class AdvancedFAISSDemo:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=api_key,
            openai_api_base=base_url if base_url else None
        )
        self.vectorstore = None
    
    def create_sample_documents(self):
        """创建示例文档并构建向量库"""
        print("=== 创建示例文档 ===")
        
        # 创建业务相关的文档
        documents = [
            Document(
                page_content="腾讯2023年营业收入超过6000亿元，净利润增长显著",
                metadata={"company": "腾讯", "year": 2023, "type": "财报"}
            ),
            Document(
                page_content="阿里巴巴在云计算和AI领域投入巨额研发资金", 
                metadata={"company": "阿里巴巴", "year": 2023, "type": "研发"}
            ),
            Document(
                page_content="百度文心一言成为国内领先的大语言模型产品",
                metadata={"company": "百度", "year": 2023, "type": "产品"}
            ),
            Document(
                page_content="科技公司需要持续进行技术创新和研发投入",
                metadata={"company": "通用", "year": 2023, "type": "分析"}
            ),
            Document(
                page_content="互联网公司的财务数据包括营收、利润、用户增长等指标",
                metadata={"company": "通用", "year": 2023, "type": "财务"}
            )
        ]

         
        # 构建FAISS向量库
        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        print(f"✅ 向量库创建成功，包含 {len(documents)} 个文档")
        return documents


    def demo_all_search_methods(self):
        """演示所有搜索方法"""
        queries = ["科技公司", "财务数据", "研发投入"]
        
        for query in queries:
            print(f"\n=== 查询: {query} ===")
            
            # 1. 基础相似度搜索
            results1 = self.vectorstore.similarity_search(query, k=2)
            print("1. 相似度搜索:")
            for doc in results1:
                print(f"   - {doc.page_content[:50]}...")
            
            # 2. 带分数搜索
            results2 = self.vectorstore.similarity_search_with_score(query, k=2)
            print("2. 带分数搜索:")
            for doc, score in results2:
                print(f"   - 分数{score:.3f}: {doc.page_content[:50]}...")
            
            # 3. 最大边际相关性搜索(减少重复)
            results3 = self.vectorstore.max_marginal_relevance_search(query, k=2)
            print("3. MMR搜索(去重):")
            for doc in results3:
                print(f"   - {doc.page_content[:50]}...")
    
    def demo_retriever_modes(self):
        """演示不同的检索器模式"""
        # 相似度检索器
        similarity_retriever = self.vectorstore.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 3}
        )
        
        # MMR检索器(最大边际相关性)
        mmr_retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3, "fetch_k": 10}
        )
        
        # 分数阈值检索器
        score_retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.5}
        )
        
        query = "公司业绩"
        print(f"\n查询: {query}")
        
        print("相似度检索:", len(similarity_retriever.invoke(query)))
        print("MMR检索:", len(mmr_retriever.invoke(query)))
        print("分数阈值检索:", len(score_retriever.invoke(query)))

    def run_complete_demo(self):
        self.create_sample_documents()
        
        # 检查向量库是否创建成功
        if self.vectorstore is None:
            print("❌ 向量库创建失败，请检查API配置")
            return
        
        # 演示搜索方法
        self.demo_all_search_methods()
        
        # 演示检索器模式
        self.demo_retriever_modes()


# 正确的调用方式
if __name__ == "__main__":
    try:
        # 创建实例
        demo = AdvancedFAISSDemo()
        
        # 运行完整演示
        demo.run_complete_demo()
    except Exception as e:
        print(f"程序运行出错: {e}")
        print("\n💡 可能的原因:")
        print("1. 请检查OPENAI_API_KEY和OPENAI_BASE_URL环境变量")
        print("2. 确保网络连接正常")
        print("3. 检查API密钥是否有足够额度")
