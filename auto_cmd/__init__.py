import sys


def _get_cmd_class():
    if sys.platform == 'darwin':
        from .mac import MacAutoVm
        return MacAutoVm
    # TODO: windows


AutoCmd = _get_cmd_class()

