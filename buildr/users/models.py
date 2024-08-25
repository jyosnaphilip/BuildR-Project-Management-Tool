from django.db import models
import uuid
from django.contrib.auth.models import User
from django.utils import timezone
# Create your models here.

class customUser(models.Model):
    custom_id=models.UUIDField(primary_key=True,default=uuid.uuid4,auto_created=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    profile_pic=models.ImageField(upload_to='user_dp',null=True,blank=True)
    gameMode=models.BooleanField(default=True,blank=False,)

    def __str__(self) :
        return self.user
class workspace(models.Model):
    ws_id=models.UUIDField(primary_key=True,default=uuid.uuid4,auto_created=True)
    ws_name=models.CharField(blank=True,max_length=50)
    admin=models.ForeignKey(customUser,on_delete=models.CASCADE)
    active=models.BooleanField(default=True,blank=False)
    def __str__(self):
        return self.ws_name

class workspaceMember(models.Model):
    workspace=models.ForeignKey(workspace,on_delete=models.CASCADE)
    customUser=models.ForeignKey(customUser,on_delete=models.CASCADE)
    active=models.BooleanField(blank=False,default=True)

    def __str__(self):
        return self.customUser.user.first_name+ " ("+self.workspace.ws_name+")"
    
    
class workspaceCode(models.Model):
    ws=models.ForeignKey(workspace,on_delete=models.CASCADE)
    code=models.CharField(max_length=8,unique=True)

    is_active=models.BooleanField(default=True,blank=False)
    created_on=models.DateTimeField(auto_now_add=True)
    expires_on=models.DateTimeField()
    
    def has_expired(self):
        return timezone.now>self.expires_on
    
    def regenerate_code(self):
        self.code = self.generate_unique_code()
        self.created_at = timezone.now()
        self.expires_on = self.created_at + timezone.timedelta(days=120) 
        self.save()
    
    def generate_unique_code():
        return uuid.uuid4().hex[:8].upper()
    
class playerStats(models.Model):
    custom=models.ForeignKey(customUser,on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)

    def add_points(self, points):
        self.points += points
        self.update_level()

    def update_level(self):
        # Define your level-up logic here
        level_thresholds = [100, 250, 500, 1000]  # Example thresholds
        for i, threshold in enumerate(level_thresholds, start=1):
            if self.points >= threshold:
                self.level = i + 1
            else:
                break
        self.save()

class priority(models.Model):
    name = models.CharField(max_length=100, choices=[
        ('Urgent', 'Open'),
        ('High Priority', 'High Priority'),
        ('Medium Priority', 'Medium Priority'),
        ('Low Priority','Low Prioirty')
    ])

    def __str__(self):
        return self.name
class status(models.Model):
    name = models.CharField(max_length=100, choices=[
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed')
    ])
    
class Project(models.Model):
    project_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    ws = models.ForeignKey(workspace, on_delete=models.CASCADE, related_name='projects')
    priority = models.ForeignKey(priority, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    status = models.ForeignKey(status, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')

    def __str__(self):
        return self.name

