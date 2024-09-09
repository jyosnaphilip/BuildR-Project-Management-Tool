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
from users.views import *
from django.contrib.auth import views as auth_views
from django.urls import include
from users.views import register,logout,join_workspace,new_workspace

from users.views import home,add_project,project_view,issue_view,add_issue,add_subIssue,user_login,first_signin,change_ws,update_status,update_issue_field,update_project_field,edit_project,edit_issue
urlpatterns = [
    path('admin/', admin.site.urls),
    # path("accounts/",include('allauth.urls')),


    path('add-project/<str:custom_id>',add_project,name='add_project'),
    path('project_view/<str:project_id>/<str:custom_id>',project_view,name="project_view"),
    path('issue_view/<str:issue_id>/<str:custom_id>',issue_view,name="issue_view"),
    path('add_issue/<str:custom_id>/<str:project_id>/',add_issue,name="add_issue"),
    path('add_subIssue/<str:issue_id>/<str:custom_id>',add_subIssue,name='add_subIssue'),
    path('update_status/<str:project_id>',update_status,name="update_status"),
    path('home/<str:custom_id>/',home,name='home'),
    path('register/',register,name='register'),
    path('',user_login,name='login'),
    path('logout/',logout,name='logout'),
    path('join-workspace/<str:custom_id>',join_workspace, name='join-workspace'),
    path('new-workspace/<str:custom_id>',new_workspace,name='new_workspace'),
   path('new-signin/<str:customUser_id>',first_signin,name='first-signin'),
   path('switch_ws/',change_ws,name='switch_ws'),
     path('update-issue-field/', update_issue_field, name='update_issue_field'),
     path('update-project-field/', update_project_field, name='update_project_field'),
    #  path('verify_email/',verify_email,name='verify_email'),
    path('edit_project/<str:project_id>/<str:custom_id>',edit_project,name='edit_project'),
    path('edit_issue/<str:issue_id>/<str:custom_id>',edit_issue,name='edit_issue'),
    path('dashboard/',dashboard, name='dashboard'),
]