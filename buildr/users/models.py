from django.db import models
from django.contrib.auth.models import User,AbstractUser
import uuid


# Create your models here.


class workspace(models.Model):
    workspace_id=models.UUIDField(default=uuid.uuid4,auto_created=True,primary_key=True)
    name=models.CharField(max_length=50,default='workspace',blank=False,null=False)

    def __str__(self):
        return self.workspace_name
class User(AbstractUser):
    is_admin = models.BooleanField(default=False,blank=False)
    user_id=models.UUIDField(default=uuid.uuid4,auto_created=True,editable=False)
    points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)


    def add_points(self, points):
        self.points += points
        self.update_level()

    def update_level(self):
        
        level_thresholds = [100, 250, 500, 1000]  
        for i, threshold in enumerate(level_thresholds, start=1):
            if self.points >= threshold:
                self.level = i + 1
            else:
                break
        self.save()

    def __str__(self):
        return self.first_name +" "+ self.last_name

class project(models.Model):
    project_id=models.UUIDField(default=uuid.uuid4,primary_key=True)
    created_on=models.DateTimeField(auto_now_add=True)
    workspace=models.ForeignKey(workspace,on_delete=models.CASCADE,related_name='project')
    name=models.CharField(max_length=50,blank=True,default='Project',null=False)
    members=models.ManyToManyField(User,related_name='project')
    
    def __str__(self):
        return self.name

class issue(models.Model):
    project = models.ForeignKey(project, on_delete=models.CASCADE, related_name='issues')
    title = models.CharField(max_length=255)
    description = models.TextField()
    assignees = models.ManyToManyField(User, related_name='issues')
    status = models.CharField(max_length=50, choices=[
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed')
    ])
    date_created=models.DateTimeField(auto_now_add=True)
    priority=models.CharField(max_length=50,choices=[
        ('High','High'),
        ('Medium','Medium'),
        ('Low','Low')
    ])
    project_closed=models.DateTimeField(blank=True)
    deadline=models.DateField(blank=True)
    def __str__(self):
        return self.title
    

class subIssue(models.Model):
    parent_issue = models.ForeignKey(issue, on_delete=models.CASCADE, related_name='sub_issues')
    title = models.CharField(max_length=255)
    description = models.TextField()
    assignees = models.ManyToManyField(User, related_name='sub_issues')
    status = models.CharField(max_length=50, choices=[
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed')
    ])
    date_created=models.DateTimeField(auto_now_add=True)
    priority=models.CharField(max_length=50,choices=[
        ('High','High'),
        ('Medium','Medium'),
        ('Low','Low')
    ])
    project_closed=models.DateTimeField(blank=True)
    deadline=models.DateField(blank=True)
    def __str__(self):
        return self.title