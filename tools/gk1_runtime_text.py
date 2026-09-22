"""Token validation and Thai segmentation used by the reproducible payload build."""
import collections
import json
import re
from pathlib import Path

from gk1_segmenter import insert_zwsp


ICONS = json.loads(
    (Path(__file__).resolve().parents[1] / "config/gk1-icons.json").read_text(encoding="utf-8")
)
TOKENS = re.compile(
    "|".join(sorted(map(re.escape, ICONS), key=len, reverse=True))
    + r"|%\d+|&#xA;|\{[^{}]*\}|\[[^\]]*\]|[<>\n\r]|\d+(?:\.\d+)?"
)


def check_text(source, translation):
    if collections.Counter(TOKENS.findall(source)) != collections.Counter(TOKENS.findall(translation)):
        raise ValueError("Game tokens, markup, line breaks or numbers changed")
    if any(char in translation for char in ("\x00", "\ufffd")):
        raise ValueError("Invalid Unicode")
    if any("\ue000" <= char <= "\uf8ff" for char in translation):
        raise ValueError("Work CSV must contain Unicode Thai, not PUA")
    if source.strip() and not translation.strip():
        raise ValueError("Missing translation")


def prepare_runtime_texts(rows):
    return [insert_zwsp(row["translation"] if row["source"].strip() else row["source"]) for row in rows]
