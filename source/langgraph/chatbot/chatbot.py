# File: chatbot.py
import threading
from commands import ResumeCommand

class ChatbotState:
    """状态管理（状态模式）
    该类用于管理聊天机器人的状态，包括是否活跃、是否暂停等，
    并支持添加状态监听器，当状态发生变化时通知监听器。
    """
    def __init__(self):
        # 初始化状态字典，active 表示机器人是否活跃，paused 表示是否暂停
        self._state = {"active": True, "paused": False}
        # 使用可重入锁来保证线程安全
        self._lock = threading.RLock()
        # 存储状态监听器的列表
        self._state_listeners = []

    def add_listener(self, listener):
        """添加状态监听器
        :param listener: 监听器对象，需要实现 on_state_change 方法
        """
        self._state_listeners.append(listener)

    def update(self, key, value):
        """更新状态
        :param key: 状态的键，如 "active" 或 "paused"
        :param value: 状态的新值
        """
        with self._lock:
            # 获取旧的状态值
            old = self._state.get(key)
            # 更新状态值
            self._state[key] = value
            # 如果状态值发生了变化，通知所有监听器
            if old != value:
                self._notify(key, value)

    def _notify(self, key, value):
        """通知所有监听器状态发生了变化
        :param key: 发生变化的状态的键
        :param value: 发生变化的状态的新值
        """
        for listener in self._state_listeners:
            listener.on_state_change(key, value)

class Chatbot:
    """聊天机器人核心（策略模式）
    该类是聊天机器人的核心，负责处理用户输入，根据机器人的状态
    决定是立即处理输入还是保存为待处理请求。
    """
    def __init__(self, state: ChatbotState, processor, task_queue):
        """初始化聊天机器人
        :param state: 聊天机器人的状态管理对象
        :param processor: 输入处理器，用于处理用户输入
        :param task_queue: 任务队列，用于存储待处理的任务
        """
        self.state = state
        self.processor = processor
        self.task_queue = task_queue
        # 将自己添加为状态监听器
        state.add_listener(self)

    def on_state_change(self, key, value):
        """当状态发生变化时的回调方法
        :param key: 发生变化的状态的键
        :param value: 发生变化的状态的新值
        """
        # 如果暂停状态变为 False，即机器人恢复运行，处理待处理请求
        if key == "paused" and not value:
            self._process_pending()

    def handle_input(self, user_input: str, user_id: str):
        """处理用户输入
        :param user_input: 用户输入的文本
        :param user_id: 用户的 ID
        """
        # 如果机器人处于暂停状态
        if self.state._state["paused"]:
            self._handle_paused_input(user_input, user_id)
        else:
            self._process_input(user_input, user_id)

    def _handle_paused_input(self, user_input: str, user_id: str):
        """处理机器人暂停时的用户输入
        :param user_input: 用户输入的文本
        :param user_id: 用户的 ID
        """
        # 如果用户输入以 "RESUME:" 开头，尝试恢复系统
        if user_input.startswith("RESUME:"):
            # user_input[7:] 表示从第 7 个字符开始截取输入，因为 "RESUME:" 长度为 7，
            # 这样就可以获取到 "RESUME:" 后面的命令部分
            self._resume_system(user_input[7:], user_id)
        else:
            # 否则，将输入保存为待处理请求
            self._save_pending(user_input, user_id)

    def _resume_system(self, command: str, operator: str):
        """恢复系统运行
        :param command: 恢复系统的命令
        :param operator: 操作者的 ID
        """
        ResumeCommand(command, operator).execute(self.state)

    def _save_pending(self, text: str, user_id: str):
        """保存待处理请求
        :param text: 用户输入的文本
        :param user_id: 用户的 ID
        """
        # 获取或初始化待处理请求列表
        pending = self.state._state.setdefault("pending_inputs", [])
        # 将待处理请求添加到列表中
        pending.append((user_id, text))

    def _process_pending(self):
        """处理待处理请求
        """
        # 获取待处理请求列表
        pending = self.state._state.get("pending_inputs", [])
        if pending:
            print(f"[SYSTEM] Processing {len(pending)} pending requests")
            # 遍历待处理请求列表
            for user_id, text in pending:
                # 将处理请求的任务添加到任务队列中
                self.task_queue.put(self.handle_input, text, user_id)
            # 清空待处理请求列表
            self.state._state["pending_inputs"] = []

    def _process_input(self, text: str, user_id: str):
        """处理用户输入
        :param text: 用户输入的文本
        :param user_id: 用户的 ID
        """
        try:
            # 使用处理器处理用户输入
            response = self.processor.process(text, user_id)
            print(f"[BOT] {user_id}: {response}")
        except Exception as e:
            print(f"[ERROR] Processing failed: {str(e)}")