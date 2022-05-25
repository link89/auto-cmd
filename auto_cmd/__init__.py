import sys


def _get_cmd_class():
    if sys.platform == 'darwin':
        from .mac import MacAutoVm
        return MacAutoVm
    if sys.platform == 'win32':
        from .win import WinAutoVm
        return WinAutoVm

AutoCmd = _get_cmd_class()

