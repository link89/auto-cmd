import atomac
from typing import Iterable
from atomac import NativeUIElement
from xml.etree import ElementPath
from enum import Enum, auto

from .core import BaseVm
from .utils import next_n


class XmlElement:
    @property
    def tag(self):
        return self.get('AXRole', '')

    @property
    def title(self):
        return self.get('AXTitle', '')

    @property
    def _children(self):
        native_children = None

        if self._element is None:
            native_children = iter_native_running_apps()
        else:
            try:
                native_children = self.get('AXChildren', ())
            except Exception as e:
                pass
        if native_children is None:
            native_children = ()

        for child in native_children:
            yield XmlElement(child)

    def __init__(self, native_element: NativeUIElement = None):
        self._element = native_element

    def __getitem__(self, index):
        return next_n(self._children, index)

    def get(self, key, default=None):
        if key not in self._element.getAttributes():
            return default
        return getattr(self._element, key, default)

    def iter(self, tag=None):
        if tag == "*":
            tag = None
        if tag is None or self.tag == tag:
            yield self
        for e in self._children:
            yield from e.iter(tag)

    def findall(self, path, namespaces=None):
        return ElementPath.findall(self, path, namespaces)

    def __repr__(self):
        return "<{} AXTitle={}>".format(self.tag, self.title)

    def _dump_xml(self, depth=0):
        children = tuple(self._children)
        if children:
            yield "  " * depth + "<{} AXTitle={}>".format(self.tag, self.title)
            for child in children:
                yield from child._dump_xml(depth + 1)
            yield "  " * depth + "</{}>".format(self.tag)
        else:
            yield "  " * depth + "<{} AXTitle={} />".format(self.tag, self.title)

    def dump_xml(self):
        return "\n".join(self._dump_xml())


class DataType(Enum):
    ELEMENT_IT = auto()


class MacAutoVm(BaseVm[DataType]):

    def select_app(self, name=None, pid=0, bundle_id=None):
        app = None
        if name:
            app = atomac.getAppRefByLocalizedName(name)
        elif pid:
            app = atomac.getAppRefByPid(pid)
        elif bundle_id:
            app = atomac.getAppRefByBundleId(bundle_id)
        else:
            app = atomac.getFrontmostApp()
        self._push_element_it(iter([XmlElement(app)]))
        return self

    def nth(self, n: int):
        element_it = self._pop_and_validate_element_it()
        element = next_n(element_it, n)
        self._push_element_it(iter([element]))
        return self

    def find(self, path: str):
        element_it = self._pop_and_validate_element_it()
        element_it = self._xpath_find(element_it, path)
        self._push_element_it(element_it)
        return self

    def print_xml(self):
        element_it = self._peak_and_validate_element_it()
        for element in element_it:
            print(element.dump_xml())
        return self

    def _xpath_find(self, element_it: Iterable[XmlElement], path: str = '') -> Iterable[XmlElement]:
        for element in element_it:
            yield from ElementPath.iterfind(element, path)

    def _pop_and_validate_element_it(self):
        dtype, element_it = self._pop_stack()
        self._validate_dtype(DataType.ELEMENT_IT, dtype)
        return element_it

    def _peak_and_validate_element_it(self):
        dtype, element_it = self._peek_stack()
        self._validate_dtype(DataType.ELEMENT_IT, dtype)
        return element_it

    def _push_element_it(self, element_it):
        self._push_stack(DataType.ELEMENT_IT, element_it)


def iter_native_running_apps():
    for app in NativeUIElement._getRunningApps():
        if app.isFinishedLaunching():
            pid = app.processIdentifier()
            yield atomac.getAppRefByPid(pid)
