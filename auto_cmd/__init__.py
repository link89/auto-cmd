import sys


def _get_cmd_class():
    if sys.platform == 'darwin':
        from .mac import MacAutoCmd
        return MacAutoCmd
    # TODO: windows


AutoCmd = _get_cmd_class()

