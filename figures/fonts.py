"""Discover an installed open font pair for the vector figures."""
from pathlib import Path
import importlib.util
import os

FAMILIES = (
    ("DejaVu Sans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ("Liberation Sans", "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
    ("Noto Sans", "NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
)
REQUIRED_CHARACTERS = '±²¾Δδηλρϑ‖’…⁰₁₂ℓ→−√≈≠≤≥'


def add_font_arguments(parser):
    parser.add_argument("--font-dir", type=Path,
                        help="Directory containing an open regular/bold font pair")


def font_directories(font_dir=None):
    override = font_dir or os.environ.get("REFRESHING_FONT_DIR")
    if override:
        return [Path(override).expanduser()]
    home = Path.home()
    directories = [
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation2"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/local/share/fonts"), home / ".local/share/fonts", home / ".fonts",
        Path("/Library/Fonts"), home / "Library/Fonts",
        Path("/opt/homebrew/share/fonts"),
        Path("/Applications/LibreOffice.app/Contents/Resources/fonts/truetype"),
    ]
    if os.environ.get("WINDIR"):
        directories.append(Path(os.environ["WINDIR"]) / "Fonts")
    spec = importlib.util.find_spec("matplotlib")
    if spec is not None and spec.origin:
        directories.append(Path(spec.origin).parent / "mpl-data/fonts/ttf")
    return directories


def register_fonts(font_dir=None, regular_name="PaperSans", bold_name="PaperSansBold"):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    failures = []
    for directory in font_directories(font_dir):
        if not directory.is_dir():
            continue
        for family, regular_file, bold_file in FAMILIES:
            pairs = [(directory / regular_file, directory / bold_file)]
            if not pairs[0][0].is_file():
                pairs = [(path, path.with_name(bold_file))
                         for path in sorted(directory.rglob(regular_file))]
            for regular, bold in pairs:
                if not regular.is_file() or not bold.is_file():
                    continue
                regular_font = TTFont(regular_name, str(regular))
                bold_font = TTFont(bold_name, str(bold))
                missing = [ch for ch in REQUIRED_CHARACTERS
                           if any(ord(ch) not in font.face.charWidths
                                  for font in (regular_font, bold_font))]
                if missing:
                    failures.append(f"{family}: missing {''.join(missing)}")
                    continue
                pdfmetrics.registerFont(regular_font)
                pdfmetrics.registerFont(bold_font)
                return family
    detail = "; ".join(failures)
    raise FileNotFoundError(
        "Install DejaVu Sans, Liberation Sans, or Noto Sans, or use --font-dir "
        "or REFRESHING_FONT_DIR to select a regular/bold pair. " + detail
    )
