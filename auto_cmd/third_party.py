from .core import CommonVm
from guibot import guibot_simple
from guibot.config import GlobalConfig


class GuibotSimpleVm(CommonVm):

    def __init__(self, display_control_backend='autopy'):
        super().__init__()
        GlobalConfig.display_control_backend = display_control_backend
        guibot_simple.initialize()

    def exists(self, target: str, timeout: int=0):
        guibot_simple.exists(target, timeout)
        return self

    def click(self, target: str):
        guibot_simple.click(target)
        return self

    def right_click(self, target: str):
        guibot_simple.right_click(target)
        return self

    def hover(self, target: str):
        guibot_simple.hover(target)
        return self

    def type_text(self, text: str):
        guibot_simple.type_text(text)
        return self
