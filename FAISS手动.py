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

# 初始化嵌入模型
embedder = OpenAIEmbeddings()
class ManualFAISSExperiment:
    def __init__(self):
        self.embedder = OpenAIEmbeddings()
        self.index = None
        self.memories = []  # 存储元数据
        self.dimension = 1536  # OpenAI嵌入维度
        
    def setup_index(self):
        """创建FAISS索引"""
        print("=== 步骤1: 创建FAISS索引 ===")
        self.index = faiss.IndexFlatL2(self.dimension)
        print(f"✅ 索引创建成功，维度: {self.dimension}")
        print(f"索引是否已训练: {self.index.is_trained}")
        return self.index
    
    def understand_embeddings(self):
        """理解嵌入向量"""
        print("\n=== 步骤2: 分析嵌入向量 ===")
        
        # 测试文本
        test_texts = [
            "上市公司年报分析",
            "财务报表审计",
            "公司治理结构"
        ]
        
        for i, text in enumerate(test_texts):
            embedding = self.embedder.embed_query(text)
            print(f"\n文本 {i+1}: '{text}'")
            print(f"嵌入向量维度: {len(embedding)}")
            print(f"前5个维度值: {embedding[:5]}")
            print(f"向量范数: {np.linalg.norm(embedding):.4f}")
        
        return test_texts
    
    def add_vectors_manually(self, texts):
        """手动添加向量到索引"""
        print("\n=== 步骤3: 手动添加向量 ===")
        
        embeddings_list = []
        for i, text in enumerate(texts):
            # 生成嵌入
            embedding = self.embedder.embed_query(text)
            embeddings_list.append(embedding)
            
            # 存储元数据
            self.memories.append({
                "id": i,
                "text": text,
                "embedding": embedding
            })
            
            print(f"✅ 添加文本 {i+1}: '{text}'")
        
        # 批量添加到FAISS索引（注意数据类型转换）
        embeddings_array = np.array(embeddings_list, dtype=np.float32)
        print(f"嵌入矩阵形状: {embeddings_array.shape}")
        
        self.index.add(embeddings_array)
        print(f"✅ 索引中现有向量数量: {self.index.ntotal}")
        
        return embeddings_array
    
    def search_manually(self, query_text, k=2):
        """手动搜索"""
        print(f"\n=== 步骤4: 搜索查询 '{query_text}' ===")
        
        # 生成查询嵌入
        query_embedding = self.embedder.embed_query(query_text)
        query_array = np.array([query_embedding], dtype=np.float32)
        
        print(f"查询向量形状: {query_array.shape}")
        
        # 执行搜索
        distances, indices = self.index.search(query_array, k=k)
        
        print(f"搜索结果索引: {indices}")
        print(f"相似度距离: {distances}")
        
        # 显示详细结果
        print("\n🔍 搜索结果详情:")
        for i, (idx, distance) in enumerate(zip(indices[0], distances[0])):
            if idx != -1:  # 有效的索引
                memory = self.memories[idx]
                print(f"{i+1}. 相似度: {distance:.4f}")
                print(f"   文本: {memory['text']}")
                print(f"   索引ID: {memory['id']}")
            else:
                print(f"{i+1}. 无结果")
        
        return indices, distances
    
    def run_complete_experiment(self):
        """运行完整的手动FAISS实验"""
        print("🚀 开始手动FAISS实验")
        print("=" * 50)
        
        # 1. 设置索引
        self.setup_index()
        
        # 2. 理解嵌入
        test_texts = self.understand_embeddings()
        
        # 3. 添加向量
        self.add_vectors_manually(test_texts)
        
        # 4. 测试搜索
        test_queries = ["公司年报", "财务分析", "治理"]
        for query in test_queries:
            self.search_manually(query)
        
        print("\n" + "=" * 50)
        print("✅ 手动FAISS实验完成！")

# 运行手动FAISS实验
print("🎯 实验1: 手动FAISS实现")
manual_experiment = ManualFAISSExperiment()
manual_experiment.run_complete_experiment()