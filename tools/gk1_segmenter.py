"""Token-safe Thai word segmentation for the Graveyard Keeper 1 runtime."""
import json
import re
from pathlib import Path


ZWSP = '\u200b'
THAI_RUN_PATTERN = re.compile(r'[\u0e00-\u0e7f]+')
ICON_PATH = Path(__file__).resolve().parents[1] / 'config/gk1-icons.json'

DEFAULT_GAME_WORDS = [
    'เกอร์รี่', 'โฮราดริก', 'เอพิสคอป', 'อินควิซิเตอร์', 'โคลโธ', 'สเนค',
    'นักโหราศาสตร์', 'โต๊ะผ่าชันสูตร', 'ชิ้นส่วนศพ', 'หินลับมีด',
    'เตาหลอมโลหะ', 'แท่นแปรรูปไม้', 'สุสาน', 'โบสถ์', 'ห้องใต้ดิน',
    'คะแนนความชอบ', 'หัวกะโหลกขาว', 'หัวกะโหลกแดง', 'พลังงาน',
    'ความเหนื่อยล้า', 'เหรียญทอง', 'เหรียญเงิน', 'เหรียญทองแดง',
    'ใบอนุญาตขุดศพ', 'ใบมรณบัตร', 'การชันสูตรศพ', 'มีดผ่าตัด',
    'หลุมศพ', 'ป้ายหลุมศพ', 'รั้วหลุมศพ', 'ช่องเก็บของ', 'ม้านั่งทำงาน',
]

# PyThaiNLP correctly treats these as compounds, but GK1's narrow item panels
# still need safe internal wrap points. These are linguistic word boundaries,
# not arbitrary character breaks.
SOFT_BREAK_COMPOUNDS = {
    'โต๊ะเขียนหนังสือ': ('โต๊ะ', 'เขียน', 'หนังสือ'),
    'โต๊ะงานโบสถ์': ('โต๊ะ', 'งาน', 'โบสถ์'),
    'โต๊ะผ่าชันสูตร': ('โต๊ะ', 'ผ่าชันสูตร'),
}


def _protected_pattern():
    icons = json.loads(ICON_PATH.read_text(encoding='utf8'))
    alternatives = [re.escape(token) for token in sorted(icons, key=len, reverse=True)]
    alternatives.extend([
        r'%\d+', r'&#x[0-9A-Fa-f]+;', r'\{[^{}]*\}', r'\[[^\]]*\]',
    ])
    return re.compile('(' + '|'.join(alternatives) + ')')


PROTECTED_PATTERN = _protected_pattern()


class TrieNode:
    __slots__ = ('children', 'is_end')

    def __init__(self):
        self.children = {}
        self.is_end = False


class TrieSegmenter:
    """Small longest-match fallback used when PyThaiNLP is unavailable."""

    def __init__(self, words=None):
        self.root = TrieNode()
        for word in words or ():
            self.add_word(word)

    def add_word(self, word):
        if not word:
            return
        node = self.root
        for char in word:
            node = node.children.setdefault(char, TrieNode())
        node.is_end = True

    def segment(self, text):
        tokens = []
        index = 0
        while index < len(text):
            node = self.root
            cursor = index
            match_end = index
            while cursor < len(text) and text[cursor] in node.children:
                node = node.children[text[cursor]]
                cursor += 1
                if node.is_end:
                    match_end = cursor
            if match_end == index:
                match_end = index + 1
                while match_end < len(text) and '\u0e31' <= text[match_end] <= '\u0e4e':
                    match_end += 1
            tokens.append(text[index:match_end])
            index = match_end
        return tokens


class ThaiWordSegmenter:
    def __init__(self, custom_words=None, force_fallback=False):
        self.custom_words = list(DEFAULT_GAME_WORDS)
        if custom_words:
            self.custom_words.extend(custom_words)
        self.fallback = TrieSegmenter(self.custom_words)
        self.word_tokenize = None
        self.custom_dict = None
        if not force_fallback:
            try:
                from pythainlp.corpus import thai_words
                from pythainlp.tokenize import word_tokenize
                from pythainlp.util import dict_trie
            except ImportError:
                pass
            else:
                self.word_tokenize = word_tokenize
                self.custom_dict = dict_trie(set(thai_words()).union(self.custom_words))

    def tokenize_thai(self, text):
        if text in SOFT_BREAK_COMPOUNDS:
            return list(SOFT_BREAK_COMPOUNDS[text])
        if self.word_tokenize is None:
            return self.fallback.segment(text)
        return self.word_tokenize(
            text,
            custom_dict=self.custom_dict,
            engine='newmm',
            keep_whitespace=False,
        )

    def insert_zwsp(self, text):
        if not text:
            return text
        clean = text.replace(ZWSP, '')
        parts = PROTECTED_PATTERN.split(clean)
        output = []
        for part in parts:
            if not part or PROTECTED_PATTERN.fullmatch(part):
                output.append(part)
                continue
            output.append(THAI_RUN_PATTERN.sub(self._segment_match, part))
        return ''.join(output)

    def _segment_match(self, match):
        return ZWSP.join(token for token in self.tokenize_thai(match.group()) if token)


_SEGMENTER = None


def get_segmenter():
    global _SEGMENTER
    if _SEGMENTER is None:
        _SEGMENTER = ThaiWordSegmenter()
    return _SEGMENTER


def insert_zwsp(text):
    return get_segmenter().insert_zwsp(text)


def strip_zwsp(text):
    return text.replace(ZWSP, '') if text else text
