"""Pygame and Tkinter drawing adapters."""

from pathlib import Path
from collections import deque
from .artwork import ARTWORK_FILES, SPRITE_SIZES
from .config import HEIGHT, RENDER_SCALE, WIDTH


class PygameCanvas:
    def __init__(self, pygame, screen):
        self.pg = pygame
        self.display = screen
        self.logical_size = WIDTH, HEIGHT
        source_art = {
            name: pygame.image.load(str(path)).convert_alpha()
            for name, path in ARTWORK_FILES.items()
        }
        self._remove_white_background(source_art['nailong'])
        self.source_art = {
            name: self._trim_transparent(image)
            for name, image in source_art.items()
        }
        self.scale = RENDER_SCALE * self.display_scale()
        self.screen = self._new_render_surface()
        self.damage_glow = None
        self._rebuild_render_art()

        self.font_file = (
            Path(__file__).resolve().parent.parent
            / 'assets'
            / 'fonts'
            / 'NotoSansTC.ttf'
        )

        if not self.font_file.is_file():
            raise FileNotFoundError(
                f'找不到中文字型：{self.font_file}'
            )

        self.font_file = str(self.font_file)
        self.chinese = True
        self.fonts = {}
        self.portrait_cache = {}

        # 測試字型能否正常渲染中文字
        test_font = pygame.font.Font(self.font_file, round(20 * self.scale))
        test_surface = test_font.render(
            "清大大禮堂", True, (255, 255, 255)
        )
        print("Font test successful:", test_surface.get_size())

    @staticmethod
    def _remove_white_background(image):
        """Make an edge-connected near-white backdrop transparent."""
        width, height = image.get_size()
        queue = deque()

        def is_background(x, y):
            red, green, blue, alpha = image.get_at((x, y))
            return (alpha > 0 and min(red, green, blue) >= 238
                    and max(red, green, blue) - min(red, green, blue) <= 18)

        def enqueue(x, y):
            if is_background(x, y):
                image.set_at((x, y), (255, 255, 255, 0))
                queue.append((x, y))

        for x in range(width):
            enqueue(x, 0)
            enqueue(x, height - 1)
        for y in range(1, height - 1):
            enqueue(0, y)
            enqueue(width - 1, y)

        while queue:
            x, y = queue.popleft()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < width and 0 <= ny < height and is_background(nx, ny):
                    image.set_at((nx, ny), (255, 255, 255, 0))
                    queue.append((nx, ny))

    @staticmethod
    def _trim_transparent(image):
        """Crop an image to its nontransparent pixels without modifying its source."""
        bounds = image.get_bounding_rect(min_alpha=1)
        if bounds.width == 0 or bounds.height == 0:
            return image
        if bounds.size == image.get_size() and bounds.topleft == (0, 0):
            return image
        return image.subsurface(bounds).copy()

    def clear(self, color):
        self.screen.fill(color)

    def present(self):
        """Downsample the 2x-window-resolution frame into the display."""
        self.pg.transform.smoothscale(self.screen, self.display.get_size(), self.display)

    def set_display(self, screen):
        """Resize the render surface and artwork with the display scale."""
        self.display = screen
        self.scale = RENDER_SCALE * self.display_scale()
        self.screen = self._new_render_surface()
        self.damage_glow = None
        self._rebuild_render_art()
        self.fonts.clear()
        self.portrait_cache.clear()

    def _new_render_surface(self):
        width, height = self.display.get_size()
        return self.pg.Surface((width * RENDER_SCALE, height * RENDER_SCALE))

    def damage_vignette(self, bounds, strength):
        left, top, width, height = (int(value * self.scale) for value in bounds)
        if self.damage_glow is None or self.damage_glow.get_size() != (width, height):
            depth = min(round(62 * self.scale), min(width, height) // 2)
            self.damage_glow = self.pg.Surface((width, height), self.pg.SRCALPHA)
            for inset in range(depth):
                falloff = 1 - inset / depth
                color = (248, round(26 + 35 * falloff), 48, round(215 * falloff ** 2))
                ring = (inset, inset, width - 2 * inset, height - 2 * inset)
                self.pg.draw.rect(self.damage_glow, color, ring, 1)
        self.damage_glow.set_alpha(round(255 * strength))
        self.screen.blit(self.damage_glow, (left, top))

    def _rebuild_render_art(self):
        self.art = {}
        self.art_content_heights = {}
        for name, source in self.source_art.items():
            width, height = SPRITE_SIZES[name]
            target_width = round(width * self.scale)
            target_height = round(height * self.scale)
            source_width, source_height = source.get_size()
            fit_scale = min(
                target_width / source_width,
                target_height / source_height,
            )
            content_width = max(1, round(source_width * fit_scale))
            content_height = max(1, round(source_height * fit_scale))
            content = self.pg.transform.smoothscale(
                source, (content_width, content_height)
            )
            frame = self.pg.Surface(
                (target_width, target_height), self.pg.SRCALPHA
            )
            frame.blit(
                content,
                ((target_width - content_width) // 2,
                 target_height - content_height),
            )
            self.art[name] = frame
            self.art_content_heights[name] = content_height / self.scale

    def display_scale(self):
        return self.display.get_width() / self.logical_size[0]

    def image(self, name, x, y):
        self.screen.blit(self.art[name], (int(x * self.scale), int(y * self.scale)))

    def portrait(self, name, x, y, size):
        key = name, size
        if key not in self.portrait_cache:
            source = self.source_art[name]
            width, height = source.get_size()
            output_size = int(size * self.scale)
            fit_scale = min(output_size / width, output_size / height)
            content_size = (
                max(1, round(width * fit_scale)),
                max(1, round(height * fit_scale)),
            )
            content = self.pg.transform.smoothscale(source, content_size)
            frame = self.pg.Surface(
                (output_size, output_size), self.pg.SRCALPHA
            )
            frame.blit(
                content,
                ((output_size - content_size[0]) // 2,
                 (output_size - content_size[1]) // 2),
            )
            self.portrait_cache[key] = frame
        self.screen.blit(
            self.portrait_cache[key],
            (int(x * self.scale), int(y * self.scale)),
        )

    def sprite(self, name, x, foot_y):
        width, height = self.art[name].get_size()
        top = foot_y - height / self.scale
        self.image(name, x - width / self.scale / 2, top)
        return foot_y - self.art_content_heights[name]

    def rect(self, x, y, width, height, color, outline=None, line_width=1):
        bounds = self.pg.Rect(int(x * self.scale), int(y * self.scale),
                              int(width * self.scale), int(height * self.scale))
        self.pg.draw.rect(self.screen, color, bounds)
        if outline:
            self.pg.draw.rect(
                self.screen, outline, bounds,
                max(1, round(line_width * self.scale)),
            )

    def circle(self, x, y, radius, color, outline=None, width=1):
        center = int(x * self.scale), int(y * self.scale)
        if color:
            self.pg.draw.circle(self.screen, color, center, int(radius * self.scale))
        if outline:
            self.pg.draw.circle(self.screen, outline, center, int(radius * self.scale),
                                max(1, round(width * self.scale)))

    def line(self, start, end, color, width=1):
        start = (int(start[0] * self.scale), int(start[1] * self.scale))
        end = (int(end[0] * self.scale), int(end[1] * self.scale))
        self.pg.draw.line(
            self.screen, color, start, end, max(1, round(width * self.scale))
        )

    def polygon(self, points, color, outline=None):
        points = [(int(x * self.scale), int(y * self.scale)) for x, y in points]
        self.pg.draw.polygon(self.screen, color, points)
        if outline:
            self.pg.draw.polygon(
                self.screen, outline, points, max(1, round(self.scale))
            )

    def text(self, x, y, value, size, color, anchor):
        if size not in self.fonts:
            self.fonts[size] = self.pg.font.Font(
                self.font_file, max(1, round(size * self.scale))
            )

        surface = self.fonts[size].render(value, True, color)
        box = surface.get_rect()
        setattr(
            box,
            {'w': 'midleft', 'e': 'midright', 'center': 'center'}[anchor],
            (int(x * self.scale), int(y * self.scale))
        )
        self.screen.blit(surface, box)


class TkCanvas:
    def __init__(self, canvas, families):
        from tkinter import PhotoImage

        self.canvas = canvas
        self.art = {}
        for name, path in ARTWORK_FILES.items():
            self.art[name] = PhotoImage(master=canvas, file=str(path))
        for name, size in SPRITE_SIZES.items():
            art = self.art[name]
            if (art.width(), art.height()) != size:
                self.art[name] = self._resize_photo(art, *size)
        self.portrait_cache = {}
        available = set(families)
        preferred = ('Microsoft JhengHei UI', 'Microsoft JhengHei', 'PingFang TC', 'Noto Sans CJK TC', 'WenQuanYi Zen Hei')
        self.family = next((name for name in preferred if name in available), None)
        self.chinese = self.family is not None
        if not self.family:
            self.family = 'TkDefaultFont'

    def clear(self, color):
        self.canvas.delete('all')
        self.canvas.configure(background=color)

    def damage_vignette(self, bounds, strength):
        # Stippled bands approximate the translucent falloff on Tk's canvas.
        stipples = ('gray12', 'gray25', 'gray50', 'gray75')
        left, top, width, height = bounds
        depth = min(62, min(width, height) // 2)
        for inset in range(1, depth, 2):
            opacity = strength * (1 - inset / depth) ** 2
            level = round(4 * opacity)
            if level:
                self.canvas.create_rectangle(
                    left + inset, top + inset,
                    left + width - inset - 1, top + height - inset - 1,
                    outline='#f43836', width=2, outlinestipple=stipples[level - 1],
                )

    def image(self, name, x, y):
        self.canvas.create_image(x, y, image=self.art[name], anchor='nw')

    def _resize_photo(self, source, width, height):
        from tkinter import PhotoImage

        source_width, source_height = source.width(), source.height()
        if source_width >= width and source_height >= height:
            factor = max(1, min(source_width // width, source_height // height))
            scaled = source.subsample(factor)
        else:
            factor = max((width + source_width - 1) // source_width,
                         (height + source_height - 1) // source_height)
            scaled = source.zoom(factor)
        scaled_width, scaled_height = scaled.width(), scaled.height()
        left, top = (scaled_width - width) // 2, (scaled_height - height) // 2
        resized = PhotoImage(master=self.canvas, width=width, height=height)
        resized.tk.call(str(resized), 'copy', str(scaled), '-from', left, top,
                        left + width, top + height, '-to', 0, 0)
        return resized

    def portrait(self, name, x, y, size):
        key = name, size
        if key not in self.portrait_cache:
            source = self.art[name]
            width, height = source.width(), source.height()
            if width <= size and height <= size:
                factor = max(1, min(size // width, size // height))
                scaled = source.zoom(factor)
            else:
                factor = max(1, (width + size - 1) // size,
                             (height + size - 1) // size)
                scaled = source.subsample(factor)
            frame = self._new_photo(size, size)
            left = (size - scaled.width()) // 2
            top = (size - scaled.height()) // 2
            frame.tk.call(str(frame), 'copy', str(scaled), '-to', left, top)
            self.portrait_cache[key] = frame
        self.canvas.create_image(
            x, y, image=self.portrait_cache[key], anchor='nw'
        )

    def _new_photo(self, width, height):
        from tkinter import PhotoImage
        return PhotoImage(master=self.canvas, width=width, height=height)

    def sprite(self, name, x, foot_y):
        art = self.art[name]
        top = foot_y - art.height()
        self.image(name, x - art.width() / 2, top)
        return top

    def rect(self, x, y, width, height, color, outline=None, line_width=1):
        self.canvas.create_rectangle(x, y, x + width, y + height, fill=color, outline=outline or '', width=line_width)

    def circle(self, x, y, radius, color, outline=None, width=1):
        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color or '',
                                outline=outline or '', width=width)

    def line(self, start, end, color, width=1):
        self.canvas.create_line(*start, *end, fill=color, width=width)

    def polygon(self, points, color, outline=None):
        coords = [coord for point in points for coord in point]
        self.canvas.create_polygon(*coords, fill=color, outline=outline or '')

    def text(self, x, y, value, size, color, anchor):
        self.canvas.create_text(x, y, text=value, anchor=anchor, fill=color, font=(self.family, -size))
