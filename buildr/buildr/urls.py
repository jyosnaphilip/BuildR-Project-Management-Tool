"""
URL configuration for buildr project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from users.views import home,add_project,project_view,issue_view,add_issue,add_subIssue
urlpatterns = [
    path('admin/', admin.site.urls),
    path('',home,name='home'),
    path('add-project',add_project,name='add_project'),
    path('project_view',project_view,name="project_view"),
    path('issue_view',issue_view,name="issue_view"),
    path('add_issue',add_issue,name="add_issue"),
    path('add_subIssue',add_subIssue,name='add_subIssue'),
  
]
