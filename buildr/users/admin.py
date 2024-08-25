from django.contrib import admin
from .models import customUser,workspace,workspaceMember,workspaceCode, Project,playerStats,priority,status
admin.site.register(customUser)
admin.site.register(workspace)
admin.site.register(workspaceMember)
admin.site.register(workspaceCode)
admin.site.register(Project)
admin.site.register(playerStats)
admin.site.register(priority)

admin.site.register(status)

