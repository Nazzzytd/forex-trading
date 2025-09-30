import os
import numpy as np
import faiss
from PyPDF2 import PdfReader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # 使用新的导入方式
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import re

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL")

class FinancialReportRAG:
    def __init__(self, embedding_model="text-embedding-3-small", llm_model="gpt-4o"):
        """
        初始化金融年报RAG系统
        """
        self.embedder = OpenAIEmbeddings(model=embedding_model)
        self.llm = ChatOpenAI(model=llm_model, temperature=0.3)
        self.vector_store = None
        self.documents = []
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        print("✅ 金融年报RAG系统初始化完成")

    def load_and_process_pdf(self, pdf_path):
        """
        加载并处理PDF文件
        """
        print(f"📄 开始处理PDF文件: {pdf_path}")
        
        # 检查文件是否存在
        if not os.path.exists(pdf_path):
            print(f"❌ 文件不存在: {pdf_path}")
            return None
        
        try:
            reader = PdfReader(pdf_path)
            text = ""
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- 第{page_num + 1}页 ---\n{page_text}"
            
            print(f"✅ PDF读取完成，共{len(reader.pages)}页，总字符数: {len(text)}")
            
            # 清理文本
            text = self.clean_text(text)
            
            # 创建Document对象
            doc = Document(
                page_content=text,
                metadata={"source": pdf_path, "pages": len(reader.pages)}
            )
            
            # 分割文本
            chunks = self.text_splitter.split_documents([doc])
            print(f"✅ 文本分割完成，共{len(chunks)}个文本块")
            
            return chunks
            
        except Exception as e:
            print(f"❌ PDF处理错误: {e}")
            return None

    def create_sample_data(self):
        """
        创建示例数据用于测试
        """
        print("📝 创建示例数据...")
        
        sample_texts = [
            "贵州茅台酒股份有限公司2023年实现净利润人民币888.54亿元，同比增长15.5%。公司主要经营茅台酒系列产品的生产和销售。",
            "公司主要产品包括飞天茅台酒、茅台王子酒、贵州大曲、赖茅酒等系列产品，其中飞天茅台是核心产品。",
            "2023年公司实现营业收入人民币1,275.32亿元，较上年增长16.5%。经营活动产生的现金流量净额为人民币635.2亿元。",
            "公司治理结构完善，设有董事会、监事会和管理层。董事会下设战略委员会、审计委员会、提名委员会、薪酬与考核委员会等专门委员会。",
            "茅台酒采用传统酿造工艺，生产周期长达五年，包括制曲、制酒、贮存、勾兑和包装等环节，确保产品品质优良。",
            "2023年公司研发投入人民币5.2亿元，主要用于生产工艺改进和产品质量提升。公司拥有专利技术156项。",
            "公司员工总数约3.2万人，其中生产人员占比65%，技术人员占比15%，管理人员占比10%，销售人员占比10%。",
            "贵州茅台在国内外市场均有销售，国内市场份额稳固，国际市场主要分布在东南亚、欧美等地区。",
            "公司2023年每股收益为人民币70.85元，拟向全体股东每10股派发现金红利259.11元（含税）。",
            "茅台酒的贮存条件严格，需要在特定的温度和湿度环境下陈放，以确保酒体老熟和风味形成。"
        ]
        
        documents = []
        for i, text in enumerate(sample_texts):
            documents.append(Document(
                page_content=text,
                metadata={"source": "sample_data", "id": i}
            ))
        
        print(f"✅ 示例数据创建完成，共{len(documents)}个文档")
        return documents

    def clean_text(self, text):
        """清理文本"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？：；（）《》]', '', text)
        return text.strip()

    def create_vector_store(self, documents):
        """
        使用封装的FAISS创建向量存储
        """
        print("🔧 开始创建向量存储...")
        
        if not documents:
            print("❌ 没有可处理的文档")
            return False
        
        try:
            # 使用LangChain封装的FAISS
            self.vector_store = FAISS.from_documents(
                documents=documents,
                embedding=self.embedder
            )
            
            self.documents = documents
            print(f"✅ 向量存储创建完成，共{len(documents)}个文档")
            return True
            
        except Exception as e:
            print(f"❌ 创建向量存储错误: {e}")
            return False

    def save_vector_store(self, path):
        """
        保存向量存储到本地
        """
        if self.vector_store:
            self.vector_store.save_local(path)
            print(f"✅ 向量存储已保存到: {path}")
        else:
            print("❌ 没有可保存的向量存储")

    def load_vector_store(self, path):
        """
        从本地加载向量存储
        """
        try:
            self.vector_store = FAISS.load_local(
                folder_path=path,
                embeddings=self.embedder,
                allow_dangerous_deserialization=True
            )
            print(f"✅ 向量存储已从 {path} 加载")
            return True
        except Exception as e:
            print(f"❌ 加载向量存储错误: {e}")
            return False

    def search_similar_chunks(self, query, k=3):
        """
        搜索相似的文本块
        """
        if not self.vector_store:
            print("❌ 请先创建向量存储")
            return []
        
        try:
            # 使用封装的相似度搜索
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for i, (doc, score) in enumerate(results):
                formatted_results.append({
                    'rank': i + 1,
                    'text': doc.page_content,
                    'score': score,
                    'metadata': doc.metadata
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ 搜索错误: {e}")
            return []

    def generate_answer(self, query, context_chunks):
        """
        基于检索结果生成答案
        """
        if not context_chunks:
            return "抱歉，在年报中未找到相关信息。"
        
        # 构建上下文
        context = "\n\n".join([f"[来源 {chunk['rank']}] {chunk['text']}" 
                               for chunk in context_chunks])
        
        prompt = f"""你是一个专业的金融分析师，需要基于上市公司年报内容回答问题。

请严格按照提供的上下文信息回答问题，不要编造信息。

上下文信息：
{context}

用户问题：{query}

请按照以下格式回答：
1. 直接基于上下文给出答案
2. 引用具体的来源编号
3. 如果信息不足，请说明在哪些部分可能找到相关信息

专业分析："""
        
        try:
            response = self.llm.invoke([
                {"role": "system", "content": "你是一个严谨的金融分析师，只基于提供的事实回答问题。"},
                {"role": "user", "content": prompt}
            ])
            return response.content
            
        except Exception as e:
            return f"生成答案时出错: {e}"

    def ask_question(self, question, k=3):
        """
        完整的问答流程
        """
        print(f"\n🤔 用户问题: {question}")
        print("🔍 正在检索相关信息...")
        
        # 检索相关文本块
        similar_chunks = self.search_similar_chunks(question, k=k)
        
        if not similar_chunks:
            return "未在年报中找到相关信息。"
        
        print(f"✅ 检索到{len(similar_chunks)}个相关文本块")
        
        # 生成答案
        print("🧠 正在生成答案...")
        answer = self.generate_answer(question, similar_chunks)
        
        # 显示检索结果
        print("\n📋 检索到的参考内容:")
        for chunk in similar_chunks:
            print(f"[{chunk['rank']}] 相似度分数: {chunk['score']:.4f}")
            print(f"   内容: {chunk['text'][:100]}...")
            print()
        
        return answer

    def build_from_pdf(self, pdf_path, save_path=None):
        """
        从PDF文件构建完整的RAG系统
        """
        print("🚀 开始构建RAG系统...")
        
        # 处理PDF
        chunks = self.load_and_process_pdf(pdf_path)
        
        if chunks is None:
            print("📝 PDF文件不存在，使用示例数据进行演示...")
            chunks = self.create_sample_data()
        
        if not chunks:
            print("❌ 无法获取任何数据")
            return False
        
        # 创建向量存储
        success = self.create_vector_store(chunks)
        
        # 保存向量存储（如果指定了路径）
        if success and save_path:
            self.save_vector_store(save_path)
        
        if success:
            print("🎉 RAG系统构建完成！可以开始提问了。")
        return success

# 使用示例
def main():
    # 初始化RAG系统
    rag_agent = FinancialReportRAG()
    
    # PDF文件路径
    pdf_path = "茅台2023年年报.pdf"
    vector_store_path = "faiss_index"  # 向量存储保存路径
    
    # 构建知识库（如果PDF不存在会自动使用示例数据）
    if rag_agent.build_from_pdf(pdf_path, vector_store_path):
        print("✅ 知识库构建完成！")
    
    # 测试问答
    test_questions = [
        "茅台公司2023年的净利润是多少？",
        "公司的主要产品有哪些？",
        "营业收入是多少？",
        "公司治理结构是怎样的？",
        "公司的研发投入是多少？",
        "员工总数和构成情况如何？"
    ]
    
    for question in test_questions:
        print("=" * 60)
        answer = rag_agent.ask_question(question)
        print(f"💡 答案: {answer}")
        print("=" * 60)
        print("\n")

if __name__ == "__main__":
    main()