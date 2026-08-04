from unicodedata import category

from crud.auth.base import CRUDSession
from properties.models import Property,Category
from typing import Optional
from crud.base import ModelType


class CRUDProperty(CRUDSession[Property]):
    pass


property_crud = CRUDProperty(Property)



class CRUDCategory(CRUDSession[Category]):
    pass


category_crud = CRUDProperty(Category)