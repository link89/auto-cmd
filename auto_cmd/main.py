import sys
import fire


def cli():
    if sys.platform == 'darwin':
        from .mac import MacCmd
        fire.Fire(MacCmd)
