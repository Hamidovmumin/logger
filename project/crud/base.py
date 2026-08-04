from typing import TypeVar, Generic, Callable, Optional, Type
from django.db import models

ModelType  = TypeVar('ModelType ',bound=models.Model)

class CRUD(Generic[ModelType ]):
    def __init__(self,model: Type[ModelType ]):
        self.model = model

    def create(self,**kwargs)->ModelType:
        db_obj = self.model.objects.create(**kwargs)
        return db_obj
    

    def update(self,db_obj:ModelType,**kwargs)->ModelType:
        password = kwargs.pop('password',None)

        if password is not None:
            db_obj.set_password(password)

        for key,value in kwargs.items():
            setattr(db_obj,key,value)

        db_obj.save()
        return db_obj
    
    def delete(self, db_obj: ModelType)->bool:
        try:
            db_obj.delete()
            return True
        except:
            return False
