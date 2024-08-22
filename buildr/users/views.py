from django.http import HttpResponse
from django.shortcuts import render,redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from .models import customUser

# Create your views here.
def home(request,custom_id):
    return render(request,'users\home.html',{'custom_id':custom_id})

#auth-----------------------------------------------
# register---------------------------------------
def register(request):
    if request.method == 'POST':
        first_name = request.POST.get('FirstName')
        last_name = request.POST.get('LastName')
        username = request.POST.get('Username')
        email = request.POST.get('Email')
        password1 = request.POST.get('Password1')
        password2 = request.POST.get('Password2')

        if password1 == password2:
            if User.objects.filter(username=username).exists():
                messages.error(request,"Username Already Exists!")
                return redirect('register')
                
            elif User.objects.filter(email=email).exists():
                messages.error(request,"Email is already registered!")
                return redirect('register')
                
            else:
                user = User.objects.create_user(username=username,password=password1,email=email,first_name=first_name,last_name=last_name)
                user.set_password(password1)
                user.save()
                print(user)
                custom_User=customUser(user_id=user) #automatically create a row in customUser table- profile pic  & gamemode can be changed
                custom_User.save()
                messages.success(request,'Account Created Successfully ')
                return redirect('login')
                
        else:
            print("Password not matching")
            return redirect('register')
    else:
        return render(request, 'login/register.html')

# register end----------------------------------------------


def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username,password=password)
        if user is not None:
            login(request,user)
            custom_user=customUser.objects.get(user=user)
            customUser_id=custom_user.custom_id
            return redirect('home',customUser_id)
    
        else:
            messages.error(request, "Username or password is incorrect!")
            return redirect('login')
    
    else:
        return render(request, 'login/login.html')


                


def logout(request):
    return render(request,'login/login.html')
#auth end------------------------

def join_workspace(request):
    return render(request, 'partials/join_workspace.html')

def new_workspace(request):
    return render(request,'partials/new_workspace.html')
def add_project(request):
    return render(request, 'users/add_project.html')

def project_view(request):
    return render(request,'users\project_view.html')

def issue_view(request):
    return render(request,'users\issue_view.html')

def add_issue(request):
    return render(request,'users/add_issue.html')

def add_subIssue(request):
    return render(request,'users/add_subIssue.html')