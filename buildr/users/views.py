from django.shortcuts import render,redirect

# Create your views here.
def home(request):
    return render(request,'users\home.html')

def add_project(request):
    return render(request, 'users/add_project.html')