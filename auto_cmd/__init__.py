import sys


def _get_cmd_class():
    if sys.platform == 'darwin':
        from .mac import MacAutoCmd
        return MacAutoCmd
    if sys.platform == 'win32':
        from .win import WinAutoCmd
        return WinAutoCmd

AutoCmd = _get_cmd_class()

