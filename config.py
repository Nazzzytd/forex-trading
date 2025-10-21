# config.py
import os
from typing import Dict
from dotenv import load_dotenv

class Config:
    """配置管理类"""
    
    def __init__(self):
        # 加载 .env 文件
        load_dotenv()
        
        # Alpha Vantage API (金融数据)
        self.alpha_api_key = os.getenv('ALPHA_VANTAGE_API_KEY')  # 注意：使用您在.env中的变量名

        # 新增NewsAPI密钥
        self.newsapi_key = os.getenv('NEWSAPI_KEY')

        self.twelvedata_api_key = os.getenv('TWELVEDATA_API_KEY')
        
        # OpenAI API (AI生成)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_base_url = os.getenv('OPENAI_BASE_URL')
        
        # 显示配置状态
        self._show_config_status()
    
    def _show_config_status(self):
        """显示配置状态"""
        print("🔧 配置检查:")
        print(f"   Alpha Vantage API: {'✅ 已设置' if self.alpha_api_key else '❌ 未设置'}")
        print(f"   NewsAPI: {'✅ 已设置' if self.newsapi_key else '❌ 未设置'}")
        print(f"   OpenAI API Key: {'✅ 已设置' if self.openai_api_key else '❌ 未设置'}")
        print(f"   OpenAI Base URL: {'✅ 已设置' if self.openai_base_url else '❌ 未设置'}")
        
        if not self.alpha_api_key:
            print("❌ 错误: 缺少Alpha Vantage API密钥，无法获取金融数据")
    
    def validate(self) -> bool:
        """验证配置是否完整"""
        return bool(self.alpha_api_key)

# 全局配置实例
config = Config()