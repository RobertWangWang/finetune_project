from pathlib import Path
from babel.support import Translations
from app.api.middleware.context import get_current_locale

LOCALE_DIR = Path(__file__).parent / "translations"


class I18n:
    def __init__(self):
        self._translations_cache = {}

    def get_translations(self, local: str = None) -> Translations:
        """获取翻译对象，默认使用当前协程的locale"""
        if local is None:
            local = get_current_locale()

        if local not in self._translations_cache:
            self._translations_cache[local] = Translations.load(LOCALE_DIR, [local])
        return self._translations_cache[local]

    def gettext(self, message: str, local: str = None) -> str:
        """翻译消息，自动使用当前请求的locale"""
        translations = self.get_translations(local)
        return translations.gettext(message)


i18n = I18n()  # 单例实例