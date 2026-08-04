from crud.auth.base import CRUDSession
from django.utils import timezone
from crud.user import user_crud
import re

class PasswordChangePolicy:
    def __init__(self, today:timezone.localdate):
        self.today = today

    def get_password_change_count_today(self,user:CRUDSession)-> bool:

        if user.password_change_date == self.today:
            if int(user.password_change_count) == 3:
                return False

        return True

    def update_password(self,user:CRUDSession,password:str)->bool:
        if not self.get_password_change_count_today(user=user):
            return False

        if user.password_change_date == self.today:
            count = user.password_change_count + 1
        else:
            count = 1

        user_crud.update(
            db_obj=user,
            password=password,
            password_change_count=count,
            password_change_date=self.today,
        )

        return True

    @staticmethod
    def validate_password_policy(password: str) -> None:
        errors = []

        rules = [
            (len(password) >= 8, "Parol ən azı 8 simvol olmalıdır."),
            (re.search(r"[A-Z]", password), "Parolda ən azı bir böyük hərf olmalıdır."),
            (re.search(r"[a-z]", password), "Parolda ən azı bir kiçik hərf olmalıdır."),
            (re.search(r"\d", password), "Parolda ən azı bir rəqəm olmalıdır."),
            (
                re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;]', password),
                "Parolda ən azı bir xüsusi simvol olmalıdır.",
            ),
        ]

        for valid, message in rules:
            if not valid:
                errors.append(message)

        if errors:
            raise ValueError("\n".join(errors))


password_change_policy = PasswordChangePolicy(today=timezone.localdate())