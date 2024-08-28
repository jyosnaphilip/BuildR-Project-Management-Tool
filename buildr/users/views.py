from django.http import HttpResponse
from django.shortcuts import render,redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from .models import customUser,workspace,workspaceMember,workspaceCode
from django.utils import timezone
import json
from django.http import JsonResponse


def check_code(ws_code):
    
    ws_code = workspaceCode.objects.get(code=ws_code[0]['code'], is_active=True)
    if ws_code.has_expired():
        ws_code.regenerate_code()
        return ws_code.code
    else:
        return ws_code.code
    
# Create your views here.
def home(request,custom_id):
    current_ws = request.session.get('current_ws', None)
    ws=get_ws(custom_id,current_ws) #all ws
    current_ws=workspace.objects.get(ws_id=current_ws) 
    if str(current_ws.admin.custom_id)==custom_id:
        flag=True
        code=check_code(ws)

    else:
        flag=False
        code=None
    return render(request, 'users\home.html', {'custom_id':custom_id,'workspaces': ws,'current_ws': current_ws,'flag':flag,'ws_code':code})

def change_ws(request):
    if request.method == 'POST' and request.user.is_authenticated:
        
        data = json.loads(request.body)
        ws_id = data.get('ws_id')
        custom_user = customUser.objects.get(user=request.user)
        if workspaceMember.objects.filter(customUser=custom_user, workspace__ws_id=ws_id).exists():
            print('ws_id',ws_id)
            request.session['current_ws'] = ws_id
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
    
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
                custom_User=customUser(user_id=user.id) #automatically create a row in customUser table- profile pic  & gamemode can be changed
                custom_User.save()
                messages.success(request,'Account Created Successfully ')
                return redirect('login')
                
        else:
            print("Password not matching")
            return redirect('register')
    else:
        return render(request, 'login/register.html')

# register end----------------------------------------------
def chk_workspace(user_id):
    print(user_id)
    check=workspaceMember.objects.filter(customUser=user_id).exists()
    
    return check

def get_ws(user_id,ws_id=None):
    if ws_id:
        ws_lst=workspaceMember.objects.filter(customUser=user_id).exclude(workspace__ws_id=ws_id).values('workspace__ws_id', 'workspace__ws_name')
         # for a user with only one workspace we end up removing that from ws_lst in above line
        #to mitigate that, im putting this if condn
        if len(ws_lst)==0:
            ws_lst=workspaceMember.objects.filter(customUser=user_id)
 
    else:
        ws_lst=workspaceMember.objects.filter(customUser=user_id).values('workspace__ws_id', 'workspace__ws_name')

    return ws_lst


def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username,password=password)
        if user is not None:
            login(request,user)
            custom_user=customUser.objects.get(user=user)
            customUser_id=custom_user.custom_id
            if custom_user.last_ws:
                request.session['current_ws']=str(custom_user.last_ws.ws_id)
            else:
                first_workspace = workspaceMember.objects.filter(customUser=custom_user).first()
                if first_workspace:
                    request.session['current_ws'] = str(first_workspace.workspace.ws_id)
                    return redirect('home',customUser_id)
                else:
                    return redirect('first-signin',customUser_id)
    
        else:
            messages.error(request, "Username or password is incorrect!")
            return redirect('login')
    
    else:
        return render(request, 'login/login.html')


def first_signin(request,customUser_id):
    return render(request,'users/first_sign_in.html',{'customUser_id':customUser_id})                


def logout(request):
    if request.user.is_authenticated:
        custom_user=customUser.objects.get(user=request.user)
        current_ws=request.session.get('current_ws')
        if current_ws:
            custom_user.last_workspace=workspace.objects.get(ws_id=current_ws)
            custom_user.save()
    logout(request)
    return redirect('login')
#auth end------------------------

def join_workspace(request,custom_id):
    if request.method=="POST":
        code=request.POST.get('ws-code')
        if workspaceCode.objects.filter(code=code,is_active=True).exists():
            ws_code=workspaceCode.objects.filter(code=code,is_active=True).values('code','ws_id')

            actual_code=check_code(ws_code)
            
            if(code==actual_code):
                
                ws_member=workspaceMember(workspace=workspace.objects.get(ws_id=ws_code[0]['ws_id']),customUser=customUser.objects.get(custom_id=custom_id))
                ws_member.save()
                
                request.session['current_ws'] = str(ws_code[0]['ws_id'])
                
                return redirect('home',custom_id)
            else:
                messages.error("Invalid Code!")
                return redirect('join_workspace')
        else:
            messages.error("Invalid Code!")
            return redirect('join_workspace')
    return render(request, 'partials/join_workspace.html',{'custom_id':custom_id})


def check_ws(ws_name):
    check=workspace.objects.filter(ws_name=ws_name).exists()
    return check

def new_workspace(request,custom_id):
    if request.method=="POST":
        ws_name=request.POST.get('ws_name')
        
        name_check=check_ws(ws_name)
       
        if (not name_check) :
            ws=workspace(ws_name=ws_name,admin=customUser.objects.get(custom_id=custom_id))
            ws.save()

            ws_member=workspaceMember(workspace=workspace.objects.get(ws_id=ws.ws_id),customUser=customUser.objects.get(custom_id=custom_id))
            ws_member.save()
            code=workspaceCode.objects.filter(ws=ws).order_by('-created_on').first()
    
            if not code or code.has_expired():
                if code:
                    code.regenerate_code()
                else:
                    expires_on = timezone.now() + timezone.timedelta(days=120)  # Set expiration duration
                    code=workspaceCode.objects.create(
                        ws=workspace.objects.get(ws_id=ws.ws_id),
                        code=workspaceCode.generate_unique_code(),
                        expires_on=expires_on
                    )
                    code.save()

                return render(request,'users/home.html',{'custom_id':custom_id,"ws_id":ws,'code':code})
            else:
                messages.error(request,'Code incorrect!')
            return redirect('new_workspace',custom_id)

    
    return render(request,'partials/new_workspace.html',{'custom_id':custom_id})
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