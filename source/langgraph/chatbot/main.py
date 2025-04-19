# File: main.py
from task_executor import TaskQueue, ThreadPoolManager
from chatbot import Chatbot, ChatbotState
import time

class InputProcessor:
    def process(self, text, user_id):
        return f"Processed: {text}"

def main():
    # 初始化组件
    state = ChatbotState()
    task_queue = TaskQueue()
    pool = ThreadPoolManager(task_queue)
    processor = InputProcessor()
    bot = Chatbot(state, processor, task_queue)

    # 第一阶段：正常处理
    print("\n=== Phase 1: Normal processing ===")
    task_queue.put(bot.handle_input, "Hello", "user1")
    task_queue.put(bot.handle_input, "Check status", "user2")
    time.sleep(1)

    # 第二阶段：触发暂停
    print("\n=== Phase 2: Enter paused state ===")
    state.update("paused", True)
    task_queue.put(bot.handle_input, "Query1", "user3")
    task_queue.put(bot.handle_input, "Query2", "user4")
    time.sleep(1)

    # 第三阶段：恢复执行
    print("\n=== Phase 3: Resume system ===")
    task_queue.put(bot.handle_input, "RESUME:admin123", "operator")
    time.sleep(2)

    # 第四阶段：关闭系统
    print("\n=== Phase 4: Shutdown ===")
    pool.graceful_shutdown()
    

if __name__ == "__main__":
    main()