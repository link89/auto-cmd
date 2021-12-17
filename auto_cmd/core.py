from numbers import Real
import time
from PIL import Image, ImageDraw
from pprint import pprint as print
import pytesseract
from pytesseract import Output
import base64
from io import BytesIO
from pynput.mouse import Button, Controller
import pyvirtualcam
import numpy as np
import pandas as pd
import webbrowser
import json
import sys
import re
from math import floor
import mss

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


class Operand:
    def to_data(self):
        return str(self)


class RectangleOperand(Operand):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def position(self):
        return PositionOperand(self.x + self.w / 2, self.y + self.h / 2)

    def offset(self, w: Real, h: Real):
        return RectangleOperand(self.x + w, self.y + h, self.w, self.h)

    def move_to(self, *args, **kwargs):
        return self.position.move_to(*args, **kwargs)

    def debug(self):
        print(self.to_data())

    def scale(self, ratio: Real):
        return RectangleOperand(self.x * ratio, self.y * ratio, self.w * ratio, self.h * ratio)

    def to_data(self):
        data = {
            'x': self.x,
            'y': self.y,
            'w': self.w,
            'h': self.h,
        }
        return data


class ImageOperand(Operand):

    def __init__(self, img: Image):
        self.img = img

    def debug(self):
        self.img.show()

    def to_base64(self):
        buffered = BytesIO()
        self.img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('ascii')

    def grayscale(self):
        self.img = self.img.convert('L')
        return self

    def bi_level(self, a: int, b: int):
        lut = lambda x: 0 if a <= x < b else 255
        self.img = self.img.point(lut, mode='1')
        return self

    def scale(self, ratio: Real):
        w, h = self.img.size
        self.img = self.img.resize((floor(w * ratio), floor(h * ratio)), resample=Image.ANTIALIAS)
        return self

    def ocr(self, psm: int = 4, oem: int = 1):
        config = '--psm {} --oem {}'.format(psm, oem)
        ocr_df = pytesseract.image_to_data(self.img, config=config, output_type=Output.DATAFRAME)
        return TesseractOcrOperand(self, ocr_df)

    def mask(self, op):
        area = op.area
        if isinstance(area, RectangleOperand):
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
            self.img = Image.composite(self.img, back, mask)
            return self
        raise ValueError('area must be type one of RectOprand')

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


class ScreenshotOperand(ImageOperand):

    bound = None  # dict with keys: left, top, width, height

    @classmethod
    def take_screenshot(cls, n=1):
        with mss.mss() as sct:
            monitor = sct.monitors[n]
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            screenshot = cls(img)
            screenshot.bound = monitor
            return screenshot

    @property
    def scale_ratio(self):
        return self.bound['width'] / self.img.size[0]

    @property
    def offset(self):
        return self.bound['left'], self.bound['top']


class TesseractOcrOperand(Operand):

    @staticmethod
    def get_level_num(name: str):
        return {
            'page': 1,
            'block': 2,
            'paragraph': 3,
            'par': 3,
            'line': 4,
            'word': 5,
        }[name]

    @staticmethod
    def get_level_col(name: str):
        return {
            'page': 'page_num',
            'block': 'block_num',
            'paragraph': 'par_num',
            'par': 'par_num',
            'line': 'line_num',
            'word': 'word_num',
        }[name]

    def __init__(self, img_op: ImageOperand, df: pd.DataFrame):
        self._img_op = img_op
        self._df = df  # level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text

    def debug(self, level='word'):
        level_num = self.get_level_num(level)
        img = self._img_op.img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        for row in self._df.itertuples(name='Tesseract'):
            if row.level != level_num:
                continue
            draw.rectangle(((row.left, row.top), (row.left+row.width, row.top+row.height)), outline='green', width=4)
        img.show()

    def find(self, text: str, level='word', **kwargs):
        if 'word' == level:
            return self._find_word(text, **kwargs)

    def _find_word(self, text: str, ignore_case=True):
        word_level = self.get_level_num('word')
        flag = re.IGNORECASE if ignore_case else 0
        pattern = re.compile(text, flag)
        for row in self._df.itertuples(name='Tesseract'):
            if row.level == word_level and isinstance(row.text, str) and pattern.match(row.text):
                rect = RectangleOperand(row.left, row.top, row.width, row.height)
                if isinstance(self._img_op, ScreenshotOperand):
                    print(self._img_op.offset)
                    rect = rect.scale(self._img_op.scale_ratio).offset(*self._img_op.offset)
                return rect

    def to_data(self):
        return self._df.to_dict()


class PositionOperand(Operand):

    def __init__(self, x: Real, y: Real):
        self.x = x
        self.y = y

    def offset(self, w: Real, h: Real):
        return PositionOperand(self.x + w, self.y + h)

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
        return json.dumps(self.to_data(), default=lambda o: str(type(o)))

    def _push(self, op):
        self._stack.append(op)
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
        op = self._peek()
        if has_implement_protocol(op, 'debug'):
            op.debug(*args, **kwargs)
        else:
            print(self.to_data())
        return self

    def sleep(self, sec: int):
        time.sleep(sec)
        return self

    def to_base64(self):
        op = self._pop()
        if has_implement_protocol(op, 'to_base64'):
            return self._push(op.to_base64())

    def offset(self, *args, **kwargs):
        op = self._pop()
        if has_implement_protocol(op, 'offset'):
            return self._push(op.offset(*args, **kwargs))

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

    def take_screenshot(self, n=1):
        return self._push(ScreenshotOperand.take_screenshot(n))

    def grayscale(self):
        op = self._pop()
        if has_implement_protocol(op, 'grayscale'):
            return self._push(op.grayscale())

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
