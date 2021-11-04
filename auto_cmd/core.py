from PIL import ImageGrab, Image, ImageDraw
from pprint import pprint
import pytesseract
from pytesseract import Output
import base64
from io import BytesIO
from collections import namedtuple
from pynput.mouse import Button, Controller


# Singletons
mouse = Controller()


class Result:
    pass


class ImageResult(Result):
    def __init__(self, img: Image, scale: int):
        self.img = img
        self.scale = scale

    def debug(self):
        pprint(self.img.info)
        pprint(self.img.size)
        self.img.show()

    def to_base64(self):
        buffered = BytesIO()
        self.img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue())


TesseractItem = namedtuple('TesseractItem', [
    'level', 'page_num', 'block_num', 'par_num', 'line_num', 'word_num',
    'text',
    'left', 'top', 'width', 'height', 'conf'])


class RectResult(Result):

    def __init__(self, x, y, w, h):
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    @property
    def center(self):
        return self._x + self._w / 2, self._y + self._h / 2

    def debug(self):
        img = ImageGrab.grab()
        draw = ImageDraw.Draw(img)
        draw.rectangle(((self._x, self._y), (self._x + self._w, self._y + self._h)), outline='green', width=10)
        print((self._x, self._y, self._w, self._h))
        img.show()


class TesseractOcrResult(Result):

    @staticmethod
    def get_level(name: str):
        return {
            'page': 1,
            'block': 2,
            'paragraph': 3,
            'par': 3,
            'line': 4,
            'word': 5,
        }[name]

    def __init__(self, img_result: ImageResult, results):
        self._img_result = img_result
        self._results = results

    def iter_results(self):
        for i, _ in enumerate(self._results["text"]):
            yield TesseractItem(
                level=self._results["level"][i],
                page_num=self._results["page_num"][i],
                block_num=self._results["block_num"][i],
                par_num=self._results["par_num"][i],
                line_num=self._results["line_num"][i],
                word_num=self._results["word_num"][i],
                text=self._results["text"][i],
                top=self._results["top"][i],
                left=self._results["left"][i],
                width=self._results["width"][i],
                height=self._results["height"][i],
                conf=self._results["conf"][i],
            )

    def debug(self, level='word'):
        level_num = self.get_level(level)
        img = self._img_result.img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        for item in self.iter_results():
            if level_num != item.level:
                continue
            draw.rectangle(((item.left, item.top), (item.left+item.width, item.top+item.height)), outline='green', width=4)
            print("=" * 30)
            print("text: {}".format(item.text))
            print("location: x, y: {}, {}, w, h: {}, {}".format(item.left, item.top, item.width, item.height))
            print("conf: {}".format(item.conf))
        img.show()

    def locate_by_text(self, text: str):
        level_num = self.get_level('word')
        for item in self.iter_results():
            if level_num != item.level or item.conf < 0:
                continue
            if item.text == text:
                scale = self._img_result.scale
                return RectResult(item.left / scale, item.top / scale, item.width / scale, item.height / scale)


class BaseVm:

    @staticmethod
    def get_mouse_button(button: str):
        return {
            'left': Button.left,
            'right': Button.right,
        }[button]

    def __init__(self):
        self._stack = []

    def _push(self, result):
        self._stack.append(result)
        return self

    def _pop(self):
        return self._stack.pop()

    def _peek(self):
        return self._stack[-1]

    def to_base64(self):
        result = self._pop()
        if callable(getattr(result, 'to_base64')):
            return result.to_base64()

    def debug(self, *args, **kwargs):
        result = self._pop()
        if callable(getattr(result, 'debug')):
            return result.debug(*args, **kwargs)

    def click(self, button='left', count=1):
        result = self._peek()
        if isinstance(result, RectResult):
            mouse.move(*result.center)
            mouse.click(self.get_mouse_button(button), count)
            return self

    def take_screenshot(self, from_clipboard=False):
        img = ImageGrab.grabclipboard() if from_clipboard else ImageGrab.grab()
        return self._push(ImageResult(img, 1))

    def grayscale(self):
        result = self._pop()
        if isinstance(result, ImageResult):
            img = result.img.convert('L')
            return self._push(ImageResult(img, result.scale))

    def bi_level(self, range: tuple):
        result = self._pop()
        if type(range) is not tuple:
            raise Exception('unsupported input')
        if isinstance(result, ImageResult):
            lut = lambda x: 0 if range[0] <= x < range[1] else 255
            img = result.img.point(lut, mode='1')
            return self._push(ImageResult(img, result.scale))

    def resize(self, ratio: int):
        result = self._pop()
        if isinstance(result, ImageResult):
            w, h = result.img.size
            img = result.img.resize((w * ratio, h * ratio), resample=Image.ANTIALIAS)
            return self._push(ImageResult(img, ratio))

    def ocr(self, psm: int = 4, oem: int = 1):
        result = self._pop()
        if isinstance(result, ImageResult):
            config = '--psm {} --oem {}'.format(psm, oem)
            results = pytesseract.image_to_data(result.img, config=config, output_type=Output.DICT)
            return self._push(TesseractOcrResult(result, results))

    def locate_by_text(self, text: str):
        result = self._pop()
        if isinstance(result, TesseractOcrResult):
            loc = result.locate_by_text(text)
            if loc is None:
                raise Exception("cannot find the text")
            return self._push(loc)

