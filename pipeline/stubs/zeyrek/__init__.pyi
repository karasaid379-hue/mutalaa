from collections.abc import Sequence

class Parse:
    word: str
    lemma: str
    pos: str
    formatted: str

class MorphAnalyzer:
    def __init__(self) -> None: ...
    def analyze(self, text: str) -> Sequence[Sequence[Parse]]: ...
