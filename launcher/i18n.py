# -*- coding: utf-8 -*-
"""多语言支持（i18n）：加载 i18n/*.json，提供 tr() 翻译函数."""
import json
import os
import threading

from .constants import I18N_DIR

_lock = threading.Lock()
_cache = {}
_current = "zh_CN"
_fallback = "zh_CN"


LANGUAGES = [
    ("zh_CN", "简体中文"),
    ("zh_TW", "繁體中文"),
    ("en_US", "English"),
    ("ja_JP", "日本語"),
    ("ko_KR", "한국어"),
    ("fr_FR", "Français"),
    ("de_DE", "Deutsch"),
    ("es_ES", "Español"),
    ("ru_RU", "Русский"),
    ("pt_BR", "Português (Brasil)"),
    ("it_IT", "Italiano"),
    ("pl_PL", "Polski"),
    ("nl_NL", "Nederlands"),
    ("tr_TR", "Türkçe"),
    ("vi_VN", "Tiếng Việt"),
    ("th_TH", "ไทย"),
    ("id_ID", "Bahasa Indonesia"),
    ("uk_UA", "Українська"),
    ("hi_IN", "हिन्दी"),
    ("ar_SA", "العربية"),
    ("ms_MY", "Bahasa Melayu"),
    ("fil_PH", "Filipino"),
]


def load(lang: str) -> dict:
    """加载某语言的词典（带缓存）。"""
    with _lock:
        if lang in _cache:
            return _cache[lang]
        path = os.path.join(I18N_DIR, f"{lang}.json")
        data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        _cache[lang] = data
        return data


def set_language(lang: str):
    global _current
    codes = [c for c, _ in LANGUAGES]
    with _lock:
        if lang in codes or os.path.exists(os.path.join(I18N_DIR, f"{lang}.json")):
            _current = lang
        else:
            _current = "zh_CN"
    # 预加载
    load(_current)
    load(_fallback)


def current() -> str:
    return _current


def tr(key: str, *args, **kwargs) -> str:
    """取翻译文本；key 缺失时回退到简体中文，再回退到 key 本身."""
    with _lock:
        cur = _current
    text = load(cur).get(key)
    if text is None:
        text = load(_fallback).get(key)
    if text is None:
        text = key
    if args or kwargs:
        try:
            return text.format(*args, **kwargs)
        except Exception:
            return text
    return text
