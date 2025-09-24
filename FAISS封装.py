import numpy as np
import faiss
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import os

# 设置OpenAI API密钥（请替换为你的密钥）
api_key=os.environ.get("OPENAI_API_KEY")
base_url=os.environ.get("OPENAI_BASE_URL")
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

class LangChainFAISSExperiment:
    def __init__(self):
        self.embedder = OpenAIEmbeddings()
        self.vectorstore = None
    
    def create_documents_with_metadata(self):
        """创建带元数据的文档"""
        print("=== 步骤1: 创建文档对象 ===")
        
        # 模拟上市公司年报内容
        annual_report_data = [
            {
                "content": "公司2023年实现营业收入500亿元，同比增长15%",
                "metadata": {"year": 2023, "section": "财务摘要", "page": 1}
            },
            {
                "content": "净利润达到60亿元，净资产收益率ROE为12%", 
                "metadata": {"year": 2023, "section": "盈利能力", "page": 2}
            },
            {
                "content": "研发投入25亿元，占营业收入比例5%",
                "metadata": {"year": 2023, "section": "研发投入", "page": 3}
            },
            {
                "content": "公司现金及等价物余额为80亿元，资产负债率45%",
                "metadata": {"year": 2023, "section": "财务状况", "page": 4}
            }
        ]
        
        documents = []
        for data in annual_report_data:
            doc = Document(
                page_content=data["content"],
                metadata=data["metadata"]
            )
            documents.append(doc)
            print(f"📄 创建文档: {data['content'][:30]}...")
            print(f"   元数据: {data['metadata']}")
        
        return documents
    
    def create_vectorstore(self, documents):
        """创建FAISS向量库"""
        print("\n=== 步骤2: 创建FAISS向量库 ===")
        
        self.vectorstore = FAISS.from_documents(documents, self.embedder)
        
        print("✅ FAISS向量库创建成功")
        print(f"索引中的文档数量: {self.vectorstore.index.ntotal}")
        print(f"向量维度: {self.vectorstore.index.d}")
        
        return self.vectorstore
    
    def demonstrate_search_capabilities(self):
        """演示搜索能力"""
        print("\n=== 步骤3: 搜索功能演示 ===")
        
        test_queries = [
            "营业收入情况",
            "研发投入多少",
            "公司财务状况"
        ]
        
        for query in test_queries:
            print(f"\n🔍 查询: '{query}'")
            
            # 基础相似度搜索
            results = self.vectorstore.similarity_search(query, k=2)
            print(f"相似度搜索结果 ({len(results)} 个):")
            for i, doc in enumerate(results):
                print(f"  {i+1}. {doc.page_content}")
                print(f"     元数据: {doc.metadata}")
            
            # 带分数的搜索
            print(f"\n带相似度分数的搜索:")
            results_with_score = self.vectorstore.similarity_search_with_score(query, k=2)
            for i, (doc, score) in enumerate(results_with_score):
                print(f"  {i+1}. 分数: {score:.4f} - {doc.page_content}")
    
    def demonstrate_advanced_features(self):
        """演示高级功能"""
        print("\n=== 步骤4: 高级功能演示 ===")
        
        # 1. 作为检索器使用
        print("1. 检索器模式:")
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        results = retriever.invoke("公司利润")
        print(f"检索到 {len(results)} 个相关文档")
        
        # 2. 保存和加载
        print("\n2. 持久化功能:")
        save_path = "./faiss_demo_index"
        self.vectorstore.save_local(save_path)
        print(f"✅ 向量库已保存到: {save_path}")
        
        # 模拟加载
        try:
            loaded_vectorstore = FAISS.load_local(save_path, self.embedder)
            print(f"✅ 向量库加载成功，文档数: {loaded_vectorstore.index.ntotal}")
        except Exception as e:
            print(f"加载演示: {e}")
    
    def run_complete_experiment(self):
        """运行完整的LangChain FAISS实验"""
        print("🚀 开始LangChain FAISS实验") 
        print("=" * 50)
        
        # 1. 创建文档
        documents = self.create_documents_with_metadata()
        
        # 2. 创建向量库
        self.create_vectorstore(documents)
        
        # 3. 搜索演示
        self.demonstrate_search_capabilities()
        
        # 4. 高级功能
        self.demonstrate_advanced_features()
        
        print("\n" + "=" * 50)
        print("✅ LangChain FAISS实验完成！")

# 运行LangChain FAISS实验
print("\n🎯 实验2: LangChain FAISS封装")
lc_experiment = LangChainFAISSExperiment()
lc_experiment.run_complete_experiment()