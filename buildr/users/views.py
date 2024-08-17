from django.http import HttpResponse
from django.shortcuts import render,redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


# Create your views here.
def home(request):
    return render(request,'users\home.html')

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
                print("Username Taken")
            elif User.objects.filter(email=email).exists():
                print("Email is taken")
            else:
                user = User.objects.create_user(username=username,password=password1,email=email,first_name=first_name,last_name=last_name)
                user.save()
                return HttpResponse("User has been created successfully")
                print("User created")
        else:
            print("Password not matching")
            return redirect('home')
    else:
        return render(request, 'login/register.html')

def login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request,username=username,password=password)
    
        if user is not None:
            login(request, user)
            return redirect('home')
    
        else:
            messages.success(request, "Error. Try Again")
            return redirect('register')
    
    else:
        return render(request, 'login/login.html')

def logout(request):
    return render(request,'login/login.html')

def join_workspace(request):
    return render(request, 'partials/join_workspace.html')

def new_workspace(request):
    return render(request,'partials/new_workspace.html')