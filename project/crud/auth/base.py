from crud.base import CRUD,ModelType
from typing import Optional


class CRUDSession(CRUD[ModelType]):

    def get_by_email(self,email:str)->Optional[ModelType]:
        try:
            return self.model.objects.get(email=email)
        except self.model.DoesNotExist:
            return None
