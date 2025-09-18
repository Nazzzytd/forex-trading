from langchain_openai import ChatOpenAI
import os
from langchain_core.tools import tool
from langchain.agent import create_agent

os.environ["OPENAI_API_KEY"]="your_api_key"
os.environ["OPENAI_BASE_URL"]="your_base_url"

@tool
def get_stock_price(company: str) -> float:
    """Fetches the current stock price for a given company.
    
    Args:
        company (str): The name or symbol of the company.
        
    Returns:
       float:the stock price information.
    """
    # 实际应用中，这里会调用一个金融 API 来获取数据
    
    return #公司股价

@tool
def calculate_percentage_change(price_now:float,price_yesterday:float) -> float:
    """calculate the percentage change between two days
    
    Args:
        price_now(float):the current price
        price_yesterday(float):the price for yesterday
        
    Returns:
        float: the percentage change
    """
    
    return ((price_now-price_yesterday)/price_yesterday)*100

tools=[get_stock_price, calculate_percentage_change]

llm=ChatOpenAI(model="gpt-4o",temperature=0.7)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个专业的金融分析师，善于使用工具回答问题。"),
        ("user", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)
#agent = create_agent(llm, tools=[get_stock_price, calculate_percentage_change])
#agent = create_openai_tools_agent(llm, tools=[get_stock_price, calculate_percentage_change], prompt)
agent = create_openai_tools_agent(llm, tools, prompt)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 运行 Agent
# 为了计算涨跌幅，我们需要提供昨天的股价。这里假设已知。
yesterday_apple_price = 170.0
user_query = f"苹果公司现在的股价是多少？相比昨天 {yesterday_apple_price} 涨了多少？"
response = agent_executor.invoke({"input": user_query})

print("\n--- Agent 最终回答 ---")
print(response['output'])

