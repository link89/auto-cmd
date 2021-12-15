from .core import CommonCmd, Result, PositionResult, RectResult
from typing import List
import atomac
from atomac import NativeUIElement


class MacUiElementResult(Result):
    def __init__(self, el: NativeUIElement):
        self.element = el

    @property
    def size(self):
        return tuple(getattr(self.element, 'AXSize'))

    @property
    def position(self):
        return self.area.position

    @property
    def area(self):
        x, y = getattr(self.element, 'AXPosition')
        w, h = self.size
        return RectResult(x, y, w, h)

    def move_to(self, *args, **kwargs):
        return self.position.move_to(*args, **kwargs)

    def to_data(self):
        data = dict()
        for key in self.element.getAttributes():
            if key not in {'AXParent', 'AXTopLevelUIElement', 'AXWindow', 'AXFrame',
                           'AXServesAsTitleForUIElements', 'AXChildren'}:
                try:
                    data[key] = getattr(self.element, key)
                except Exception as e:
                    pass
        return data


class MacUiElementsResult(Result):
    def __init__(self, els: List[NativeUIElement]):
        self._elements = els

    def to_data(self):
        pass

    def debug(self):
        print(self._elements)


class MacAutoCmd(CommonCmd):

    def query_app(self, name=None, pid=0, bundle_id=None):
        if name:
            app = atomac.getAppRefByLocalizedName(name)
        elif pid:
            app = atomac.getAppRefByPid(pid)
        elif bundle_id:
            app = atomac.getAppRefByBundleId(bundle_id)
        else:
            app = atomac.getFrontmostApp()
        return self._push(MacUiElementResult(app))

    def query_element(self, recursive=False, **kwargs):
        result = self._pop()
        if isinstance(result, MacUiElementResult):
            if recursive:
                element = result.element.findFirstR(**kwargs)
            else:
                element = result.element.findFirst(**kwargs)
            return self._push(MacUiElementResult(element))

    def query_elements(self, recursive=False, **kwargs):
        result = self._pop()
        if isinstance(result, MacUiElementResult):
            if recursive:
                elements = result.element.findAllR(**kwargs)
            else:
                elements = result.element.findAll(**kwargs)
            return self._push(MacUiElementsResult(elements))
