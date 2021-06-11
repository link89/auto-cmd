from typing import TypeVar, Generic, Tuple, Any, List

T = TypeVar('T')


class BaseVm(Generic[T]):

    def __init__(self, blob_type='base64', output_type='json'):
        self._blob_type = blob_type
        self._output_type = output_type

        self._stack: List[Tuple[T, Any]] = []

    def _pop_stack(self) -> Tuple[T, Any]:
        return self._stack.pop(0)

    def _peek_stack(self) -> Tuple[T, Any]:
        return self._stack[0]

    def _push_stack(self, dtype: T, data: Any):
        self._stack.append((dtype, data))

    def _validate_dtype(self, expect: T, actual: T):
        assert actual == expect, "Expect: {}, Actual {}".format(expect, actual)

    def __str__(self):
        return ''

    def __repr__(self):
        return ''
