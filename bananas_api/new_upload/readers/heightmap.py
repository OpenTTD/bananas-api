import hashlib

from PIL import Image

from ..exceptions import ValidationException
from ...helpers.enums import PackageType

# Limit the size of heightmaps, as otherwise it could allocate a lot of
# memory for clients loading the map.
Image.MAX_IMAGE_PIXELS = 16384 * 16384


def rgb_to_gray(color):
    return ((color[0] * 19595) + (color[1] * 38470) + (color[2] * 7471)) // 65536


class Heightmap:
    """
    Heightmap meta data.

    @ivar md5sum: md5 checksum of heightmap file
    @type md5sum: C{bytes}

    @ivar size: Image size
    @type size: (C{int}, C{int})

    @ivar histogram: List of 256 entries indicating how often that height level occurs
    @type histogram: C{list} of C{int}
    """

    package_type = PackageType.HEIGHTMAP

    def __init__(self):
        self.md5sum = None
        self.size = (None, None)
        self.histogram = None

    def read(self, fp):
        """
        Read heightmap meta data

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """

        pos = fp.tell()
        md5sum = hashlib.md5()
        md5sum.update(fp.read())
        self.md5sum = md5sum.digest()
        fp.seek(pos, 0)

        try:
            im = Image.open(fp)
        except Image.DecompressionBombError:
            raise ValidationException("Image is too large.")
        except Exception:
            raise ValidationException("File is not a valid image.")

        self.size = im.size

        # The following code is based on https://github.com/OpenTTD/OpenTTD/blob/master/src/heightmap.cpp
        # to mimic the heightmap loading in OpenTTD as much as possible.

        if im.palette:
            palette = im.palette.palette
            mode_len = len(im.palette.mode)

            gray_palette = []
            all_gray = True
            for i in range(0, len(palette), mode_len):
                color = palette[i : i + mode_len]
                all_gray = all_gray and (color[0] == color[1] and color[1] == color[2])
                gray_palette.append(rgb_to_gray(color))

            palette_size = len(palette) // mode_len
            if palette_size == 16 and not all_gray:
                for i in range(palette_size):
                    gray_palette[i] = 256 * i // palette_size

        height_funcs = {
            "P": lambda pixel: gray_palette[pixel],
            "RGB": rgb_to_gray,
            "RGBA": rgb_to_gray,
            "I": lambda pixel: pixel >> 8,
            "L": lambda pixel: pixel,
            "LA": lambda pixel: pixel[0],
        }

        height_func = height_funcs.get(im.mode)
        if height_func is None:
            raise ValidationException(f"Unsupported image mode: {im.mode}.")

        # Create a histogram based on the height of the pixels.
        self.histogram = [0] * 256
        for pixel in im.getdata():
            self.histogram[height_func(pixel)] += 1
