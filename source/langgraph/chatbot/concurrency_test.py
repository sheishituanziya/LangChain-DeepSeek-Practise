# File: concurrency_test.py
import concurrent.futures
import random
import time
import os
import pytest
import threading
from utils.task_executor import TaskQueue,ThreadPoolManager
from chatbot import Chatbot,ChatbotState
from main import InputProcessor


class TestProcessor(InputProcessor):
    """测试系统在非均匀负载下的表现，模拟真实场景中的处理延迟"""
    def __init__(self):
        super().__init__()
        # 计数
        self.processed_count = 0
        self.lock = threading.Lock()
    
    def process(self, text: str, user_id: str) -> str:
        with self.lock:
            self.processed_count += 1
        # 缩短延迟加速测试
        delay = random.uniform(0.01, 0.1)  
        time.sleep(delay)
        return super().process(text, user_id)
    

def stress_test():
    """并发压力测试流程"""
    # 初始化组件
    state = ChatbotState()
    task_queue = TaskQueue()
    pool = ThreadPoolManager(task_queue)
    processor = TestProcessor()
    bot = Chatbot(state, processor, task_queue)

    # 创建线程池（可根据CPU核心数调整）
    workers = min(32, (os.cpu_count() or 1) * 4)

    # 阶段1：正常状态并发测试
    print("\n[阶段1] 正常状态并发验证，50请求")
    normal_requests = 50
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        # 10个用户模拟
        futures = [executor.submit(bot.handle_input, f"req_{i}", f"user_{i%10}") 
                  for i in range(normal_requests)]
        concurrent.futures.wait(futures)
    
    # 断言1：所有正常请求立即处理
    time.sleep(0.5)  # 等待任务完成
    assert processor.processed_count == normal_requests, "正常请求未全部处理"
    assert state.pending_size() == 0, "正常状态产生待处理请求"
    assert task_queue._queue.qsize() == 0, "正常状态任务积压"
    
    # 阶段2：暂停状态并发测试
    print("\n[阶段2] 暂停状态并发验证，30请求")
    state.update("paused", True)
    paused_requests = 30
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(bot.handle_input, f"pending_{i}", f"user_{i%10}") 
                  for i in range(paused_requests)]
        concurrent.futures.wait(futures)
    
    # 断言2：暂停期间请求被保存且未处理
    assert processor.processed_count == normal_requests, "暂停期间错误处理请求"
    assert state.pending_size()== paused_requests, "待处理请求数量不符"
    
    # 阶段3：恢复与继续请求测试
    print("\n[阶段3] 恢复与继续请求验证（20操作+恢复指令）")
    mixed_requests = 20
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        
        # 先发送恢复指令
        resume_future = executor.submit(bot.handle_input, "RESUME:emergency", "admin")
        # 其他用户继续发送请求
        futures = [executor.submit(bot.handle_input, f"mixed_{i}", f"user_{i%10}") 
                  for i in range(mixed_requests)]
        concurrent.futures.wait([resume_future] + futures)
    
    # 断言3：积压请求和新请求都被处理
    time.sleep(2)  # 等待积压处理完成
    total_expected = normal_requests + paused_requests + mixed_requests
    assert processor.processed_count == total_expected, f"总处理数不符，预期{total_expected}，实际{processor.processed_count}"
    assert state.pending_size() == 0, "恢复后仍有待处理请求"
    assert task_queue._queue.qsize() == 0, "最终任务队列未清空"

    # 阶段4：关闭验证
    print("\n[阶段4] 关闭系统验证")
    task_queue.shutdown()
    assert task_queue._shutdown_flag.is_set, "任务队列未正确关闭"
    
    # 断言4：关闭后拒绝新任务
    try:
        task_queue.put(bot.handle_input, "after_shutdown", "ghost")
        pytest.fail("关闭后仍接受新任务")
    except RuntimeError:
        pass


if __name__ == "__main__":
    stress_test()