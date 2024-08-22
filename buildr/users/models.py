from django.db import models
import uuid
from django.contrib.auth.models import User
# Create your models here.

class customUser(models.Model):
    custom_id=models.UUIDField(primary_key=True,default=uuid.uuid4,auto_created=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    profile_pic=models.ImageField(upload_to='user_dp',null=True,blank=True)
    gameMode=models.BooleanField(default=True,blank=False,)

