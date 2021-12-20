import traceback
from typing import List
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import time

_mouse = MouseController()
_keyboard = KeyboardController()


def get_pynput_mouse_button(button: str):
    return {
        'left': Button.left,
        'right': Button.right,
    }[button]


def mouse_move(x, y, smooth=True):
    old_x, old_y = _mouse.position
    for i in range(100):
        intermediate_x = old_x + (x - old_x) * (i + 1) / 100.0
        intermediate_y = old_y + (y - old_y) * (i + 1) / 100.0
        _mouse.position = (intermediate_x, intermediate_y)
        if smooth:
            time.sleep(.01)


def mouse_click(button='left', count=1):
    _mouse.click(get_pynput_mouse_button(button), count)


def validate_key(key: str):
    if key not in Key._member_names_:
        raise ValueError("{} is not a valid key".format(key))


def press_key(key: str):
    validate_key(key)
    _keyboard.press(key)


def release_key(key: str):
    validate_key(key)
    _keyboard.release(key)


def tap_key(key: str):
    validate_key(key)
    _keyboard.tap(key)


def send_keys(keys: List[str]):
    pairs = dict()
    for key in keys:
        if key.startswith('^'):
            key = key[1:]



    pass


def get_stacktrace_from_exception(e: Exception):
    return "".join(traceback.TracebackException.from_exception(e).format())
