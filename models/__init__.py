# Этот файл делает директорию 'models' Python-пакетом
# Импортируем основные классы для удобного доступа из других модулей
from .schemas import *
from .reuqest_types import *
import pkgutil
import importlib
# Автоматически импортируем все модули в папке models (кроме __init__.py)
for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if module_name not in ('schemas', 'reuqest_types'):
        importlib.import_module(f"{__name__}.{module_name}")
# Определяем, какие имена будут доступны при импорте из пакета
# __all__ = ['Character', 'Ability', 'Item', 'Scene', 'SceneObject', 'ClassifyAnswerOrActionRequest']
