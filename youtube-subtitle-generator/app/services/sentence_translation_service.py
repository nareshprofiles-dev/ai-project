"""
sentence_translation_service.py
--------------------------------
Translates a single Telugu sentence to English using MarianMT.

Uses Helsinki-NLP/opus-mt-mul-en (multilingual → English) with the
>>te<< language prefix to steer the model toward Telugu input.

Note: Helsinki-NLP/opus-mt-te-en (Telugu-only) was made private on
HuggingFace and returns 401. opus-mt-mul-en is the public replacement.

The model is loaded once and cached in module-level globals so
repeated calls within the same process don't reload from disk.
"""

from typing import Optional

from transformers import MarianMTModel, MarianTokenizer


_MODEL_NAME = "Helsinki-NLP/opus-mt-mul-en"
_LANG_PREFIX = ">>te<< "   # steers opus-mt-mul-en toward Telugu source
_tokenizer: Optional[MarianTokenizer] = None
_model: Optional[MarianMTModel] = None


def _load_model() -> tuple[MarianTokenizer, MarianMTModel]:
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        print(f"[SentenceTranslation] Loading MarianMT model: '{_MODEL_NAME}' ...")
        _tokenizer = MarianTokenizer.from_pretrained(_MODEL_NAME)
        _model = MarianMTModel.from_pretrained(_MODEL_NAME)
        print("[SentenceTranslation] Model ready.")
    return _tokenizer, _model


def translate_sentence(telugu_text: str) -> str:
    """
    Translate a single Telugu string to English.

    Args:
        telugu_text: A Telugu sentence or short paragraph.

    Returns:
        English translation string.

    Raises:
        RuntimeError: If the MarianMT model fails to translate.
    """
    text = telugu_text.strip()
    if not text:
        return ""

    try:
        tokenizer, model = _load_model()
        inputs = tokenizer(
            [_LANG_PREFIX + text],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        translated_ids = model.generate(**inputs)
        result = tokenizer.decode(translated_ids[0], skip_special_tokens=True)
        return result.strip()
    except Exception as exc:
        raise RuntimeError(f"MarianMT translation failed: {exc}") from exc
