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
from users.views import register,logout,join_workspace,new_workspace

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/',home,name='home'),
    path('register/',register,name='register'),
    path('',login,name='login'),
    path('logout/',logout,name='logout'),
    path('join-workspace/',join_workspace, name='join-workspace'),
    path('new-workspace',new_workspace,name='new_workspace')
]
