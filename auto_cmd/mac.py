import atomac
from atomac import NativeUIElement
from typing import Iterable, List, Tuple, Callable

from .common import BaseCmd
from .filter import create_ldap_filter_fn


class ElementWrapper:
    @classmethod
    def create_many(cls, els: Iterable[NativeUIElement], parent: 'ElementWrapper' = None):
        return map(lambda el: cls(el, parent), els)

    def __init__(self, element: NativeUIElement, parent: 'ElementWrapper' = None):
        self._element = element
        self._parent = parent

    def activate(self):
        self._element.activate()

    @property
    def children(self):
        children = []
        try:
            children = self._element.AXChildren or []
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
        return "find '(&(role={})(title={}))'".format(
            format_assertion_value(self.role), format_assertion_value(self.title))

    @property
    def full_search_string(self):
        filters = []
        node = self
        while node:
            s = node.search_string
            if s:
                if node._parent:
                    s += ' --chain'
                filters.insert(0, s)
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

    def is_match(self, filter_fn: Callable[['ElementWrapper'], bool]) -> bool:
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


class MacCmd(BaseCmd):

    def __init__(self, blob_type='base64', output_type='json'):
        super().__init__(blob_type, output_type)
        self._filter_fn_factory = lambda expr: create_ldap_filter_fn(expr, element_get_value)

    def find_many(self, filter=None, max_depth=0, limit=0, chain=True):
        filter_fn = (lambda _: True) if filter is None else self._filter_fn_factory(filter)

        def action(stack: tuple) -> tuple:
            result: List[ElementWrapper] = []
            fifo: List[Tuple[int, ElementWrapper]] = []  # (depth, node)
            if chain and stack:
                if isinstance(stack[-1], ElementWrapper):
                    fifo.append((0, stack[-1]))
                elif isinstance(stack[-1], tuple) and isinstance(stack[-1][0], ElementWrapper):
                    fifo.extend(map(lambda el: (0, el), stack[-1]))
                else:
                    raise ValueError("Top of result stack must be `ElementWrapper` or tuple of `ElementWrapper` when "
                                     "`chain` option is true")
            else:
                fifo.extend(map(lambda el: (0, el), get_running_apps()))
            # order travelling
            while fifo:
                depth, el = fifo.pop(0)
                if (not max_depth) or (depth + 1 < depth):
                    fifo.extend(map(lambda child: (depth + 1, child), el.children))
                if el.is_match(filter_fn):
                    result.append(el)
                    if limit and (len(result) >= limit):
                        break
            return *stack, result

        self._enqueue_action(action)
        return self

    def find(self, filter=None, max_depth=0, chain=True):
        self.find_many(filter, max_depth, limit=1, chain=chain)
        self.nth(0)
        return self

    def nth(self, n: int):
        def action(stack: tuple) -> tuple:
            # TODO: friendly error handling
            return *stack, stack[-1][n]
        self._enqueue_action(action)
        return self

    def click(self):
        ...

    def find_app(self, name=None, pid=0, bundle_id=None):
        def action(stack):
            if name:
                app = atomac.getAppRefByLocalizedName(name)
            elif pid:
                app = atomac.getAppRefByPid(pid)
            elif bundle_id:
                app = atomac.getAppRefByBundleId(bundle_id)
            else:
                app = atomac.getFrontmostApp()
            return *stack, ElementWrapper(app)
        self._enqueue_action(action)
        return self


def element_get_value(obj: ElementWrapper, attr=None):
    if attr is None:
        return []
    if attr not in ['role', 'title']:
        return None
    return getattr(obj, attr)


def get_running_apps() -> Iterable[ElementWrapper]:
    apps = []
    for app in NativeUIElement._getRunningApps():
        if app.isFinishedLaunching():
            pid = app.processIdentifier()
            apps.append(atomac.getAppRefByPid(pid))
    return ElementWrapper.create_many(apps)


def format_assertion_value(s: str):
    return '"' + s.replace('"', '\\"').replace('\\', '\\\\') + '"'
