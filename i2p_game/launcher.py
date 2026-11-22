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

SCANCODE_MOVEMENT_KEYS = {26: 'w', 4: 'a', 22: 's', 7: 'd'}
SCANCODE_SHORTCUT_KEYS = {
    **SCANCODE_MOVEMENT_KEYS,
    44: 'space',
    11: 'h', 20: 'q', 21: 'r', 24: 'u',
}
WINDOWS_PHYSICAL_VKS = {
    'w': 0x57, 'a': 0x41, 's': 0x53, 'd': 0x44, 'space': 0x20,
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
                    physical_key = SCANCODE_SHORTCUT_KEYS.get(
                        getattr(event, 'scancode', None)
                    )
                    key = physical_key or normalize_key(pygame.key.name(event.key))
                    interface.key_down(key)
                elif event.type == pygame.KEYUP:
                    physical_key = SCANCODE_SHORTCUT_KEYS.get(
                        getattr(event, 'scancode', None)
                    )
                    key = physical_key or normalize_key(pygame.key.name(event.key))
                    interface.key_up(key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    scale = interface.canvas.display_scale()
                    interface.click(event.pos[0] / scale, event.pos[1] / scale)
                elif event.type == pygame.WINDOWFOCUSLOST:
                    interface.focus_lost()
                elif event.type == pygame.WINDOWFOCUSGAINED:
                    interface.focus_gained()
            if interface.quit_requested:
                return
            current_windows_keys = windows_pressed_physical_keys()
            if 'space' in current_windows_keys - windows_keys:
                interface.key_down('space')
            if 'space' in windows_keys - current_windows_keys:
                interface.key_up('space')
            windows_keys = current_windows_keys
            scale = interface.canvas.display_scale()
            mouse_x, mouse_y = pygame.mouse.get_pos()
            interface.pointer = mouse_x / scale, mouse_y / scale
            pressed = pygame.key.get_pressed()
            movement_keys = set()
            if pressed[pygame.K_a]:
                movement_keys.add('a')
            if pressed[pygame.K_d]:
                movement_keys.add('d')
            if pressed[pygame.K_w]:
                movement_keys.add('w')
            if pressed[pygame.K_s]:
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
