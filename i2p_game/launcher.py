"""Application entry points for Pygame and Tkinter."""

from .config import (
    BG, HEIGHT, MAX_WINDOW_SCALE, MIN_WINDOW_SCALE, WIDTH,
)
from .interface import Interface
from .canvas import PygameCanvas, TkCanvas
from time import perf_counter
import os

KEY_NAMES = {
    'return': 'enter',
    'kp_enter': 'enter',
    'kp enter': 'enter',
    'kp_1': '1',
    'kp_2': '2',
    'kp_3': '3',
    'kp_4': '4',
    'kp_5': '5',
    '[1]': '1',
    '[2]': '2',
    '[3]': '3',
    '[4]': '4',
    '[5]': '5',
}

SCANCODE_SHORTCUT_KEYS = {
    4: 'a', 7: 'd', 8: 'e', 11: 'h', 19: 'p', 20: 'q', 21: 'r',
    24: 'u', 26: 'w', 22: 's', 30: '1', 31: '2', 32: '3', 33: '4',
    34: '5', 40: 'enter', 41: 'escape', 42: 'backspace', 43: 'tab',
    44: 'space', 79: 'right', 80: 'left', 81: 'down', 82: 'up',
    225: 'shift', 229: 'shift',
}
WINDOWS_PHYSICAL_VKS = {
    'w': 0x57, 'a': 0x41, 's': 0x53, 'd': 0x44,
    'h': 0x48, 'q': 0x51, 'r': 0x52, 'u': 0x55, 'p': 0x50,
    '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35,
    'space': 0x20, 'enter': 0x0D, 'escape': 0x1B, 'backspace': 0x08,
    'tab': 0x09, 'left': 0x25, 'up': 0x26, 'right': 0x27,
    'down': 0x28, 'shift': 0x10,
}
_windows_get_async_key_state = None
_windows_key_state_loaded = False

# Taiwan Zhuyin keyboard positions for letter shortcuts. Keep the UI labels in
# Latin letters while accepting the symbol emitted by a Chinese IME.
ZHUYIN_KEY_NAMES = {
    'ㄆ': 'q', 'ㄊ': 'w', 'ㄍ': 'e', 'ㄐ': 'r', 'ㄔ': 't',
    'ㄗ': 'y', 'ㄧ': 'u', 'ㄛ': 'i', 'ㄟ': 'o', 'ㄣ': 'p',
    'ㄇ': 'a', 'ㄋ': 's', 'ㄎ': 'd', 'ㄑ': 'f', 'ㄕ': 'g',
    'ㄘ': 'h', 'ㄨ': 'j', 'ㄜ': 'k', 'ㄠ': 'l',
    'ㄈ': 'z', 'ㄌ': 'x', 'ㄏ': 'c', 'ㄒ': 'v', 'ㄖ': 'b',
    'ㄙ': 'n', 'ㄩ': 'm',
}


def normalize_key(name):
    name = name.lower()
    return KEY_NAMES.get(name, ZHUYIN_KEY_NAMES.get(name, name))


def windows_pressed_physical_keys():
    """Read physical key state even when a Windows IME translates key text."""
    global _windows_get_async_key_state, _windows_key_state_loaded
    if os.name != 'nt':
        return set()
    if not _windows_key_state_loaded:
        _windows_key_state_loaded = True
        try:
            import ctypes
            _windows_get_async_key_state = ctypes.windll.user32.GetAsyncKeyState
        except (AttributeError, OSError):
            _windows_get_async_key_state = None
    if _windows_get_async_key_state is None:
        return set()
    return {
        name for name, virtual_key in WINDOWS_PHYSICAL_VKS.items()
        if _windows_get_async_key_state(virtual_key) & 0x8000
    }


def bounded_window_size(width, height, display_width=None, display_height=None):
    """Keep a resizable window inside both the scale and display limits."""
    scale = min(width / WIDTH, height / HEIGHT)
    max_scale = MAX_WINDOW_SCALE
    if display_width and display_height:
        max_scale = min(max_scale, display_width / WIDTH, display_height / HEIGHT)
    scale = max(min(MIN_WINDOW_SCALE, max_scale), min(max_scale, scale))
    return round(WIDTH * scale), round(HEIGHT * scale)


def initial_window_size(pygame):
    """Use the largest allowed aspect-preserving window that fits the display."""
    info = pygame.display.Info()
    display_width = getattr(info, 'current_w', 0)
    display_height = getattr(info, 'current_h', 0)
    if display_width <= 0 or display_height <= 0:
        return round(WIDTH * MAX_WINDOW_SCALE), round(HEIGHT * MAX_WINDOW_SCALE)

    return bounded_window_size(
        display_width, display_height, display_width, display_height
    )


def run_pygame(pygame):
    pygame.display.init()
    pygame.font.init()
    try:
        initial_size = initial_window_size(pygame)
        screen = pygame.display.set_mode(initial_size, pygame.RESIZABLE)
        pygame.display.set_caption('大禮堂防衛戰 | Auditorium Defense')
        clock = pygame.time.Clock()
        interface = Interface(PygameCanvas(pygame, screen))
        windows_keys = set()
        window_focused = True
        while True:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type in (pygame.VIDEORESIZE,
                                  getattr(pygame, 'WINDOWRESIZED', -1)):
                    requested_width = getattr(event, 'w', getattr(event, 'x', WIDTH))
                    requested_height = getattr(event, 'h', getattr(event, 'y', HEIGHT))
                    display_info = pygame.display.Info()
                    screen = pygame.display.set_mode(
                        bounded_window_size(
                            requested_width, requested_height,
                            getattr(display_info, 'current_w', None),
                            getattr(display_info, 'current_h', None),
                        ),
                        pygame.RESIZABLE,
                    )
                    interface.canvas.set_display(screen)
                if event.type == pygame.KEYDOWN:
                    key = SCANCODE_SHORTCUT_KEYS.get(
                        getattr(event, 'scancode', None),
                        normalize_key(pygame.key.name(event.key)),
                    )
                    interface.key_down(key)
                elif event.type == pygame.KEYUP:
                    key = SCANCODE_SHORTCUT_KEYS.get(
                        getattr(event, 'scancode', None),
                        normalize_key(pygame.key.name(event.key)),
                    )
                    interface.key_up(key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    scale = interface.canvas.display_scale()
                    interface.click(event.pos[0] / scale, event.pos[1] / scale)
                elif event.type == pygame.WINDOWFOCUSLOST:
                    window_focused = False
                    interface.focus_lost()
                    for key in windows_keys:
                        interface.key_up(key)
                    windows_keys.clear()
                elif event.type == pygame.WINDOWFOCUSGAINED:
                    window_focused = True
                    interface.focus_gained()
            if interface.quit_requested:
                return
            current_windows_keys = (
                windows_pressed_physical_keys() if window_focused else set()
            )
            for key in current_windows_keys - windows_keys:
                interface.key_down(key)
            for key in windows_keys - current_windows_keys:
                interface.key_up(key)
            windows_keys = current_windows_keys
            scale = interface.canvas.display_scale()
            mouse_x, mouse_y = pygame.mouse.get_pos()
            interface.pointer = mouse_x / scale, mouse_y / scale
            pressed = pygame.key.get_pressed()
            movement_keys = set()
            if window_focused and pressed[pygame.K_a]:
                movement_keys.add('a')
            if window_focused and pressed[pygame.K_d]:
                movement_keys.add('d')
            if window_focused and pressed[pygame.K_w]:
                movement_keys.add('w')
            if window_focused and pressed[pygame.K_s]:
                movement_keys.add('s')
            movement_keys.update(current_windows_keys & {'w', 'a', 's', 'd'})
            interface.tick(dt, movement_keys)
            interface.draw()
            interface.canvas.present()
            pygame.display.flip()
    finally:
        pygame.quit()


def run_tkinter():
    import tkinter as tk
    from tkinter import font

    root = tk.Tk()
    root.title('大禮堂防衛戰 | Auditorium Defense')
    root.resizable(False, False)
    widget = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0, background=BG)
    widget.pack()
    interface = Interface(TkCanvas(widget, font.families(root)))
    root.bind('<KeyPress>', lambda event: interface.key_down(normalize_key(event.keysym)))
    root.bind('<KeyRelease>', lambda event: interface.key_up(normalize_key(event.keysym)))
    root.bind('<FocusOut>', lambda event: interface.focus_lost())
    root.bind('<FocusIn>', lambda event: interface.focus_gained())
    widget.bind('<Button-1>', lambda event: interface.click(event.x, event.y))
    widget.bind('<Motion>', lambda event: setattr(interface, 'pointer', (event.x, event.y)))
    widget.bind('<Leave>', lambda event: setattr(interface, 'pointer', (-1, -1)))
    previous = perf_counter()

    def frame():
        nonlocal previous
        now = perf_counter()
        interface.tick(now - previous)
        interface.draw()
        if interface.quit_requested:
            root.destroy()
            return
        previous = now
        root.after(16, frame)

    frame()
    root.mainloop()


def main():
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    try:
        import pygame
    except ModuleNotFoundError as error:
        if error.name != 'pygame':
            raise
        run_tkinter()
    else:
        run_pygame(pygame)
