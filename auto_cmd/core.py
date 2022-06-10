import fire
import time
import json
from typing import Tuple
from numbers import Real
from PIL import Image, ImageDraw
from pprint import pprint as print
import pytesseract
from pytesseract import Output
import base64
from io import BytesIO
import pandas as pd
import re
import mss
from functools import wraps
from .utils import get_stacktrace_from_exception, mouse_move


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


IS_OPERATOR = '__is_operator__'


def define_operator(func):
    setattr(func, IS_OPERATOR, True)
    return func


def is_operator(func):
    return getattr(func, IS_OPERATOR, False)


def get_operator(o, key):
    operator = getattr(o, key, None)
    return operator if is_operator(operator) else None


def get_operator_names(o):
    for key in dir(type(o)):
        if get_operator(o, key) is not None:
            yield key


# the delegation pattern is inspired by: https://www.fast.ai/2019/08/06/delegation/
class VirtualMachine:

    def __init__(self):
        self._permanent_operands = list()
        self._ephemeral_operand = None

    def health_check(self):
        return 'OK'

    @property
    def _operands(self):
        if self._ephemeral_operand is not None:
            yield self._ephemeral_operand
        yield from self._permanent_operands

    def __dir__(self):
        attributes = set()
        attributes.update(dir(type(self)))
        attributes.update(self.__dict__.keys())

        for operand in self._operands:
            attributes.update(get_operator_names(operand))

        return list(attributes)

    def __getattr__(self, key):
        for operand in self._operands:
            operator = get_operator(operand, key)
            if operator is not None:
                @wraps(operator)
                def wrapper(*args, **kwargs):
                    ret = operator(*args, **kwargs)
                    if ret is not None:
                        self._ephemeral_operand = ret
                    return self
                return wrapper
        else:
            raise AttributeError(key)

    def __str__(self):
        if isinstance(self._ephemeral_operand, Operand):
            return json.dumps(self._ephemeral_operand.to_data())
        else:
            return str(self._ephemeral_operand)


class DefaultVirtualMachine(VirtualMachine):

    def __init__(self):
        super().__init__()
        self._permanent_operands.insert(0, DefaultOperand())


class Operand:
    def to_data(self):
        return str(self)


class DefaultOperand(Operand):

    @define_operator
    def take_screenshot(self, n=1):
        with mss.mss() as sct:
            monitor = sct.monitors[n]
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return ScreenshotOperand(img, monitor)

    @define_operator
    def sleep(self, seconds: int):
        time.sleep(seconds)


class ImageOperand(Operand):

    def __init__(self, img: Image):
        self.img = img

    def to_base64(self):
        buffered = BytesIO()
        self.img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('ascii')

    @define_operator
    def debug(self):
        self.img.show()

    @define_operator
    def grayscale(self):
        self.img = self.img.convert('L')
        return self

    @define_operator
    def bi_level(self, black_range: Tuple[int, int]):
        a, b = black_range
        lut = lambda x: 0 if a <= x < b else 255
        self.img = self.img.point(lut, mode='1')
        return self

    @define_operator
    def tesseract(self, psm: int = 4, oem: int = 1):
        config = '--psm {} --oem {}'.format(psm, oem)
        ocr_df = pytesseract.image_to_data(self.img, config=config, output_type=Output.DATAFRAME)
        return TesseractResultOperand(self, ocr_df)

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

    def __init__(self, img: Image, monitor):
        super().__init__(img)
        self.monitor = monitor


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


class TesseractResultOperand(Operand):

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

    @define_operator
    def debug(self, level='word'):
        level_num = self.get_level_num(level)
        img = self._img_op.img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        for row in self._df.itertuples(name='Tesseract'):
            if row.level != level_num:
                continue
            draw.rectangle(((row.left, row.top), (row.left+row.width, row.top+row.height)), outline='green', width=1)
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


if __name__ == '__main__':
    fire.Fire(DefaultVirtualMachine)
