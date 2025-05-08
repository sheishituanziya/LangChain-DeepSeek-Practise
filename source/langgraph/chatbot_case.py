from typing import Annotated
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import InjectedToolCallId
from langchain_core.tools import BaseTool
from typing_extensions import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt
import getpass
import os

# 定义状态类型，该类型用于描述状态图中的状态信息
# 包含消息列表（messages）、实体名称（name）和实体生日（birthday）
# 消息列表将用于存储与用户的交互信息，实体名称和生日是示例中涉及的特定实体属性
class State(TypedDict):
    messages: Annotated[list, add_messages]  # 用于存储与用户交互的消息列表
    name: str  # 表示实体的名称
    birthday: str  # 表示实体的生日


# 定义自定义工具节点类，该工具用于请求人类协助以确认信息的正确性
# 继承自BaseTool类，是一个自定义的工具实现
class CustomToolNode(BaseTool):
    name = "human_assistance"  # 工具的名称，用于标识该工具
    description = "Request assistance from a human."  # 工具的描述，说明其功能是请求人类协助

    # 同步运行工具的方法，接收实体名称、生日和工具调用ID作为参数
    def _run(self, name: str, birthday: str, tool_call_id: Annotated[str, InjectedToolCallId]):
        # 向人类发送请求，询问当前的信息（实体名称和生日）是否正确
        human_response = interrupt(
            {
                "question": "Is this correct?",
                "name": name,
                "birthday": birthday,
            }
        )
        # 根据人类的反馈结果更新状态信息
        if human_response.get("correct", "").lower().startswith("y"):
            # 如果人类确认信息正确，创建一个命令对象来更新状态
            command = Command(state_update={"name": name, "birthday": birthday})
            return "Information approved by human."  # 返回信息已被人类批准的消息
        return "Information needs to be corrected."  # 如果人类认为信息不正确，返回需要修正的消息

    # 异步运行工具的方法，在当前示例中未实现
    async def _arun(self, *args, **kwargs):
        raise NotImplementedError


def main():
    # 设置环境变量的内部函数，用于获取用户输入的API密钥并设置到环境变量中
    def _set_env(var: str):
        if not os.environ.get(var):
            os.environ[var] = getpass.getpass(f"{var}: ")

    _set_env("ANTHROPIC_API_KEY")  # 获取并设置Anthropic API的密钥，用于访问Anthropic的语言模型服务
    _set_env("TAVILY_API_KEY")  # 获取并设置Tavily API的密钥，用于使用Tavily的搜索工具服务

    # 初始化语言模型和工具
    tool = TavilySearchResults(max_results=2)  # 初始化Tavily搜索工具，设置最大返回结果数为2
    # 初始化ChatAnthropic语言模型，并将Tavily搜索工具绑定到该语言模型上
    # 这样语言模型在生成回复时可以调用Tavily搜索工具获取相关信息
    llm = ChatAnthropic(model="claude-3-5-sonnet-20240620").bind_tools([tool])

    # 定义聊天机器人节点函数，该函数用于处理用户的消息并生成回复
    def chatbot(state: State):
        # 使用绑定了工具的语言模型来处理状态中的消息列表
        # 并将生成的回复添加到消息列表中，更新状态信息
        return {"messages": [llm.invoke(state["messages"])]}

    # 构建状态图，通过链式调用的方式逐步添加节点和边
    graph_builder = (
        StateGraph(State)  # 创建一个基于State类型的状态图对象
        .add_node("chatbot", chatbot)  # 添加名为"chatbot"的节点，节点的处理函数为chatbot
        .add_node("tools", ToolNode(tools=[tool, CustomToolNode()]))  # 添加名为"tools"的节点，包含Tavily搜索工具和自定义的人类协助工具
        .add_conditional_edges("chatbot", tools_condition)  # 在"chatbot"节点和"tools"节点之间添加条件边，根据特定条件决定是否调用工具节点
        .add_edge("tools", "chatbot")  # 添加从"tools"节点到"chatbot"节点的边，表示工具调用完成后返回聊天机器人节点
        .add_edge(START, "chatbot")  # 添加从起始点START到"chatbot"节点的边，设置状态图的入口
    )

    # 编译状态图，并创建一个内存检查点保存器
    # 内存检查点保存器用于保存状态图的状态，以便在需要时恢复
    graph = graph_builder.compile(checkpointer=MemorySaver())

    # 主循环，用于与用户进行交互并处理用户输入
    config = {"configurable": {"thread_id": "1"}}  # 配置信息，包含线程ID等相关设置
    while True:
        try:
            user_input = input("User: ")  # 获取用户输入的文本
            if user_input.lower() in ["quit", "exit", "q"]:  # 检查用户输入是否为退出指令
                print("Goodbye!")  # 如果是退出指令，打印再见消息并退出循环
                break
            # 使用状态图处理用户输入，通过流式处理获取处理结果
            # 并将生成的回复消息进行格式化打印
            for event in graph.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config,
                stream_mode="values",
            ):
                if "messages" in event:
                    event["messages"][-1].pretty_print()
        except Exception as e:
            print(f"An error occurred: {e}")  # 捕获并打印在处理过程中发生的异常信息
            user_input = "What do you know about LangGraph?"  # 如果发生异常，设置一个默认的用户输入问题
            print("User: " + user_input)  # 打印默认的用户输入问题
            # 使用状态图处理默认的用户输入问题，并将处理结果进行格式化打印
            for event in graph.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config,
                stream_mode="values",
            ):
                if "messages" in event:
                    event["messages"][-1].pretty_print()
            break


if __name__ == "__main__":
    main()  # 调用主函数，启动程序的执行流程
