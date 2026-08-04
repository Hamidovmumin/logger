from crud.auth.base import CRUDSession
from accounts.models import CustomUser
from typing import Optional
from crud.base import ModelType


class CRUDUser(CRUDSession[CustomUser]):

    def get_by_username(self, username:str)->Optional[CustomUser]:
        try:
            return self.model.objects.get(username=username)
        except self.model.DoesNotExist:
            return None


user_crud = CRUDUser(CustomUser)