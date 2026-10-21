"""Output to the braille embosser.

Tapos na ang pag-hati sa linya at pahina. Ang totoong driver ay ilalagay sa send_pages()
kapag may embosser na.
"""

CELLS_PER_LINE = 30
LINES_PER_PAGE = 27


class EmbosserError(Exception):
    """Expected problems (no device, port busy, ...). Ipinapakita ang mensahe sa status bar."""


def wrap_lines(braille, cells=CELLS_PER_LINE):
    """Word-wrap at `cells` characters; blank lines are kept."""
    lines = []
    for para in braille.split("\n"):
        cur = ""
        for word in para.split(" "):
            while len(word) > cells:  # salitang mas mahaba pa sa isang linya
                if cur:
                    lines.append(cur)
                    cur = ""
                lines.append(word[:cells])
                word = word[cells:]
            if not cur:
                cur = word
            elif len(cur) + 1 + len(word) <= cells:
                cur += " " + word
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def paginate(braille, cells=CELLS_PER_LINE, lines_per_page=LINES_PER_PAGE):
    """Returns a list of pages; each page is a list of at most `lines_per_page` lines."""
    lines = wrap_lines(braille, cells)
    return [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[]]


def send_pages(pages, progress=None, is_cancelled=None):
    """TODO: ikabit dito ang embosser driver (serial/USB). Tatanggap ng pages, magpapadala sa device."""
    raise EmbosserError("no embosser is connected yet")