# FAISSMemory类：自定义记忆存储，使用FAISS进行向量相似性搜索
# FinancialAgent类：金融对话Agent，整合记忆系统和LLM
# 记忆检索机制：能够根据当前查询找到相关的历史对话

import os
from openai import OpenAI
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from langchain.embeddings import OpenAIEmbeddings

os.environ["OPENAI_API_KEY"]="your-api-key"
os.environ["OPENAI_BASE_URL"]="your-base_url"
#能否直接这样编码在前面？全局使用？

class FAISSMemory:
    def __init__(self,dimension=1536):
        self.embedder=OpenAIEmbeddings()
        self.index=faiss.Indexflat2(dimention)
        self.memories=[]


    def add_memory(self,query:str,response:str):
        text=f"{query}{response}"
        embedding=embedder.embeded_query(text)

        self.index.add(np.array([embedding],dtype=np.float32))
        self.memories.append({
            "query":query,
            "response":response,
            "embedding":embedding
        })

    def search_memory(self,query:str,k:int=3)->List[Dict]:
        embedding_query=embedder.embed_query(query)
        distances,indices=self.index.search(np.array([embedding_query],dtype=np.float32),k)

        result=[]
        for i,idx in enumerate(indices[0]):  #取索引i，和索引i对应的数的index索引
            if 0<=idx<len(self.memories):
                memory=self.memories[idx].copy()
                memory["similarity"]=1 / (1 + distances[0][i])
                results.append(memory)
        return results


class FinacialAgent:

    def __init__(self):
        self.llm=OpenAI(temperature=0.3)
        self.memory=FAISSMemory()
        self.conversation_history=[]
    
    def chat(self,query:str)->str:
        #搜索相关记忆
        relevant_memory=self.memory.search_memory(query)

        prompt=build_prompt()

        response=self.llm.predict(prompt)

        self.memory.add_memory(query,response)
        self.conversation_history.append((query,response))


    def build_prompt(self,query:str,memories:list[Dict])->str:
        
        history = "\n".join([f"用户: {q}\n助手: {r}" for q, r in self.conversation_history[-3:]])
        
        memory_text="\n".join([
            f"记忆:{m['query']} -> 记忆:{m['response']}" for m in memories
        ]) if memories else  "无相关记忆"

        return f"""你是金融助手，基于以下信息回答问题：

最近对话：
{history}

相关记忆：
{memory_text}

当前问题：{query}

请提供专业回答："""


    def handle_reference():
        """处理模糊引用"""
        # 查找最近的股票对话
        stock_keywords = ["股票", "股价", "stock", "ticker"]
        for q, r in reversed(self.conversation_history):
            if any(keyword in q.lower() for keyword in stock_keywords):
                return f"""您之前问过："{q}"
我回答过："{r}"

您想了解这只股票的什么最新信息？"""
        
        return "抱歉，没找到您之前询问的股票记录。"

def main():
    agent = FinancialAgent()
    
    queries = [
        "苹果股票怎么样？",
        "特斯拉股价如何？", 
        "刚才问的那只股票呢？",
        "微软财报怎么样？"
    ]
    
    for query in queries:
        print(f"用户: {query}")
        
        if "刚才" in query or "之前" in query:
            response = agent.handle_reference(query)
        else:
            response = agent.chat(query)
        
        print(f"助手: {response}\n")

if __name__ == "__main__":
    main()


