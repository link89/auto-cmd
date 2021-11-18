from .core import CommonCmd
import atomac
from atomac import NativeUIElement


class MacAutoCmd(CommonCmd):

    def find_app(self, name=None, pid=0, bundle_id=None):
        if name:
            app = atomac.getAppRefByLocalizedName(name)
        elif pid:
            app = atomac.getAppRefByPid(pid)
        elif bundle_id:
            app = atomac.getAppRefByBundleId(bundle_id)
        else:
            app = atomac.getFrontmostApp()
        return self._push(app)

    def find_element(self):
        result = self._pop()
        if isinstance(result, NativeUIElement):
            ...

    def find_elements(self):
        result = self._pop()
        if isinstance(result, NativeUIElement):
            ...






