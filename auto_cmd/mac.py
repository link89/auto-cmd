import atomac
from atomac import NativeUIElement
from typing import Iterable, List, Tuple, Callable
from pynput.mouse import Controller, Button

from .common import BaseCmd
from .filter import create_ldap_filter_fn

_mouse = Controller()


class WrappedElement:
    @classmethod
    def create_many(cls, els: Iterable[NativeUIElement], parent: 'WrappedElement' = None):
        return map(lambda el: cls(el, parent), els)

    def __init__(self, element: NativeUIElement, parent: 'WrappedElement' = None):
        self._element = element
        self._parent = parent

    def activate(self):
        self._element.activate()

    @property
    def children(self):
        children = ()
        try:
            children = self._element.AXChildren or ()
        except:
            pass
        return self.create_many(children, self)

    @property
    def center(self):
        x, y = self._element.AXPosition  # top-left
        w, h = self._element.AXSize
        return x + w // 2, y + h // 2

    @property
    def search_string(self):
        if not (self.title and self.role):
            return None
        return "'(&(role={})(title={}))'".format(
            format_assertion_value(self.role), format_assertion_value(self.title))

    @property
    def full_search_string(self):
        filters = []
        node = self
        while node:
            if node.search_string:
                prefix = 'select ' if node._parent is None else 'find '
                filters.insert(0, prefix + node.search_string)
            node = node._parent
        return ' - '.join(filters)

    @property
    def role(self):
        if 'AXRole' in self.attributes:
            return self._element.AXRole

    @property
    def title(self):
        if 'AXTitle' in self.attributes:
            return self._element.AXTitle

    @property
    def attributes(self):
        try:
            return self._element.getAttributes()
        except:
            return []

    def is_match(self, filter_fn: Callable[['WrappedElement'], bool]) -> bool:
        return filter_fn(self)

    def __str__(self):
        # TODO: json string
        printable_attrs = (
            'AXRole',
            'AXTitle',
            'AXPosition',
            'AXSize',
            'AXRoleDescription',
        )
        attrs = self.attributes
        s = '[\n'
        s += '\n'.join("{}: {}".format(attr, getattr(self._element, attr))
                       for attr in printable_attrs if attr in attrs)
        s += '\n' + "FullFilterString: " + self.full_search_string
        s += '\n]'
        return s

    def __repr__(self):
        return str(self)


def ensure_not_empty(stack: tuple):
    if not stack:
        raise ValueError("stack should not be empty!")


def ensure_wrapped_elements(x) -> Tuple[WrappedElement]:
    if not x:
        raise ValueError("Data is empty!")
    if isinstance(x, tuple) and isinstance(x[0], WrappedElement):
        return x
    raise ValueError("expect `Tuple[ElementWrapper]`, actual: {}: {}".format(type(x), str(x)))


class MacCmd(BaseCmd):

    def __init__(self, blob_type='base64', output_type='json'):
        super().__init__(blob_type, output_type)
        self._filter_fn_factory = lambda expr: create_ldap_filter_fn(expr, element_get_value)

    def select(self, filter=None, max_depth=0, limit=1):
        filter_fn = (lambda _: True) if filter is None else self._filter_fn_factory(filter)
        return self._search(filter_fn, max_depth, limit, chain=False)

    def find(self, filter=None, max_depth=0, limit=1):
        filter_fn = (lambda _: True) if filter is None else self._filter_fn_factory(filter)
        return self._search(filter_fn, max_depth, limit, chain=True)

    def nth(self, n: int):
        def action(stack: tuple) -> tuple:
            el = ensure_wrapped_elements(stack[-1])[n]
            return *stack[:-1], (el,)

        self._enqueue_action(action)
        return self

    def click(self):
        def action(stack):
            ensure_not_empty(stack)
            el = ensure_wrapped_elements(stack[-1])[0]
            _mouse.position = el.center
            _mouse.click(Button.left)
            return stack
        self._enqueue_action(action)
        return self

    def activate(self):
        def action(stack):
            ensure_not_empty(stack)
            el = ensure_wrapped_elements(stack[-1])[0]
            el.activate()
            return stack
        self._enqueue_action(action)
        return self

    def select_app(self, name=None, pid=0, bundle_id=None):
        def action(stack):
            if name:
                app = atomac.getAppRefByLocalizedName(name)
            elif pid:
                app = atomac.getAppRefByPid(pid)
            elif bundle_id:
                app = atomac.getAppRefByBundleId(bundle_id)
            else:
                app = atomac.getFrontmostApp()
            return *stack, (WrappedElement(app),)
        self._enqueue_action(action)
        return self

    def _search(self, filter_fn=lambda _: True, max_depth=0, limit=0, chain=True):
        def action(stack: tuple) -> tuple:
            result: List[WrappedElement] = []
            fifo: List[Tuple[int, WrappedElement]] = []  # (depth, node)
            if chain:  # search based on previous result
                ensure_not_empty(stack)
                els = ensure_wrapped_elements(stack[-1])
                fifo.extend(map(lambda _el: (0, _el), els))
            else:  # search from system root
                fifo.extend(map(lambda _el: (0, _el), get_running_apps()))
            # order travelling
            while fifo:
                depth, el = fifo.pop(0)
                if (not max_depth) or (depth + 1 < depth):
                    fifo.extend(map(lambda child: (depth + 1, child), el.children))
                if el.is_match(filter_fn):
                    result.append(el)
                    if limit and (len(result) >= limit):
                        break
            return *stack[:-1], tuple(result)
        self._enqueue_action(action)
        return self


def element_get_value(obj: WrappedElement, attr=None):
    if attr is None:
        return []
    if attr not in ['role', 'title']:
        return None
    return getattr(obj, attr)


def get_running_apps() -> Iterable[WrappedElement]:
    apps = []
    for app in NativeUIElement._getRunningApps():
        if app.isFinishedLaunching():
            pid = app.processIdentifier()
            apps.append(atomac.getAppRefByPid(pid))
    return WrappedElement.create_many(apps)


def format_assertion_value(s: str):
    return '"' + s.replace('"', '\\"').replace('\\', '\\\\') + '"'
