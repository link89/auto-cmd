from .core import CommonVm, Operand, RectangleOperand, has_implement_protocol
from typing import List
import atomac
from atomac import NativeUIElement


class MacUiElementOperand(Operand):
    def __init__(self, el: NativeUIElement):
        self.element = el

    def _order_iter_elements(self, max_depth=0):
        max_depth = max_depth if max_depth > 0 else 255  # limit max_depth to 255 to ensure return
        fifo = [(1, self.element)]  # item is tuple of depth, element
        while fifo:
            depth, element = fifo.pop(0)
            if depth > max_depth:
                break
            yield element
            try:
                children = element.AXChildren
                for child in children:
                    fifo.append((depth + 1, child))
            except Exception as e:
                pass

    def query_element(self, max_depth=0, **kwargs):
        for element in self._order_iter_elements(max_depth):
            try:
                found = element.findFirst(**kwargs)
                if found:
                    return MacUiElementOperand(found)
            except Exception as e:
                pass

    def query_elements(self, max_depth=0, limit=0, **kwargs):
        all_founds = []
        for element in self._order_iter_elements(max_depth):
            try:
                founds = element.findAll(**kwargs)
                all_founds.extend(map(MacUiElementOperand, founds))
                if 0 < limit <= len(all_founds):
                    return all_founds[0: limit]
            except Exception as e:
                pass
        return all_founds

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
        return RectangleOperand(x, y, w, h)

    def move_to(self, *args, **kwargs):
        return self.position.move_to(*args, **kwargs)

    def offset(self, *args, **kwargs):
        return self.area.offset(*args, **kwargs)

    def activate(self):
        return self.element.activate()

    def to_data(self):
        data = dict()
        for key in self.element.getAttributes():
            try:
                data[key] = getattr(self.element, key)
            except Exception as e:
                pass
        return data


class MacUiElementsOperand(Operand):
    def __init__(self, els: List[NativeUIElement]):
        self._elements = els

    @property
    def elements(self):
        return tuple(map(lambda o: MacUiElementOperand(o), self._elements))

    def to_data(self):
        return tuple(map(lambda o: o.to_data, self.elements))

    def debug(self):
        print(self._elements)


class MacAutoVm(CommonVm):

    def query_app(self, name=None, pid=0, bundle_id=None):
        if name:
            app = atomac.getAppRefByLocalizedName(name)
        elif pid:
            app = atomac.getAppRefByPid(pid)
        elif bundle_id:
            app = atomac.getAppRefByBundleId(bundle_id)
        else:
            app = atomac.getFrontmostApp()
        return self._push(MacUiElementOperand(app))

    def query_element(self, **kwargs):
        op = self._pop()
        if isinstance(op, MacUiElementOperand):
            return self._push(op.query_element(**kwargs))

    def query_elements(self, **kwargs):
        op = self._pop()
        if isinstance(op, MacUiElementOperand):
            return self._push(op.query_elements(**kwargs))

    def activate(self, *args, **kwargs):
        result = self._peek()
        if has_implement_protocol(result, 'activate'):
            result.activate(*args, **kwargs)
            return self
