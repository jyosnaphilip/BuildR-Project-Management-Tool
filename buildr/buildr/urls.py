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
from django.conf import settings
from django.conf.urls.static import static
from users.views import home,add_project,project_view,issue_view,add_issue,add_subIssue,user_login,first_signin,change_ws,update_status,update_issue_field,update_project_field,edit_project,edit_issue, get_issueComments,submit_comment,submit_replies,dashboard,user_profile,edit_profile, manage_workspace, remove_ws_member, deactivate_ws_member, toggle_ws_member_status, create_new_code
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
    path('logout/',logout_user,name='logout_user'),
    path('join-workspace/<str:custom_id>',join_workspace, name='join-workspace'),
    path('new-workspace/<str:custom_id>',new_workspace,name='new_workspace'),
   path('new-signin/<str:customUser_id>',first_signin,name='first-signin'),
   path('switch_ws/',change_ws,name='switch_ws'),
     path('update-issue-field/', update_issue_field, name='update_issue_field'),
     path('update-project-field/', update_project_field, name='update_project_field'),
    #  path('verify_email/',verify_email,name='verify_email'),
    path('edit_project/<str:project_id>/<str:custom_id>',edit_project,name='edit_project'),
    path('edit_issue/<str:issue_id>/<str:custom_id>',edit_issue,name='edit_issue'),
    path('dashboard/<str:custom_id>',dashboard, name='dashboard'),
    path('get_issueComments/<str:issue_id>',get_issueComments,name='get_issueComments'),
    path('submit_comment/',submit_comment,name="submit_comment"),
    path('submit_reply/',submit_replies,name='submit_reply'),
    path('user-profile/<str:custom_id>',user_profile,name='user-profile'),
    path('edit_profile/<str:custom_id>',edit_profile,name='edit_profile'),
    path('manage_ws/<str:custom_id>/<str:ws_id>',manage_workspace,name='manage_ws'),
    path('remove_ws_member/<str:user_custom_id>/<str:custom_id>/<str:ws_id>',remove_ws_member,name='remove_ws_member'),
    path('deactivate_ws_member/<str:user_custom_id>/<str:custom_id>/<str:ws_id>',deactivate_ws_member,name='deactivate_ws_member'),
    path('toggle_ws_member_status/<str:ws_id>', toggle_ws_member_status, name='toggle_ws_member_status'),
    path('create_new_code/<str:custom_id>/<str:ws_id>', create_new_code, name='create_new_code'),


 
]   

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)