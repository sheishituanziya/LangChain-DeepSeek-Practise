import os
import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import CSVLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain.agents import create_react_agent, tool
from langchain.schema import input_adapter
from langchain.schema.messages import HumanMessage, AIMessage
from langchain_core.language_models import BaseLanguageModel

# 假设 llm 是一个已配置的语言模型
llm = BaseLanguageModel()  # 替换为您的实际模型

def get_completion_from_messages(messages, temperature=0):
    llm.temperature = temperature
    response = llm.invoke(messages)
    return response.content

def get_city(text):
    template_string = """
    请从用户输入中精确提取中国地级市及下属区县名称，并严格按以下规则输出：

    **提取规则：**
    1. 必须包含市级和区县级两个行政单位
    2. 输出格式为："xx市xx区" 或 "xx市xx县"
    3. 直辖市特殊处理（如北京、上海等），格式为："xx区"（不重复市级）

    **处理要求：**
    - 若原文同时包含区和县，优先保留区
    - 若原文只有市级名称，补充该市的主城区（如"南京市"→"南京市玄武区"）
    - 若原文不包含有效信息，返回"未识别"
    - 返回结果仅包含xx市xx区或xx市xx县，不要附加任何解释信息

    **示例：**
    输入："明天江宁的天气怎么样"
    输出："南京市江宁区"

    输入："我想查询上海浦东新区的交通"
    输出："浦东新区"

    输入："河北省邯郸市涉县天气预报"
    输出："邯郸市涉县"

    **请处理以下输入：**
    "{text}"
     """
    template = ChatPromptTemplate.from_template(template_string)
    messages = template.format_messages(text=text)
    return get_completion_from_messages(messages=messages)

def get_city_code(text):
    city_name = get_city(text)
    file = "./file/5_city_code.csv"
    loader = CSVLoader(file_path=file, encoding="gbk")
    embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
    index = VectorstoreIndexCreator(
        embedding=embedding, vectorstore_cls=DocArrayInMemorySearch
    ).from_loaders([loader])

    query = f"""
    请检索出目标城市或区县的信息，并直接输出城市编号pid

    城市名称{city_name}

    当输入中既包含城市又包含区县时，只需要返回区县的信息即可
    """
    return index.query(query, llm=llm)

def weather_description(data):
    template_string = """
    你是一位专业的天气播报员，请根据以下JSON格式的天气数据，为游客生成简洁明了的天气简报和出行建议。要求：

    1. **核心天气概况**（50字以内）：
       - 用一句话总结今日整体天气状况
       - 标注当前实时温度和体感关键词（如"凉爽"、"闷热"等）

    2. **重点指标**（表格呈现）：
       | 指标        | 日间数值 | 夜间数值 |
       |-------------|----------|----------|
       | 温度范围    | [白天高温]℃ | [夜间低温]℃ |
       | 天气现象    | [白天天气] | [夜间天气] |
       | 降水概率    | [降雨概率]% | [降雨概率]% |
       | 紫外线强度  | [UV指数] - [强度描述] | - |
       | 空气质量    | [AQI] - [污染等级] | - |

    3. **分时段建议**：
       - 清晨（[日出时间]）：[活动建议]
       - 日间（10:00-16:00）：[活动建议]
       - 傍晚（[日落时间]前后）：[活动建议]
       - 夜间：[活动建议]

    4. **特殊提示**（如有）：
       - 空气质量提醒：[空气提示]
       - 极端天气预警：[警报内容]
       - 穿衣指南：根据温度变化推荐

    5. **旅游规划建议**：
       - 户外活动适宜度：⭐️[1-5星评价]
       - 推荐携带物品：[列出3-5项]
       - 交通影响：[风速和能见度对出行的影响]

    请基于以下数据生成报告（保持专业但友好的语气）：
    {data}
     """
    template = ChatPromptTemplate.from_template(template_string)
    messages = template.format_messages(data=data)
    return get_completion_from_messages(messages=messages)

@tool
def get_city_weather(text):
    pid = get_city_code(text)
    weather_id = os.environ.get("weather_id")
    weather_secret = os.environ.get("weather_secret")
    if not weather_id or not weather_secret:
        return "请设置天气 API 的环境变量 weather_id 和 weather_secret"
    
    api_url = f"http://gfeljm.tianqiapi.com/api?unescape=1&version=v63&appid={weather_id}&appsecret={weather_secret}&adcode={pid}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        return weather_description(data)
    return "无法获取天气信息"

@tool
def get_city_spot(text):
    city_name = get_city(text)
    file = "./file/5_city_spot.csv"
    loader = CSVLoader(file_path=file, encoding="gbk")
    embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
    index = VectorstoreIndexCreator(
        embedding=embedding, vectorstore_cls=DocArrayInMemorySearch
    ).from_loaders([loader])

    query = f"""
    请执行以下操作：
    1. 检索{city_name}的所有景点信息
    2. 将所有景点名称提取出来
    3. 用中文顿号"、"连接成一个字符串
    4. 直接返回连接后的字符串，不要包含其他说明文字

    注意：
    - 如果{city_name}同时匹配到城市和区县，优先返回区县的景点
    - 确保每个景点名称之间用顿号分隔
    - 不要包含编号或其他字段
    """
    return index.query(query, llm=llm)

@tool
def calculator(text):
    # 示例计算器工具
    try:
        result = eval(text)
        return f"计算结果：{result}"
    except Exception as e:
        return f"计算失败：{str(e)}"

@tool
def search(text):
    # 示例搜索工具
    return f"搜索结果：{text}"

@tool
def get_current_time(text):
    # 示例时间工具
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def analyze_tool_usage(response):
    tool_usage = []
    for item in response["intermediate_steps"]:
        if "action" in item and "tool" in item:
            tool_usage.append({"action": item["action"], "tool": item["tool"]})
    return tool_usage

# 创建代理
tools = [get_current_time, calculator, search, get_city_weather, get_city_spot]
agent = create_react_agent(tools=tools, model=llm)
chain = input_adapter | agent

# 测试工作流
response = chain.invoke({
    "input": "今天南京天气如何？请帮我根据天气制定一个南京的游玩攻略，再帮我计算去那里旅游预算：5天住宿每天400元，机票往返2000元"
})

print("最终回答:", response["messages"][-1].content)
print("\n工具调用记录:")
for item in analyze_tool_usage(response):
    print(f"- {item['action']} {item['tool']}")