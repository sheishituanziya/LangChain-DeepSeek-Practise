# File: task_executor.py
import queue
import threading
import concurrent.futures

class TaskQueue:
    """线程安全任务队列（观察者模式）
    该类实现了一个线程安全的任务队列，支持添加任务、获取任务，
    并使用观察者模式，当有新任务添加时通知观察者。
    """
    def __init__(self):
        # 初始化一个线程安全的队列
        self._queue = queue.Queue()
        # 存储观察者的列表
        self._observers = []
        # 用于控制队列是否关闭的事件标志
        self._shutdown_flag = threading.Event()

    def add_observer(self, observer):
        """添加观察者
        :param observer: 观察者对象，需要实现 on_task_added 方法
        """
        self._observers.append(observer)

    def put(self, task, *args, **kwargs):
        """向队列中添加任务
        :param task: 要执行的任务函数
        :param args: 任务函数的位置参数
        :param kwargs: 任务函数的关键字参数
        """
        # 如果队列没有关闭
        if not self._shutdown_flag.is_set():
            # 将任务及其参数封装成元组添加到队列中
            self._queue.put((task, args, kwargs))
            # 通知所有观察者有新任务添加
            self._notify_observers()

    def _notify_observers(self):
        """通知所有观察者有新任务添加
        """
        for observer in self._observers:
            observer.on_task_added()

    def get(self):
        """从队列中获取任务
        :return: 任务及其参数的元组，如果队列为空则返回 None
        """
        try:
            # 非阻塞地从队列中获取任务
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def shutdown(self):
        """关闭队列
        """
        # 设置关闭标志
        self._shutdown_flag.set()

class ThreadPoolManager:
    """线程池管理（工厂模式）
    该类负责管理线程池，从任务队列中获取任务并提交到线程池中执行，
    同时支持优雅地关闭线程池。
    """
    def __init__(self, task_queue: TaskQueue, max_workers=5):
        """初始化线程池管理器
        :param task_queue: 任务队列对象
        :param max_workers: 线程池中的最大工作线程数，默认为 5
        """
        self.task_queue = task_queue
        # 创建一个线程池执行器
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        # 创建一个工作线程，用于从任务队列中获取任务并分发到线程池
        self._worker = threading.Thread(target=self._dispatch, daemon=True)
        # 启动工作线程
        self._worker.start()

    def _dispatch(self):
        """任务分发方法
        该方法在工作线程中运行，不断从任务队列中获取任务并提交到线程池执行。
        """
        while True:
            # 从任务队列中获取任务
            task = self.task_queue.get()
            if not task:
                # 如果队列为空且队列已关闭，则退出循环
                if self.task_queue._shutdown_flag.is_set():
                    break
                continue
            # 将任务提交到线程池执行
            self.executor.submit(self._execute_task, *task)

    def _execute_task(self, task, args, kwargs):
        """执行任务
        :param task: 要执行的任务函数
        :param args: 任务函数的位置参数
        :param kwargs: 任务函数的关键字参数
        """
        try:
            # 执行任务
            task(*args, **kwargs)
        except Exception as e:
            print(f"[ERROR] Task failed: {e}")

    def graceful_shutdown(self, timeout=5):
        """优雅地关闭线程池
        :param timeout: 等待线程池关闭的最大时间，默认为 5 秒
        """
        print("\n[SHUTDOWN] Initiating graceful shutdown...")
        # 关闭任务队列
        self.task_queue.shutdown()
        # 关闭线程池，等待所有任务完成
        self.executor.shutdown(wait=True, cancel_futures=True)
        print("[SHUTDOWN] All resources released")