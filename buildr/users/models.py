from django.db import models
import uuid
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class customUser(models.Model):
    custom_id=models.UUIDField(primary_key=True,default=uuid.uuid4,auto_created=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    profile_pic=models.ImageField(upload_to='user_dp',null=True,blank=True)
    gameMode=models.BooleanField(default=True,blank=False)
    last_ws=models.ForeignKey("workspace",null=True,blank=True,on_delete=models.SET_NULL)
    email=models.EmailField(null=True,blank=True,unique=True)
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
    class Meta:
        unique_together = ('workspace', 'customUser')
    
class workspaceCode(models.Model):
    ws=models.ForeignKey(workspace,on_delete=models.CASCADE)
    code=models.CharField(max_length=8,unique=True)

    is_active=models.BooleanField(default=True,blank=False)
    created_on=models.DateTimeField(auto_now_add=True)
    expires_on=models.DateTimeField()
    
    def has_expired(self):
        return timezone.now()>self.expires_on
       
    
    def regenerate_code(self):
        
        self.code = self.generate_unique_code()
        self.created_at = timezone.now()
        self.expires_on = self.created_at + timezone.timedelta(days=120) 
        self.save()
    
    def generate_unique_code(self):
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
        ('Urgent', 'Urgent'),
        ('High Priority', 'High Priority'),
        ('Medium Priority', 'Medium Priority'),
        ('Low Priority','Low Priority'),
        ('No Priority','No Priority')
    
    ])
    icon=models.CharField(max_length=20,null=True)

    def __str__(self):
        return self.name
class status(models.Model):
    name = models.CharField(max_length=100, choices=[
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Paused', 'Paused'),
        ('Closed', 'Closed')
    ])
    
class Project(models.Model):
    project_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_date =models.DateTimeField(null=True, blank=True)
    ws = models.ForeignKey(workspace, on_delete=models.CASCADE, related_name='projects')
    priority = models.ForeignKey(priority, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    status = models.ForeignKey(status, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    team=models.ManyToManyField(customUser,through='project_member_bridge')
    def __str__(self):
        return self.name
    
    def mark_completed(self):
        self.completed = True
        self.completed_date  = timezone.now()
        self.save()
    
class project_member_bridge(models.Model):
    team_member=models.ForeignKey(customUser,on_delete=models.CASCADE)
    project=models.ForeignKey(Project,on_delete=models.CASCADE)
    role=models.CharField(max_length=12, choices=[
        ('Lead', 'Lead'),
        ('Team member', 'Team member')
    ])
    joined_on=models.DateTimeField(auto_now_add=True)
    active=models.BooleanField(default=True)
    class Meta:
        unique_together = ('team_member', 'project')
class issue(models.Model):
    issue_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True,blank=True)
    deadline = models.DateField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_date =models.DateTimeField(null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='issues')
    priority = models.ForeignKey(priority, on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    status = models.ForeignKey(status, on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    assignee=models.ManyToManyField(customUser,through='issue_assignee_bridge')
    parent_task=models.ForeignKey('self', on_delete=models.CASCADE,null=True,related_name='child')
    overall_sentiment_score = models.FloatField(null=True, blank=True)
    def __str__(self):
        return self.name
    
    def mark_completed(self):
        self.completed = True
        self.completed_date  = timezone.now()
        self.save()

    def unread_comments_count(self, user):
        return self.comments.exclude(read_by=user).count()
    
    class Meta:
        ordering = ['priority__id'] 

class issue_assignee_bridge(models.Model):
    assignee=models.ForeignKey(customUser,on_delete=models.CASCADE)
    issue=models.ForeignKey(issue,on_delete=models.CASCADE)
    assigned_on=models.DateTimeField(auto_now_add=True)
    active=models.BooleanField(default=True)

    class Meta:
        unique_together = ('assignee', 'issue')
        
class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    verification_code = models.CharField(max_length=6)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=False)
    is_verified = models.BooleanField(default=False)
    created_At = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    
    def generate_unique_code(self):
        return uuid.uuid4().hex[:8].upper()
    
class Comments(models.Model):

    comment = models.CharField(max_length = 500, null = True, blank = True)
    author = models.ForeignKey(customUser, on_delete = models.CASCADE)
    parent_comment = models.ForeignKey('self', null = True, blank = True, related_name = 'replies',
                                        on_delete = models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    issue = models.ForeignKey(issue, related_name = 'comments', on_delete = models.CASCADE)
    sentiment_score=models.IntegerField(blank=True,null=True)
    read_by = models.ManyToManyField(customUser, related_name='read_comments', blank=True)  # Track which users have read the comment
    def __str__(self):
        return 'Comment by ' + self.author + 'about' + self.issue.name
    
    @property
    def is_reply(self):
        return self.parent is not None
    