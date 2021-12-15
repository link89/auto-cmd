from numbers import Real
import time
from functools import lru_cache
import tkinter as tk
from PIL import ImageGrab, Image, ImageDraw
from pprint import pprint
import pytesseract
from pytesseract import Output
import base64
from io import BytesIO
from collections import namedtuple
from pynput.mouse import Button, Controller
import pyvirtualcam
import numpy as np
import webbrowser
import json
import sys
from math import floor

from .utils import get_stacktrace_from_exception

# Singletons
mouse = Controller()


class AutoCmdError(Exception):
    def __init__(self, code: int, error: str, message: str, data: dict = None):
        self.code = code
        self.error = error
        self.message = message
        self.data = data

    def to_data(self):
        data = dict(
            code=self.code,
            error=self.error,
            message=self.message,
            stacktrace=get_stacktrace_from_exception(self),
        )
        if self.data is not None:
            data['data'] = self.data


class Result:
    def to_data(self):
        return str(self)


class RectResult(Result):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def position(self):
        return PositionResult(self.x + self.w / 2, self.y + self.h / 2)

    def move_to(self, *args, **kwargs):
        return self.position.move_to(*args, **kwargs)

    def debug(self):
        print(self.to_data())

    def scale(self, ratio: Real):
        return RectResult(self.x * ratio, self.y * ratio, self.w * ratio, self.h * ratio)

    def to_data(self):
        data = {
            'x': self.x,
            'y': self.y,
            'w': self.w,
            'h': self.h,
        }
        return data


class ImageResult(Result):
    def __init__(self, img: Image):
        self.img = img

    def debug(self):
        print(self.to_data(False))
        self.img.show()

    def to_base64(self):
        buffered = BytesIO()
        self.img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('ascii')

    def grayscale(self):
        img = self.img.convert('L')
        return ImageResult(img)

    def bi_level(self, a: int, b: int):
        lut = lambda x: 0 if a <= x < b else 255
        img = self.img.point(lut, mode='1')
        return ImageResult(img)

    def scale(self, ratio: Real):
        w, h = self.img.size
        img = self.img.resize((floor(w * ratio), floor(h * ratio)), resample=Image.ANTIALIAS)
        return ImageResult(img)

    def ocr(self, psm: int = 4, oem: int = 1):
        config = '--psm {} --oem {}'.format(psm, oem)
        results = pytesseract.image_to_data(self.img, config=config, output_type=Output.DICT)
        return TesseractOcrResult(self, results)

    def mask(self, op):
        area = op.area
        if isinstance(area, RectResult):
            back = Image.new(self.img.mode, self.img.size)
            mask = Image.new('L', self.img.size, 0)
            draw = ImageDraw.Draw(mask)
            left_top = (area.x, area.y)
            right_button = (area.x + area.w, area.y + area.h)
            # if the coordinate is relative, convert to absolute
            if all(map(lambda z: z <= 1, (*left_top, *right_button))):
                img_w, img_h = self.img.size
                left_top = (floor(left_top[0] * img_w), floor(left_top[1] * img_h))
                right_button = (floor(right_button[0] * img_w), floor(right_button[1] * img_h))
            draw.rectangle((left_top, right_button), fill=255)
            return ImageResult(Image.composite(self.img, back, mask))
        raise ValueError('area must be type one of RectResult')

    def to_data(self, with_content=True):
        w, h = self.img.size
        data = {
            'size': {
                'width': w,
                'height': h,
            },
            'type': 'image/png;base64',
        }
        if with_content:
            data['content'] = self.to_base64(),
        return data


TesseractItem = namedtuple('TesseractItem', [
    'level', 'page_num', 'block_num', 'par_num', 'line_num', 'word_num',
    'text', 'left', 'top', 'width', 'height', 'conf'])


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

    def find(self, text: str):
        level_num = self.get_level('word')
        for item in self.iter_results():
            if level_num != item.level or item.conf < 0:
                continue
            if item.text == text:
                return RectResult(item.left, item.top, item.width, item.height)

    def to_data(self):
        return self._results


class PositionResult(Result):

    def __init__(self, x: Real, y: Real):
        self.x = x
        self.y = y

    def offset(self, w: Real, h: Real):
        return PositionResult(self.x + w, self.x + h)

    def move_to(self, smooth=True):
        mouse_move(self.x, self.y, smooth)


class CommonCmd:
    is_quiet = False

    def __init__(self):
        self._stack = []

    def to_data(self):
        if not self._stack:
            return None
        ret = self._peek()
        if ret is None:
            return None
        if any(map(lambda cls: isinstance(ret, cls), [int, float, str])):
            return ret
        if has_implement_protocol(ret, 'to_data'):
            return ret.to_data()
        return str(ret)

    def __str__(self):
        if self.is_quiet:
            return str(self._peek())
        return json.dumps(self.to_data())

    def _push(self, result):
        self._stack.append(result)
        return self

    def _pop(self):
        return self._stack.pop()

    def _peek(self):
        return self._stack[-1]

    def health_check(self):
        return 'OK'

    def get_platform(self):
        return sys.platform

    def push_none(self):
        return self._push(None)

    def debug(self, *args, **kwargs):
        result = self._peek()
        if has_implement_protocol(result, 'debug'):
            result.debug(*args, **kwargs)
        else:
            pprint(self.to_data())

    def sleep(self, sec: int):
        time.sleep(sec)
        return self

    def to_base64(self):
        op = self._pop()
        if has_implement_protocol(op, 'to_base64'):
            return self._push(op.to_base64())

    def move_to(self, *args, **kwargs):
        op = self._peek()
        if has_implement_protocol(op, 'move_to'):
            op.move_to(*args, **kwargs)
            return self

    def click(self, button='left', count=1):
        mouse_click(button, count)
        return self

    def open_browser(self, *args, **kwargs):
        webbrowser.open(*args, **kwargs)
        return self

    def take_screenshot(self, from_clipboard=False):
        img = ImageGrab.grabclipboard() if from_clipboard else ImageGrab.grab()
        return self._push(ImageResult(img))

    def grayscale(self):
        op = self._pop()
        if has_implement_protocol(op, 'grayscale'):
            return self._push(op.grayscale)

    def bi_level(self, *args, **kwargs):
        op = self._pop()
        if has_implement_protocol(op, 'bi_level'):
            return self._push(op.bi_level(*args, **kwargs))

    def scale(self, *args, **kwargs):
        op = self._pop()
        if has_implement_protocol(op, 'scale'):
            return self._push(op.scale(*args, **kwargs))

    def mask(self, *args, **kwargs):
        op2 = self._pop()
        op1 = self._pop()
        if has_implement_protocol(op1, 'mask'):
            return self._push(op1.mask(op2, *args, **kwargs))

    def nullify_display_scale(self):
        return self.scale(1 / get_screen_scale_ratio())

    def ocr(self, *args, **kwargs):
        op = self._pop()
        if has_implement_protocol(op, 'ocr'):
            return self._push(op.ocr(*args, **kwargs))

    def find(self, *args, **kwargs):
        op = self._pop()
        if has_implement_protocol(op, 'find'):
            return self._push(op.find(*args, **kwargs))


def send_video_to_virtual_camera(timeout = 10):
    with pyvirtualcam.Camera(width=1280, height=720, fps=20) as cam:
        print(f'Using virtual camera: {cam.device}')
        frame = np.zeros((cam.height, cam.width, 3), np.uint8)  # RGB
        due = time.time() + timeout

        while time.time() < due:
            frame[:] = cam.frames_sent % 255  # grayscale animation
            cam.send(frame)
            cam.sleep_until_next_frame()


def get_pynput_mouse_button(button: str):
    return {
        'left': Button.left,
        'right': Button.right,
    }[button]


def mouse_move(x, y, smooth=True):
    old_x, old_y = mouse.position
    for i in range(100):
        intermediate_x = old_x + (x - old_x) * (i + 1) / 100.0
        intermediate_y = old_y + (y - old_y) * (i + 1) / 100.0
        mouse.position = (intermediate_x, intermediate_y)
        if smooth:
            time.sleep(.01)


def mouse_click(button='left', count=1):
    mouse.click(get_pynput_mouse_button(button), count)


def has_implement_protocol(obj, proto: str):
    return hasattr(obj, proto) and callable(getattr(obj, proto))


@lru_cache(maxsize=None)
def get_screen_size():
    root = tk.Tk()
    size = root.winfo_screenwidth(), root.winfo_screenheight()
    root.destroy()
    return size


@lru_cache(maxsize=None)
def get_resolution():
    return ImageGrab.grab().size


@lru_cache(maxsize=None)
def get_screen_scale_ratio():
    resolution = get_resolution()
    screen_size = get_screen_size()
    return resolution[0] / screen_size[0]
