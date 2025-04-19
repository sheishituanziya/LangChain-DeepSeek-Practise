# File: commands.py
class Command:
    """命令模式基类"""
    def execute(self, context: dict) -> None:
        raise NotImplementedError

class ResumeCommand(Command):
    """恢复系统命令"""
    def __init__(self, command_text, operator):
        self.command_text = command_text
        self.operator = operator

    def execute(self, state):
        """执行恢复命令"""
        # 验证恢复命令的合法性
        if self._is_valid_command(self.command_text):
            # 更新状态为未暂停
            state.update("paused", False)
            print(f"[RESUME] System resumed by {self.operator}")
        else:
            print(f"[ERROR] Invalid resume command: {self.command_text}")

    def _is_valid_command(self, command):
        """验证恢复命令是否合法"""
        # 可以添加复杂的验证逻辑
        return command.strip() == "admin123"
