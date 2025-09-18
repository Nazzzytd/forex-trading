#1.编写prompt
#2.chatmodel

import os
from openai import OpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"),
    base_url=os.environ.get("OPENAI_BASE_URL","your-base-url")
    )

messages=ChatPromptTemplate.from_messages([
    ("system","你是一位专业的金融分析师，擅长股票、外汇交易、宏观经济和投资策略分析。请用中文回答，并保持分析的专业性和客观性"),
    ("human","{question}")
    ])

user_input = "针对外汇交易，针对的美元和欧元，你认为最近应该买进还是买出？为什么？"

# 将 user_input 作为 question 参数传递
formatted_messages = messages.format_messages(question=user_input)
#formatted_messages = messages.format_messages(**user_input) ->format_messages() 需要字典参数，但您传递了字符串


# 转换为 OpenAI 格式
# openai_messages = [
#     {"role": "system", "content": system_message.content},
#     {"role": "user", "content": human_message.content}
# ]
openai_messages = []
for msg in formatted_messages:
    role = "user" if msg.type == "human" else msg.type
    openai_messages.append({"role": role, "content": msg.content})

response = client.chat.completions.create(
    model="gpt-4o",
    messages=openai_messages,
    temperature=0.7
)

print(response.choices[0].message.content)

