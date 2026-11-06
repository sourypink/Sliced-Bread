"""Point the QR code on the deck's cover at a new link: python set_qr.py https://xxxx.gradio.live

Needs: pip install python-pptx "qrcode[pil]"
"""

import io
import sys

import qrcode
from pptx import Presentation
from qrcode.constants import ERROR_CORRECT_M

DECK = "Sliced Bread.pptx"
QR_SHAPE_NAME = "QR code"  # the picture's name on slide 1
INK = "#1C1B18"  # Pond ink, same as the deck's text
QR_BOX_PIXELS = 20  # size of one QR square in the PNG


def qr_png(url):
    code = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=QR_BOX_PIXELS, border=1)
    code.add_data(url)
    code.make(fit=True)
    buffer = io.BytesIO()
    code.make_image(fill_color=INK, back_color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith("http"):
        sys.exit("Usage: python set_qr.py https://your-public-link")
    url = sys.argv[1]
    deck = Presentation(DECK)
    pictures = [shape for shape in deck.slides[0].shapes if shape.name == QR_SHAPE_NAME]
    if not pictures:
        sys.exit(f'No picture named "{QR_SHAPE_NAME}" on slide 1 of {DECK}')
    blip_id = pictures[0]._element.blipFill.blip.rEmbed
    deck.slides[0].part.related_part(blip_id)._blob = qr_png(url)
    deck.save(DECK)
    print(f"QR code on {DECK} now opens {url}")


if __name__ == "__main__":
    main()
