from numbers import Real
import time
from PIL import Image, ImageDraw
from pprint import pprint as print
import pytesseract
from pytesseract import Output
import base64
from io import BytesIO
import numpy as np
import pandas as pd
import webbrowser
import json
import sys
import re
from math import floor
import mss

from .utils import get_stacktrace_from_exception, mouse_click, mouse_move


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
            if row.level == word_level and isinstance(row.text, str) and pattern.fullmatch(row.text):
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
        pass

    def _push(self, op):
        self._stack.append(op)
        return self

    def _pop(self):
        return self._stack.pop()

    def _peek(self):
        return self._stack[-1]

    def health_check(self):
        return 'OK'

    def echo(self, text):
        return text

    def get_platform(self):
        return sys.platform

    def send_keys(self, keys: list):
        pass

    def tap_key(self, key: str):
        pass

    def press_key(self, key: str):
        pass

    def release_key(self, key: str):
        pass

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


def has_implement_protocol(obj, proto: str):
    return hasattr(obj, proto) and callable(getattr(obj, proto))


IS_OPERATOR = 'is_operator'


def define_operator(func):
    setattr(func, IS_OPERATOR, True)
    return func


def is_operator(func):
    return getattr(func, IS_OPERATOR, False)


def get_operator(o, key):
    operator = getattr(o, key, None)
    return operator if is_operator(operator) else None


def get_operator_names(o):
    for key in o.__dict__.keys():
        if get_operator(o, key) is not None:
            yield key


# the delegation pattern is inspired by: https://www.fast.ai/2019/08/06/delegation/
class VirtualMachine:

    def __init__(self):
        self._permanent_operands = list()
        self._ephemeral_operand = None

    @property
    def _operands(self):
        yield from self._permanent_operands
        if self._ephemeral_operand is not None:
            yield self._ephemeral_operand

    def __dir__(self):
        attributes = set()
        attributes.update(dir(type(self)))
        attributes.update(self.__dict__.keys())

        for operand in self._operands:
            attributes.update(get_operator_names(operand))
        return list(attributes)

    def __getattr__(self, key):
        for operand in self._operands:
            pass
