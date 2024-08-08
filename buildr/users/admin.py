from django.contrib import admin
from .models import workspace,project, issue,subIssue,User
# Register your models here.
admin.site.register(workspace)
admin.site.register(project)
admin.site.register(issue)
admin.site.register(subIssue)
admin.site.register(User)