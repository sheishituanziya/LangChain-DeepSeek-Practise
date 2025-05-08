from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

class Tool:
    """基础工具类，封装工具的执行逻辑"""
    def __init__(self, name: str):
        self.name = name
        self.description = f"{name} tool"

    def run(self, input: str) -> str:
        """执行工具并返回结果"""
        return f"Result of {self.name}({input})"

@dataclass
class ActionResponse:
    """LLM响应解析结果"""
    thought: str
    action: str
    action_input: str

class MockLLM:
    """模拟大语言模型，支持预设场景响应"""
    def __init__(self, scenario: str = "normal"):
        self.scenarios = {
            "normal": [
                "\nThought: 需要计算\nAction: Calculator\nAction Input: 2+3",
                "\nThought: 完成\nAction: FINISH\nAction Input: 5"
            ],
            "error": [
                "\nThought: 错误测试\nAction: UnknownTool\nAction Input: xxx",
                "\nThought: 经过推理，无更合适的工具，决定重试\nAction: UnknownTool\nAction Input: xxx"
            ]
        }
        self.responses = self.scenarios[scenario]
        self.step = 0

    def generate(self, prompt: str) -> str:
        """根据预设场景返回响应"""
        response = self.responses[self.step]
        self.step = min(self.step + 1, len(self.responses)-1)
        return response

class ReActAgent:
    """基于ReAct框架的智能体"""
    def __init__(
        self,
        tools: list[Tool],
        llm: MockLLM,
        max_iterations: int = 3,
        max_retries: int = 2
    ):
        self.tools = {t.name: t for t in tools}
        self.llm = llm
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.logs: list[str] = []

    def run(self, query: str) -> str:
        """执行主任务处理流程"""
        history: list[tuple] = []
        
        for step in range(self.max_iterations):
            prompt = self._build_prompt(query, history)
            response = self.llm.generate(prompt)
            self._log_step(step+1, prompt, response)

            try:
                parsed = self._parse_response(response)
                
                if parsed.action == "FINISH":
                    self.logs.append("<< FINISHED >>")
                    return parsed.action_input
                
                result = self._execute_tool(parsed.action, parsed.action_input)
                history.append((parsed.action, parsed.action_input, result))
            except Exception as e:
                # 处理错误并检查是否需要终止
                if terminate_reason := self._handle_error(e, step, history):
                    return terminate_reason

        return f"已达到最大迭代次数 {self.max_iterations}，程序终止"

    def _execute_tool(self, action: str, action_input: str) -> str:
        """执行指定工具并返回结果"""
        if tool := self.tools.get(action):
            return tool.run(action_input)
        raise ValueError(f"未知工具 {action}")

    def _handle_error(self, error: Exception, step: int, history: list) -> str:
        """统一处理异常情况"""
        error_count = step + 1
        history.append(("ERROR", str(error), ""))
        self.logs.append(f"Error: {error} - 重试次数: {error_count}/{self.max_retries}")
        
        if error_count >= self.max_retries:
            self.logs.append(f"<< TERMINATED >>达到最大重试次数 {self.max_retries}")
            return f"Error: {error} (最大重试次数)"
        return None

    def _parse_response(self, response: str) -> ActionResponse:
        """使用正则表达式解析LLM响应"""
        thought_match = re.search(r"Thought: (.*?)\n", response)
        action_match = re.search(r"Action: (\w+)", response)
        input_match = re.search(r"Action Input: (.*)", response)

        if not all([thought_match, action_match, input_match]):
            raise ValueError(f"响应解析失败: {response}")

        return ActionResponse(
            thought=thought_match.group(1).strip(),
            action=action_match.group(1).strip(),
            action_input=input_match.group(1).strip()
        )

    def _build_prompt(self, query: str, history: list) -> str:
        """构建带历史记录的提示模板"""
        tool_desc = "；".join(
            f"{name}: {tool.description}" 
            for name, tool in self.tools.items()
        )
        return f"""请回答以下问题: {query}
            可用工具: {tool_desc}
            历史记录: {self._format_history(history)}
            请按格式响应:
            - Thought: 思考过程...
            - Action: 工具名
            - Action Input: 输入参数"""

    def _format_history(self, history: list) -> str:
        """格式化历史记录"""
        return "\n".join(
            f"{act}({inp}) => {res}" 
            for act, inp, res in history
        )

    def _log_step(self, step: int, prompt: str, response: str):
        """记录执行日志"""
        formatted_response = "\n            ".join(response.split("\n"))
        self.logs.append(
            f"Step {step}:\n"
            f"Prompt: {prompt}\n"
            f"Response: {formatted_response}"
        )

# 测试执行
if __name__ == "__main__":
    tools = [Tool("Calculator"), Tool("Search")]

    print("==== 正常场景 ====")
    normal_agent = ReActAgent(tools, MockLLM("normal"))
    result = normal_agent.run("计算2+3")
    print("\n".join(normal_agent.logs))

    print("\n==== 异常场景 ====")
    error_agent = ReActAgent(tools, MockLLM("error"), max_retries=2)
    result = error_agent.run("错误测试")
    print("\n".join(error_agent.logs))