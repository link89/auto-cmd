from PIL import ImageGrab, Image
from pprint import pprint
import pytesseract
from pytesseract import Output

class Result:
    pass


class ImageResult(Result):
    def __init__(self, img: Image):
        self.img = img

    def debug(self):
        pprint(self.img.info)
        self.img.show()

    def to_base64(self):
        pass


class TesseractOcrResult(Result):
    def __init__(self, data):
        self._data = data

    def debug(self):
        pprint(self._data)


class BaseVm:
    def __init__(self):
        self._stack = []

    def _push(self, result):
        self._stack.append(result)
        return self

    def _pop(self):
        return self._stack.pop()

    def to_base64(self):
        result = self._pop()
        if callable(getattr(result, 'to_base64')):
            return result.to_base64()

    def debug(self):
        result = self._pop()
        if callable(getattr(result, 'debug')):
            return result.debug()

    def take_screenshot(self, from_clipboard=False):
        img = ImageGrab.grabclipboard() if from_clipboard else ImageGrab.grab()
        return self._push(ImageResult(img))

    def grayscale(self):
        result = self._pop()
        if isinstance(result, ImageResult):
            img = result.img.convert('L')
            return self._push(ImageResult(img))

    def bi_level(self, range: tuple):
        result = self._pop()
        if type(range) is not tuple:
            raise Exception('unsupported input')
        if isinstance(result, ImageResult):
            lut = lambda x: 255 if range[0] <= x < range[1] else 0
            img = result.img.point(lut, mode='1')
            return self._push(ImageResult(img))

    def resize(self, ratio: int):
        result = self._pop()
        if isinstance(result, ImageResult):
            w, h = result.img.size
            img = result.img.resize((w * ratio, h * ratio), resample=Image.ANTIALIAS)
            return self._push(ImageResult(img))

    def ocr(self, psm: int = None, oem: int = None):
        result = self._pop()

        if isinstance(result, ImageResult):
            options = []
            if psm is not None:
                options.append('--psm ' + str(psm))
            if oem is not None:
                options.append('--oem ' + str(oem))
            config = ' '.join(options) if options else ''
            data = pytesseract.image_to_data(result.img, config=config, output_type=Output.DICT)
            return self._push(TesseractOcrResult(data))
