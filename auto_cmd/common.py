from typing import Callable, List
from pprint import pformat

ActionFnType = Callable[[tuple], tuple]


class BaseCmd:

    def __init__(self, blob_type='base64', output_type='json'):
        self._blob_type = blob_type
        self._output_type = output_type
        self._actions: List[ActionFnType] = []

    def _enqueue_action(self, action: ActionFnType):
        self._actions.append(action)

    def execute(self, max_tries=1, retry_interval=1e3):
        stack = tuple()
        for action in self._actions:
            stack = action(stack)
        return pformat(stack[-1])

    def __str__(self):
        return 'Call `execute` to run command and get result!'

