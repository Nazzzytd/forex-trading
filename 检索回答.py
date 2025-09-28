import os
import numpy as np
import faiss
from PyPDF2 import PdfReader
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
import re

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
api_key=os.environ.get("OPENAI_API_KEY")
base_url=os.environ.get("OPENAI_BASE_URL")

class FinancialReportRAG:
    def __init__(self, embedding_model="text-embedding-3-small", llm_model="gpt-4o"):
        """
        初始化金融年报RAG系统
        
        Args:
            embedding_model: 嵌入模型名称
            llm_model: 大语言模型名称
        """
        
        # 初始化组件
        self.embedder = OpenAIEmbeddings(model=embedding_model)
        self.llm = ChatOpenAI(model=llm_model, temperature=0.3)
        
        # 向量数据库相关
        self.index = None
        self.documents = []  # 存储文本块和元数据
        self.dimension = 1536  # OpenAI嵌入维度
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,      # 每个文本块的大小
            chunk_overlap=200,    # 块之间的重叠
            length_function=len,
        )
        
        print("✅ 金融年报RAG系统初始化完成")

    def load_and_process_pdf(self, pdf_path):
        """
        加载并处理PDF文件
        
        Args:
            pdf_path: PDF文件路径
        """
        print(f"📄 开始处理PDF文件: {pdf_path}")
        
        try:
            # 读取PDF
            reader = PdfReader(pdf_path)
            text = ""
            
            # 提取所有页面文本
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- 第{page_num + 1}页 ---\n{page_text}"
            
            print(f"✅ PDF读取完成，共{len(reader.pages)}页，总字符数: {len(text)}")
            
            # 清理文本
            text = self.clean_text(text)
            
            # 分割文本
            chunks = self.text_splitter.split_text(text)
            print(f"✅ 文本分割完成，共{len(chunks)}个文本块")
            
            return chunks
            
        except Exception as e:
            print(f"❌ PDF处理错误: {e}")
            return []

    def clean_text(self, text):
        """清理文本，移除多余空格和特殊字符"""
        # 移除多余的空格和换行
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符但保留中文、英文、数字和基本标点
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？：；（）《》]', '', text)
        return text.strip()

    def create_vector_store(self, chunks):
        """
        创建向量存储
        
        Args:
            chunks: 文本块列表
        """
        print("🔧 开始创建向量存储...")
        
        if not chunks:
            print("❌ 没有可处理的文本块")
            return False
        
        try:
            # 生成嵌入向量
            embeddings = self.embedder.embed_documents(chunks)
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            print(f"✅ 嵌入向量生成完成，形状: {embeddings_array.shape}")
            
            # 创建FAISS索引
            self.index = faiss.IndexFlatL2(self.dimension)
            self.index.add(embeddings_array)
            
            # 存储文档元数据
            self.documents = []
            for i, chunk in enumerate(chunks):
                self.documents.append({
                    'id': i,
                    'text': chunk,
                    'embedding': embeddings[i]
                })
            
            print(f"✅ 向量存储创建完成，共{self.index.ntotal}个向量")
            return True
            
        except Exception as e:
            print(f"❌ 创建向量存储错误: {e}")
            return False

    def search_similar_chunks(self, query, k=3):
        """
        搜索相似的文本块
        
        Args:
            query: 查询文本
            k: 返回最相似的k个结果
        """
        if self.index is None:
            print("❌ 请先创建向量存储")
            return []
        
        try:
            # 生成查询嵌入
            query_embedding = self.embedder.embed_query(query)
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # 搜索
            distances, indices = self.index.search(query_array, k=k)
            
            # 获取相关文档
            results = []
            for i, (idx, distance) in enumerate(zip(indices[0], distances[0])):
                if idx != -1 and idx < len(self.documents):
                    results.append({
                        'rank': i + 1,
                        'text': self.documents[idx]['text'],
                        'distance': distance,
                        'id': idx
                    })
            
            return results
            
        except Exception as e:
            print(f"❌ 搜索错误: {e}")
            return []

    def generate_answer(self, query, context_chunks):
        """
        基于检索结果生成答案
        
        Args:
            query: 用户问题
            context_chunks: 相关文本块列表
        """
        if not context_chunks:
            return "抱歉，在年报中未找到相关信息。"
        
        # 构建上下文
        context = "\n\n".join([f"[来源 {chunk['rank']}] {chunk['text']}" 
                              for chunk in context_chunks])
        
        # 构建提示词
        prompt = f"""你是一个专业的金融分析师，需要基于上市公司年报内容回答问题。

请严格按照提供的上下文信息回答问题，不要编造信息。如果上下文没有足够信息，请明确说明。

上下文信息：
{context}

用户问题：{query}

请按照以下格式回答：
1. 直接基于上下文给出答案
2. 引用具体的来源编号
3. 如果信息不足，请说明在哪些部分可能找到相关信息

专业分析："""
        
        try:
            response = self.llm.invoke(
                messages=[
                    {"role": "system", "content": "你是一个严谨的金融分析师，只基于提供的事实回答问题。"},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"生成答案时出错: {e}"

    def ask_question(self, question, k=3):
        """
        完整的问答流程
        
        Args:
            question: 用户问题
            k: 检索的文本块数量
        """
        print(f"\n🤔 用户问题: {question}")
        print("🔍 正在检索相关信息...")
        
        # 1. 检索相关文本块
        similar_chunks = self.search_similar_chunks(question, k=k)
        
        if not similar_chunks:
            return "未在年报中找到相关信息。"
        
        print(f"✅ 检索到{len(similar_chunks)}个相关文本块")
        
        # 2. 生成答案
        print("🧠 正在生成答案...")
        answer = self.generate_answer(question, similar_chunks)
        
        # 3. 显示检索结果（用于调试）
        print("\n📋 检索到的参考内容:")
        for chunk in similar_chunks:
            print(f"[{chunk['rank']}] 相似度: {chunk['distance']:.4f}")
            print(f"   内容: {chunk['text'][:100]}...")
            print()
        
        return answer

    def build_from_pdf(self, pdf_path):
        """
        从PDF文件构建完整的RAG系统
        
        Args:
            pdf_path: PDF文件路径
        """
        print("🚀 开始构建RAG系统...")
        
        # 1. 处理PDF
        chunks = self.load_and_process_pdf(pdf_path)
        if not chunks:
            return False
        
        # 2. 创建向量存储
        success = self.create_vector_store(chunks)
        if success:
            print("🎉 RAG系统构建完成！可以开始提问了。")
        return success

# 使用示例
def main():
    # 初始化RAG系统
    rag_agent = FinancialReportRAG()
    
    # 替换为你的PDF文件路径
    pdf_path = "茅台2023年年报.pdf"  # 请确保文件存在
    
    # 构建知识库
    if rag_agent.build_from_pdf(pdf_path):
        # 测试问答
        test_questions = [
            "茅台公司2023年的净利润是多少？",
            "公司的主要产品有哪些？",
            "营业收入是多少？",
            "公司治理结构是怎样的？"
        ]
        
        for question in test_questions:
            print("=" * 60)
            answer = rag_agent.ask_question(question)
            print(f"💡 答案: {answer}")
            print("=" * 60)
            print("\n")

if __name__ == "__main__":
    # 如果PDF文件不存在，创建一个模拟的测试文件
    if not os.path.exists("茅台2023年年报.pdf"):
        print("⚠️  请将PDF文件放在当前目录下，或使用以下代码创建测试文件...")
        
        # 这里可以添加创建测试PDF的代码（可选）
        # 或者直接使用文本内容进行测试
        test_chunks = [
            "贵州茅台酒股份有限公司2023年实现净利润人民币888.54亿元，同比增长15.5%。",
            "公司主要产品包括飞天茅台酒、茅台王子酒、贵州大曲等系列产品。",
            "2023年公司实现营业收入人民币1,275.32亿元，较上年增长16.5%。",
            "公司治理结构完善，设有董事会、监事会和管理层，董事会下设战略委员会、审计委员会等专门委员会。",
            "茅台酒的生产工艺独特，采用传统酿造工艺，生产周期长，品质优良。"
        ]
        
        rag_agent = FinancialReportRAG()
        rag_agent.create_vector_store(test_chunks)
        
        # 测试问答
        question = "茅台公司2023年的净利润是多少？"
        answer = rag_agent.ask_question(question)
        print(f"💡 答案: {answer}")