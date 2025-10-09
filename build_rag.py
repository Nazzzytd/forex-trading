import os
import sys
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_build.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- 配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "trade_docs")
PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")

def check_environment():
    """检查环境配置"""
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("未找到 OPENAI_API_KEY 环境变量")
        return False
    
    if not os.path.exists(DOCS_DIR):
        logger.error(f"文档目录 {DOCS_DIR} 不存在")
        return False
    
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    if not pdf_files:
        logger.error(f"在 {DOCS_DIR} 目录下未找到PDF文件")
        return False
    
    return True

def load_documents(directory):
    """加载文档"""
    documents = []
    pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    
    for filename in pdf_files:
        file_path = os.path.join(directory, filename)
        try:
            logger.info(f"正在加载: {filename}")
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            
            for doc in docs:
                doc.metadata['source_file'] = filename
                
            documents.extend(docs)
            logger.info(f"成功加载: {filename}, 页数: {len(docs)}")
            
        except Exception as e:
            logger.error(f"加载 {filename} 时出错: {str(e)}")
            continue
    
    logger.info(f"总共加载 {len(documents)} 个文档页面")
    return documents

def split_documents(documents):
    """分割文档为块"""
    if not documents:
        logger.error("没有文档可供分割")
        return []
    
    # 显示文档统计
    total_chars = sum(len(doc.page_content.strip()) for doc in documents)
    logger.info(f"文档统计: {len(documents)} 页, {total_chars} 字符")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", "．", "……", "…", " ", ""],
        is_separator_regex=False
    )
    
    splits = text_splitter.split_documents(documents)
    logger.info(f"文档分割完成，生成 {len(splits)} 个文本块")
    
    return splits

def create_vectorstore(splits):
    """创建向量数据库"""
    if not splits:
        logger.error("没有文本块可用于创建向量数据库")
        return None
    
    try:
        # 设置环境变量，确保使用自定义基础URL
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        if base_url:
            # 设置环境变量，让OpenAIEmbeddings使用自定义URL
            os.environ["OPENAI_API_BASE"] = base_url
        
        # 使用OpenAI的嵌入模型
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key
        )
        
        # 创建持久化目录
        os.makedirs(PERSIST_DIR, exist_ok=True)
        
        # 将分割后的文本转换为向量并存入Chroma
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=PERSIST_DIR
        )
        vectorstore.persist()
        logger.info(f"向量数据库已创建并保存至: {PERSIST_DIR}")
        
        # 验证向量数据库
        collection_count = vectorstore._collection.count()
        logger.info(f"向量数据库包含 {collection_count} 个文档块")
        
        return vectorstore
        
    except Exception as e:
        logger.error(f"创建向量数据库时出错: {str(e)}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("           外汇交易RAG知识库构建系统")
    print("=" * 60)
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    
    # 执行构建流程
    logger.info("开始构建RAG知识库...")
    
    # 1. 加载文档
    raw_docs = load_documents(DOCS_DIR)
    if not raw_docs:
        logger.error("没有成功加载任何文档，构建终止")
        sys.exit(1)
    
    # 2. 分割文本
    doc_splits = split_documents(raw_docs)
    if not doc_splits:
        logger.error("文档分割失败，构建终止")
        sys.exit(1)
    
    # 3. 创建向量数据库
    vectorstore = create_vectorstore(doc_splits)
    if not vectorstore:
        logger.error("向量数据库创建失败")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ RAG知识库构建完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()