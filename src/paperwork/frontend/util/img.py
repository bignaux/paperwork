import StringIO

from gi.repository import Clutter
from gi.repository import Cogl
from gi.repository import GdkPixbuf
import PIL.ImageDraw


def add_img_border(img, color="#a6a5a4", width=1):
    """
    Add a border of the specified color and width around a PIL image
    """
    img_draw = PIL.ImageDraw.Draw(img)
    for line in range(0, width):
        img_draw.rectangle([(line, line), (img.size[0]-1-line,
                                           img.size[1]-1-line)],
                           outline=color)
    del img_draw
    return img


def image2pixbuf(img):
    """
    Convert an image object to a gdk pixbuf
    """
    if img is None:
        return None
    file_desc = StringIO.StringIO()
    try:
        img.save(file_desc, "ppm")
        contents = file_desc.getvalue()
    finally:
        file_desc.close()
    loader = GdkPixbuf.PixbufLoader.new_with_type("pnm")
    try:
        loader.write(contents)
        pixbuf = loader.get_pixbuf()
    finally:
        loader.close()
    return pixbuf


def pixbuf2clutter_img(pixbuf):
    fmt = Cogl.PixelFormat.RGB_888
    if pixbuf.get_has_alpha():
        fmt = Cogl.PixelFormat.RGB_8888

    img = Clutter.Image()
    img.set_data(pixbuf.get_pixels(), fmt,
                 pixbuf.get_width(), pixbuf.get_height(),
                 pixbuf.get_rowstride())
    return img


def image2clutter_img(img):
    if img.mode == "RGB":
        fmt = Cogl.PixelFormat.RGB_888
        row_stride = 3 * img.size[0]
    elif img.mode == "RGBA":
        fmt = Cogl.PixelFormat.RGB_8888
        row_stride = 4 * img.size[0]
    else:
        raise Exception("Unsupported image mode: %s" % img.mode)

    clutter_img = Clutter.Image()
    clutter_img.set_data(img.tobytes(), fmt,
                         img.size[0], img.size[1],
                         row_stride)
    return clutter_img
