# Create your views here.

from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login,logout
from .models import customUser, workspace, workspaceMember, workspaceCode, Project, priority, status, project_member_bridge, issue, issue_assignee_bridge, Comments
from django.utils import timezone
from django.db.models.functions import ExtractDay
import json
from datetime import datetime
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Case, When, IntegerField, F, ExpressionWrapper, fields, Exists, OuterRef, Subquery
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
import random
from django.contrib.auth.decorators import login_required
from .models import EmailVerification
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date  # Make sure to import this if you're parsing dates
from .models import EmailVerification
from datetime import timedelta,date
from django.utils.dateformat import format
from highcharts_gantt.chart import Chart
from highcharts_gantt.global_options.shared_options import SharedOptions
from highcharts_gantt.options import HighchartsGanttOptions
from highcharts_gantt.options.plot_options.gantt import GanttOptions
from highcharts_gantt.options.series.gantt import GanttSeries
from users.tasks import get_sentiment_task, send_email_task
from django.conf import settings
import os
from django.core.mail import send_mail
from django.urls import reverse
import uuid
from urllib.parse import unquote
from allauth.socialaccount.models import SocialAccount

def check_code(ws_code):
    ws_code = workspaceCode.objects.get(
        code=ws_code[0]['code'], is_active=True)
    if ws_code.has_expired():
        ws_code.regenerate_code()
        return ws_code.code
    else:
        return ws_code.code

def create_code(ws_id):
    ws_code = workspaceCode.objects.get(ws=ws_id)
    ws_code.regenerate_code()
    ws_code.save()

    return ws_code.code

def get_projects(ws_id):
    """ retrieves all projects of a workspace """
    projects = Project.objects.filter(ws=ws_id.ws_id).distinct()
    return projects

def get_google_profile_pic(user_):
    if SocialAccount.objects.filter(user_id=user_.id).exists():
     # it is a user who signed up via google
        # Decode the URL
        profile_pic_url=SocialAccount.objects.get(user_id=user_.id).extra_data['picture']
        profile_pic_url = unquote(str(profile_pic_url))
        return profile_pic_url
    else:
        return None

def req_for_navbar(custom_id, current_ws_id):
    """ retrieves all things necessary for rendering of sidebar """
    ws = get_ws(custom_id, current_ws_id)  # all ws #nav
    current_ws = get_object_or_404(workspace,ws_id=current_ws_id) #retrieves current_ws based on current_ws_id
    projects = get_projects(current_ws)  # nav #retrieve projects associated with the current workspace.
    
    if not current_ws and len(ws)!=0:
        current_ws = ws[0]
    if str(current_ws.admin.custom_id) == custom_id or current_ws.admin.custom_id == custom_id: 
        print("hre2") # nav
        flag = True #indicating whether the current user is the admin of the workspace or not.
        ws_code = workspaceCode.objects.filter(
            ws=current_ws_id, is_active=True).values('code', 'ws_id')
        if len(ws_code) == 0: #no active code was found
            code = create_code(current_ws_id)
        else:
            code = check_code(ws_code)

    else:
        flag = False #not admin
        code = None
    return ws, current_ws, projects, flag, code #returning flag to check whether the user is admin or not.

def home(request, custom_id):
    current_ws_id = request.session.get('current_ws', None)  # nav #session store and retrieve data of a particular user.
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    profile_pic_url = get_google_profile_pic(request.user)
    user_issues = issue.objects.filter(
        project__ws__ws_id=current_ws_id, issue_assignee_bridge__assignee=custom_id).annotate(
        subissue_count=Count('child'), unread_comments_count=Count('comments', filter=~Q(comments__read_by=customUser.objects.get(user=request.user))),is_closed=Case(
            When(status=4, then=1), default=0, output_field=IntegerField())).order_by('is_closed','priority__id') #fetches all issues assigned to the current user for current workspace.
    statuses, priorities = get_priority_status_list() #fetches status and priority
    custom_user = customUser.objects.get(user=request.user)
    return render(request, 'users\home.html', {"profile_pic_url":profile_pic_url,'custom_user':custom_user,'custom_id': custom_id, 'workspaces': ws, 'current_ws': current_ws, 'flag': flag, 'ws_code': code, 'projects': projects, 'user_issues': user_issues,'status':statuses,'priority':priorities}) #renders home page including custom ID, workspaces, current workspace. projects, user issues, flag for admin status

def change_ws(request):
    if request.method == 'POST' and request.user.is_authenticated:
        data = json.loads(request.body) #loading the request body as json data
        ws_id = data.get('ws_id')
        custom_user = customUser.objects.get(user=request.user) #retrieves customuser object for authenticated user
        if workspaceMember.objects.filter(customUser=custom_user, workspace__ws_id=ws_id).exists(): #customUser in workspaceMember 
            request.session['current_ws'] = ws_id #updating the current workspace id in the users session
            custom_id = customUser.objects.get(user=request.user).custom_id
            home_url = reverse('home', args=[custom_id])  # Adjust 'workspace_home' and args as needed
            return JsonResponse({'url': home_url})
    return JsonResponse({'status': 'error'}, status=400)

# auth-----------------------------------------------
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
                messages.error(request, "Username Already Exists!")
                return redirect('register')

            elif User.objects.filter(email=email).exists():
                messages.error(request, "Email is already registered!")
                return redirect('register')

            else:
                user = User.objects.create_user(
                    username=username, password=password1, email=email, first_name=first_name, last_name=last_name)
                user.set_password(password1) #setting the password in hashed secured format.
                user.save()
                # automatically create a row in customUser table- profile pic  & gamemode can be changed
                custom_User = customUser(user_id=user.id)
                custom_User.save()
                # activationEmail(request, user, email)
                messages.success(request, 'Account Created Successfully ')
                return redirect('login')

        else:
            return redirect('register')
    else:
        return render(request, 'login/register.html')
    

# register end----------------------------------------------
# auth ends-----------------


def chk_workspace(user_id):
    check = workspaceMember.objects.filter(customUser=user_id).exists()
    return check


def get_ws(user_id, ws_id=None): #retrieving a list of workspaces that a user is a member of.
    if ws_id:
        ws_lst = workspaceMember.objects.filter(customUser=user_id).exclude(
            workspace__ws_id=ws_id).values('workspace__ws_id', 'workspace__ws_name')
        # for a user with only one workspace we end up removing that from ws_lst in above line
        # to mitigate that, im putting this if condn
        if len(ws_lst) == 0: #if user is only part of one workspace(the one which is currently logged in)
            ws_lst = workspaceMember.objects.filter(customUser=user_id).values(
                'workspace__ws_id', 'workspace__ws_name')
    else:
        ws_lst = workspaceMember.objects.filter(customUser=user_id).values( #if no ws_id is provided, then retrieves all workspaces the user is a member of
            'workspace__ws_id', 'workspace__ws_name')

    return ws_lst #returns a dictionary


def user_login(request): 
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None: #authentication is successful
            login(request, user) #creates a session for the user when the user is logged in.
            custom_user = customUser.objects.get(user=user) #user is linked to authenticated user
            customUser_id = custom_user.custom_id
            if custom_user.last_ws:
                request.session['current_ws'] = str(custom_user.last_ws.ws_id) #the last_ws id is stored in session as current_ws
            else:
                first_workspace = workspaceMember.objects.filter(
                    customUser=custom_user).first() #retrieves the first workspace the user is a member of.
                if first_workspace: #atleast one workspace
                    request.session['current_ws'] = str(
                        first_workspace.workspace.ws_id)
                    return redirect('home', customUser_id)
                else:
                    return redirect('first-signin', customUser_id)

        else:
            messages.error(request, "Username or password is incorrect!")
            return redirect('login')

    else:
        
        return render(request, 'login/login.html')


def first_signin(request, customUser_id):
    return render(request, 'users/first_sign_in.html', {'customUser_id': customUser_id})

def user_logout(request):
    if request.user.is_authenticated: #checks whether the user is logged in. if not, skips saving the lst workspace and directly logs out.
        if customUser.objects.filter(user = request.user).exists():
            custom_user = customUser.objects.get(user=request.user)
            current_ws = request.session.get('current_ws') #retrieving current ws_id
            if current_ws:
                custom_user.last_workspace = workspace.objects.get( #last_workspace is a field in customUser
                    ws_id=current_ws)
                custom_user.save()
    logout(request)
    return redirect('login')

    
# auth end------------------------

# ws-related
@login_required(login_url='login')
def join_workspace(request):
    customUser_ = customUser.objects.get(user=request.user)
    custom_id=customUser_.custom_id
    if request.method == "POST":
        code = request.POST.get('ws-code') #retrieves the value associated with 'ws-code' from submitted form data. if key doesn't exist, code will be None.
        if workspaceCode.objects.filter(code=code, is_active=True).exists():
            ws_code = workspaceCode.objects.filter(
                code=code, is_active=True).values('code', 'ws_id') #retrieves the ws-code and ws-id 

            actual_code = check_code(ws_code) #validating the code and storing it in actual_code.

            if (code == actual_code):
                # check if the person is already part of this workspace
                if workspaceMember.objects.filter(workspace=workspace.objects.get(ws_id=ws_code[0]['ws_id']), customUser=customUser_,active=True).exists():
                    request.session['current_ws'] = str(ws_code[0]['ws_id'])
                    return redirect('home',customUser_)
                
                ws_member = workspaceMember(workspace=workspace.objects.get(
                    ws_id=ws_code[0]['ws_id']), customUser=customUser_) #creating a ws_member
                ws_member.save()

                request.session['current_ws'] = str(ws_code[0]['ws_id']) #storing 

                return redirect('home', custom_id)
            else:
                messages.error(request, message="Invalid Code!")
                return redirect('join-workspace', custom_id )
        else:
            messages.error(request,message="Invalid Code!")
            return redirect('join-workspace', custom_id)
    return render(request, 'partials/join_workspace.html')


def check_ws(ws_name):
    check = workspace.objects.filter(ws_name=ws_name).exists()
    return check


def new_workspace(request, custom_id):
    if request.method == "POST":
        ws_name = request.POST.get('ws_name')

        name_check = check_ws(ws_name) #checking whether ws already exists or not.

        if (not name_check):
            ws = workspace(ws_name=ws_name,
                           admin=customUser.objects.get(custom_id=custom_id))
            ws.save()

            ws_member = workspaceMember(workspace=workspace.objects.get(
                ws_id=ws.ws_id), customUser=customUser.objects.get(custom_id=custom_id))
            ws_member.save()
            code = workspaceCode.objects.filter( #retrieving the recent code from workspaceCode model
                ws=ws).order_by('-created_on').first()

            if not code or code.has_expired():
                if code: #if the code is exist and expired
                    code.regenerate_code()
                else:
                    expires_on = timezone.now() + timezone.timedelta(days=120)  # Set expiration duration
                    code = workspaceCode.objects.create(
                        ws=workspace.objects.get(ws_id=ws.ws_id),
                        code=workspaceCode().generate_unique_code(),
                        expires_on=expires_on
                    )
            code.save()
            # code = workspaceCode.objects.filter(
            #     ws=ws).order_by('-created_on').first()

            # if not code or code.has_expired():
            #     if code:
            #         code.regenerate_code()
            #     else:
            #         expires_on = timezone.now() + timezone.timedelta(days=120)  # Set expiration duration
            #         code = workspaceCode.objects.create(
            #             ws=workspace.objects.get(ws_id=ws.ws_id),
            #             code=workspaceCode.generate_unique_code(),
            #             expires_on=expires_on
            #         )
            #         code.save()
            request.session['current_ws'] = str(ws.ws_id)
            current_ws_id = request.session.get('current_ws', None)
            workspaces, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)
            profile_pic_url = get_google_profile_pic(request.user)
            custom_user = customUser.objects.get(user=request.user)
            return render(request, 'users/home.html', {'profie_pic_url':profile_pic_url,'custom_user':custom_user,'custom_id': custom_id, "ws_id": ws, 'code': code, 'workspaces': workspaces, 'current_ws': current_ws,
                   'flag': flag, 'ws_code': code, 'projects': projects})
        else:
            messages.error(request, 'Workspace name already exists!')
            return redirect('new_workspace', custom_id)

    return render(request, 'partials/new_workspace.html', {'custom_id': custom_id})


def add_project(request, custom_id): 
    # no need for access control, already controlling add prjct option in navabr
    current_ws_id = request.session.get('current_ws', None) #retrieves current_ws_id from session. no ws_id , default to None.
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    profile_pic_url = get_google_profile_pic(request.user)
    # Restrict project creation to the workspace admin only
    # if not access_control_admin(custom_id, current_ws):
    #     messages.error(request, "You do not have permission to create a project.")
    #     return redirect('home', custom_id=custom_id)  # Redirect to project view after creation

    
    ws_members = workspaceMember.objects.filter(workspace=current_ws, active=True)
    custom_user = customUser.objects.get(user=request.user)
    if request.method == "POST":
        project_name = request.POST.get('project_name')
        desc = request.POST.get('desc')
        prior = request.POST.get('priority')
        stat = request.POST.get('status')
        deadline = request.POST.get('deadline')

        lead = request.POST.getlist('lead')
        members = request.POST.getlist('members')
        for lead_ in lead:  # otherwise unique constraint failed
            if lead_ in members:
                members.remove(lead_)
        project = Project(name=project_name, description=desc, ws=current_ws)
        if deadline != None and deadline!="": #deadline is given.
            deadline = datetime.strptime(deadline, '%d-%m-%Y').date() #converting the deadline string into d-m-y.
            project.deadline = deadline
        if prior != None:
            priority_obj = get_object_or_404(priority, id=int(prior))
            project.priority = priority_obj
        if stat != None:
            status_obj = get_object_or_404(status, id=int(stat))
            project.status = status_obj
        project.save()
        for lead_id in lead:
            project_member_bridge.objects.create(project=Project.objects.get(
                project_id=project.project_id), team_member=customUser.objects.get(custom_id=lead_id), role='Lead')
        for member_id in members:

            member = get_object_or_404(customUser, custom_id=member_id)
            project_member_bridge.objects.create(
                project=project,
                team_member=member,
                role='Team member'
            )

        return redirect('project_view', project.project_id, custom_id)
    return render(request, 'users/add_project.html',
                  {'ws_members': ws_members, 'custom_id': custom_id,
                   'workspaces': ws, 'current_ws': current_ws,
                   'flag': flag, 'ws_code': code, 'projects': projects,'profile_pic_url':profile_pic_url,'custom_user':custom_user})

@csrf_exempt
def upload_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        upload_path = os.path.join(settings.MEDIA_ROOT, 'uploads', file.name)
        
        with open(upload_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        file_url = request.build_absolute_uri(settings.MEDIA_URL + 'uploads/' + file.name)
        return JsonResponse({'url': file_url})  # Return the URL to the editor
    
    return JsonResponse({'error': 'File upload failed'}, status=400)

def get_priority_status_list():
    statuses = status.objects.all()
    priorities = priority.objects.all()
    return statuses, priorities

def access_control(team, lead, custom_id):
    """
    rules:
    a workspace admin can change anything in the workspace (flag)
    project leads can change anything in their project (flag_lead)
    assignees can edit issues assigned to them (flag_assignee)
    only assignees should be able to change their issues
    in this function w only include access control for project related stuff
    add_issue,add_subissue option should be abailable to admin,team lead and respective members
    """
    # Checking whether the user can edit or not
    flag_lead = False 
    flag_member=False
    # Check if the user is the workspace admin
    # if str(custom_id) == str(current_ws.admin.custom_id):
    #     flag_edit = True
    #     print(f"Flag edit is: {flag_edit}") 

    # Check if the user is a lead 
    
    for leader in lead:
        if str(custom_id) == str(leader.team_member.custom_id):
            flag_lead = True
            break
    
    # Check if the user is a team member in the project
    for member in team:
        if str(custom_id) == str(member.team_member.custom_id):
            flag_member = True
            break
        
    return flag_lead, flag_member

def access_control_issues(issue_id,custom_id):
    """ rules: project leads must be able to change details of top level issues (flag_lead) (this is done in project view, because thy will be top level anyways)
    it should also be done in the top level issues' issue view (the upper part only)
    issue assignees can change details related to child issues. (flag_assignee)(this should be done in issue view, cos these are seen in that page only)
    this fn deals with access control on the issue page
    flag_assignee is done in the issue_view func
    """
    flag_lead = False
    
    # for top level issues
    issue_ = issue.objects.get(issue_id=issue_id)

    if issue_.parent_task == None: # top level
        issue_project = issue_.project
        flag_lead = project_member_bridge.objects.filter(
                    project=issue_project,
                    team_member=customUser.objects.get(custom_id=custom_id),
                    role='Lead',
                    active=True).exists()
    
    return flag_lead
    # for issues with parent issues
# def access_control_lead(custom_id,lead):
#     """ returns true if the 'custom_id' is among the project leads """
#     flag_lead = False
#     for leader in lead:
#         if str(custom_id) == str(leader.team_member.custom_id):
#             flag_lead = True
#             print(f"Flag edit granted to project lead: {custom_id}")
#             break
#     return flag_lead

# def access_control_admin(custom_id, current_ws):
#     flag_edit = False
#     # Checking whether the user can edit or not

#     # Check if the user is the workspace admin
#     if str(custom_id) == str(current_ws.admin.custom_id):
#         flag_edit = True
#         print(f"Flag edit is: {flag_edit}") 
#     return flag_edit
#     # Check if the user is a lead 
 

def access_control_assignee(issue, custom_id):
    # Checking if the current user is the assignee of the issue
    return issue.assignee.filter(custom_id=str(custom_id)).exists()

# def change_issue_status(request, project_id):
#     try:
#         issues = issue.objects.filter(project_id=project_id)
#         custom_id = request.user.customuser.custom_id  # Fetch the current user's custom_id

#         # Prepare a list to hold issue details with assignee status for each issue
#         issue_list = []
#         for issue_instance in issues:
#             # Check if the current user is an assignee for each issue using the helper function
#             is_assignee = access_control_assignee(issue_instance, custom_id)

#             # Add issue data along with assignee status to the list
#             issue_list.append({
#                 'issue': issue_instance,
#                 'is_assignee': is_assignee,
#             })

#         # Pass the issues along with assignee status to the template
#         context = {
#             'issue_list': issue_list,
#             'status': status.objects.all(),  # Assuming you have this passed from your view
#             'priority': priority.objects.all(),  
#         }
#         return render(request, 'project_view.html', context)

#     except issue.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'Issue does not exist.'})


def project_view(request, project_id, custom_id):
    # stuff for navbar
    current_ws_id = request.session.get('current_ws', None) #if no current_ws key, it defaults is None. to display the current ws
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    profile_pic_url = get_google_profile_pic(request.user)
    project = Project.objects.get(project_id=project_id) #retrieves the project
    team = project_member_bridge.objects.filter(
        project_id=project_id, role="Team member", active=True) #retrieves all the team members related to that project
    lead = project_member_bridge.objects.filter(
        project_id=project_id, role="Lead", active=True) #fetches lead of the project

    flag_lead,flag_member = access_control(team, lead, custom_id)
    
    statuses, priorities = get_priority_status_list() #fetches status and priority
    lead_user_ids = lead.values_list('team_member__custom_id', flat=True) #flat = true returns list instead of tuples. 
    team_ids = team.values_list('team_member__custom_id', flat=True) #to differentiate lead and team members

    # Get all users in the workspace
    workspace_members = workspaceMember.objects.filter(workspace=current_ws)
#     user_assignee_flag = issue_assignee_bridge.objects.filter(
#     issue=OuterRef('pk'), 
#     assignee=customUser.objects.get(custom_id=custom_id), 
#     active=True
# )
    custom_user = customUser.objects.get(user=request.user)
    unread_comments_subquery = Comments.objects.filter(
        issue=OuterRef('pk')
    ).exclude(
        read_by=custom_user  # Exclude comments read by the current user
    ).values('issue').annotate(
        unread_count=Count('id', distinct=True)
    ).values('unread_count')  # Only get the unread_count from the subquery
    user_assignee_flag = Subquery(
    issue_assignee_bridge.objects.filter(issue=OuterRef('pk'), assignee=custom_user).values('pk')[:1]
    )   
    issues = issue.objects.filter(project_id=project_id, parent_task__isnull=True).annotate(
        subissue_count=Count('child'), unread_comments_count=Subquery(unread_comments_subquery, output_field=IntegerField()),is_closed=Case(
            When(status=4, then=1), default=0, output_field=IntegerField()),is_assigned_to_user=Exists(user_assignee_flag)).order_by('is_closed','priority__id')

    context = {'project': project, 'lead': lead, 'team': team, 'status': statuses,
               'priority': priorities, 'issues': issues, 'workspace_memb': workspace_members,
               'lead_user_ids': lead_user_ids, 'team_ids': team_ids, 'workspaces': ws, 'current_ws': current_ws,
               'custom_user':custom_user,'flag': flag, 'ws_code': code, 'projects': projects, 'custom_id': custom_id, 'flag_member': flag_member, 'flag_lead': flag_lead, 'profile_pic_url':profile_pic_url}
         
    for issue_ in issues:
        print(issue_.unread_comments_count)
    return render(request, 'users\project_view.html', context)


def edit_project(request, project_id, custom_id):
    project = get_object_or_404(Project, project_id=project_id) #raises an error if project doesn't exist.

    current_ws = project.ws #getting the current workspace the project belongs to
    lead = project_member_bridge.objects.filter(project=project, role='Lead', active=True)
    team = project_member_bridge.objects.filter(project=project, active=True)  # Get all active team members

     # Check access control by passing the correct arguments: lead, custom_id, and current_ws
    # flag_edit = access_control_admin(custom_id, current_ws)
   
    # # Ensure only the workspace admin can edit
    # if not flag_edit:
    #     messages.error(request, "You do not have permission to edit this project.")
    #     return redirect('project_view', project_id=project_id, custom_id=custom_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('description')
        prior_id = request.POST.get('priority')
        status_id = request.POST.get('status')
        deadline = request.POST.get('deadline').strip()
        lead_ids = request.POST.getlist('lead')
        team_ids = request.POST.getlist('team')

# Update
        project.name = name
        project.description = desc

        if prior_id != None:
            project.priority = get_object_or_404(priority, id=prior_id)
        if status_id != None:
            project.status = get_object_or_404(status, id=status_id)

        # Check and update deadline
        if deadline:
            try:
                # Parse the deadline input from mm/dd/yyyy format
                deadline_date = datetime.strptime(deadline, '%d-%m-%Y').date()

                project.deadline = deadline_date  # Update the deadline in the project instance
            except ValueError as ve:
                # Handle invalid date format
                messages.error(request, 'Invalid date format. Please use dd-mm-yyyy.')
                return redirect('project_view', project_id=project_id, custom_id=custom_id)
        project.save()
    # update lead
        project_member_bridge.objects.filter(project=project).update(
            active=False)  # Remove current leads
        for lead_id in lead_ids:
            lead = get_object_or_404(customUser, custom_id=lead_id)
            if lead:
                lead_instance, created = project_member_bridge.objects.get_or_create(
                    team_member=lead, project=project)
                # Update lead details
                lead_instance.role = 'Lead'
                lead_instance.active = True
                lead_instance.save()

        # Update team members
        # project_member_bridge.objects.filter(project=project, role='Team member').update(
            # active=False)  # Remove current team members
        for team_id in team_ids:
            team_memb = get_object_or_404(customUser, custom_id=team_id)
            if str(team_memb.custom_id) in lead_ids:
                messages.warning(request, f"User {team_memb.user.first_name} is a lead and cannot be added as a team member.") # for maintaing unique constraint in model
                continue  
            if team_memb:
                team_instance, create = project_member_bridge.objects.get_or_create(
                    team_member=team_memb, project=project)
                # Update team member details
                team_instance.role = 'Team member'
                team_instance.active = True
                team_instance.save()

        messages.success(request, 'Project updated successfully!')
        return redirect('project_view', project_id=project_id, custom_id=custom_id)
        
    return redirect('project_view.html', project_id=project_id, custom_id=custom_id)


def edit_issue(request, issue_id, custom_id):
    _issue = get_object_or_404(issue, issue_id=issue_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc')
        prior_id = request.POST.get('priority')
        status_id = request.POST.get('status')
        deadline = request.POST.get('deadline').strip()
        assignee = request.POST.getlist('assignee')

# Update
        _issue.name = name
        _issue.description = desc
        if prior_id != None:
            _issue.priority = get_object_or_404(priority, id=prior_id)
        if status_id != None:
            _issue.status = get_object_or_404(status, id=status_id)
        if deadline != None and deadline != "":
            deadline = datetime.strptime(deadline, '%d-%m-%Y').date()
            _issue.deadline = deadline
        _issue.save()

    # update lead
        issue_assignee_bridge.objects.filter(issue=_issue).update(
            active=False)  # Remove current leads
        for _assignee in assignee:
            new_assignee = get_object_or_404(customUser, custom_id=_assignee)
            if new_assignee != None:
                assigned, create = issue_assignee_bridge.objects.get_or_create(
                    assignee=new_assignee, issue=_issue)
                assigned.active = True
                assigned.save()

        messages.success(request, 'Issue updated successfully!')
        return redirect('issue_view', issue_id, custom_id)
    return redirect('issue_view', issue_id, custom_id)


def update_issue_field(request):
    if request.method == "POST":
        issue_id = request.POST.get('issue_id')
        field_name = request.POST.get('field_name')
        value = request.POST.get('value')
        try:
            the_issue = issue.objects.get(issue_id=issue_id) #retrieving the issue.
        except issue.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Issue not found'}, status=404)
        
        if field_name == 'status':
            
            
            the_issue.status_id = int(value) 
            if not the_issue.completed  and int(value)==4:
                the_issue.mark_completed()
            elif int(value)!=4 and the_issue.completed:
                the_issue.completed=False
                the_issue.completed_date = None                
            
            the_issue.save()
        elif field_name == 'priority':
            the_issue.priority_id = value
            the_issue.save()
        elif field_name == 'assignee':
            try:
                the_assignee = customUser.objects.filter(custom_id__in=value)
                the_issue.assignee = the_assignee
                the_issue.save()
            except customUser.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Assignee not found'}, status=404)
        else:
            pass
        # Save the issue
        try:
            the_issue.save()
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


#updating projects priority, status, deadline from prject_view
from django.http import JsonResponse
from .models import Project
from datetime import datetime

# Combined function to update project fields (status, priority, deadline)
def update_project_field(request):
    if request.method == "POST":
        project_id = request.POST.get('project_id')
        field_name = request.POST.get('field_name')
        value = request.POST.get('value')
        the_project = Project.objects.get(project_id=project_id)
        # Get the current workspace and check for admin access
        current_ws = the_project.ws        
        try:
            # Fetch the custom user instance
            custom_user = customUser.objects.get(user=request.user)  # Get the custom user instance associated with the logged-in user
            custom_id = custom_user.custom_id  # Now access the custom_id from the custom user instance
        except customUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User does not have a custom profile.'}, status=404)
            
        # Access control: Only the admin of the workspace can edit the project
        is_member = project_member_bridge.objects.filter(project=the_project,team_member=custom_user).exists()

        # Handle deadline updates
        if field_name == 'deadline':
            try:
                # Convert the deadline to a date object
                deadline_date = datetime.strptime(value, '%d-%m-%Y').date()
                the_project.deadline = deadline_date
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date format.'}, status=400)

        else:
        # Update the appropriate field
            if field_name == 'status':
                previous_stat=the_project.status_id
                the_project.status_id = value
                if value==4 and previous_stat!=4:
                    the_project.mark_completed()
            elif field_name == 'priority':
                the_project.priority_id = value
            else:
                return JsonResponse({'success': False, 'error': 'Invalid field.'}, status=400)


        # Save the changes
        the_project.save()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)


#richtexteditor file uploading
@csrf_exempt  # Exempt from CSRF checks if handling via frontend directly
def file_upload_view(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        # You can save the file to the filesystem or the database
        with open(f'media/uploads/{uploaded_file.name}', 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        return JsonResponse({'status': 'READY:' + uploaded_file.name})
    return JsonResponse({'error': 'Invalid file upload'}, status=400)


# # updates status of the project by admin
# @require_POST
# def update_status(request, project_id):
#     print("update status is triggered from form")
#     project = get_object_or_404(Project, project_id=project_id)

#     # Check if the user is the workspace admin
#     current_ws_id = request.session.get('current_ws', None)
#     if current_ws_id is not None:
#         current_ws = get_object_or_404(workspace, ws_id=current_ws_id)  # Assuming you have a Workspace model
#         if str(request.user.customUser.custom_id) != str(current_ws.admin.custom_id):
#             return JsonResponse({'success': False, 'error': 'You do not have permission to edit the project status.'}, status=403)


#     new_status_id = request.POST.get('status_id')
#     if new_status_id:
#         new_status = get_object_or_404(status, id=new_status_id)
#         project.status = new_status
#         project.save()
#         return JsonResponse({'success': True, 'new_status': new_status.name})
# #     return JsonResponse({'success': False, 'error': 'invalid_status'})

def issue_view(request, issue_id, custom_id):

    the_issue = issue.objects.select_related('project').prefetch_related(
        'project__project_member_bridge_set').get(issue_id=issue_id)
    # if we dont put project__ as prefix in prefetch related, project member bridge instances for issue objects are searched, which doesnt exist
    current_ws_id = request.session.get('current_ws', None)

    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    profile_pic_url = get_google_profile_pic(request.user)
    project_members = project_member_bridge.objects.filter(
        active=True, project=the_issue.project)
    assignees = issue_assignee_bridge.objects.filter(
        active=True, issue=the_issue)
    assignee_ids = assignees.values_list('assignee__custom_id', flat=True)
   
    if uuid.UUID(custom_id) in assignee_ids:
        flag_assignee=True
    else:
        flag_assignee = False
    flag_lead = access_control_issues(issue_id,custom_id)
    user_assignee_flag = issue_assignee_bridge.objects.filter(
    issue=OuterRef('pk'), 
    assignee=customUser.objects.get(custom_id=custom_id), 
    active=True
)
    subIssues = issue.objects.filter(parent_task=issue_id).annotate(
        subissue_count=Count('child'), unread_comments_count=Count('comments', filter=~Q(comments__read_by=customUser.objects.get(user=request.user))),is_closed=Case(
            When(status=4, then=1), default=0, output_field=IntegerField()),is_assigned_to_user=Exists(user_assignee_flag)).order_by('is_closed','priority__id').order_by('priority__id')
    statuses, priorities = get_priority_status_list()
    custom_user = customUser.objects.get(user=request.user)
    context = {'subIssues': subIssues, 'issue': the_issue, 'issue_id': issue_id,
               "custom_id": custom_id, 'priority': priorities, 'status': statuses, 'workspaces': ws, 'current_ws': current_ws,
               'flag': flag,'flag_lead':flag_lead,'custom_user':custom_user,'flag_assignee':flag_assignee, 'ws_code': code, 'projects': projects,'profile_pic_url':profile_pic_url, 'project_members': project_members, 'assignee_id': assignee_ids, 'assignees': assignees}
    return render(request, 'users\issue_view.html', context)


def add_issue(request, custom_id, project_id):
    team_members = project_member_bridge.objects.filter(
        project=project_id, active=True)
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    profile_pic_url = get_google_profile_pic(request.user)
    if request.method == "POST":
        title = request.POST.get('title')
        desc = request.POST.get('desc')
        prior = request.POST.get('priority')
        stat = request.POST.get('status')
        deadline = request.POST.get('deadline')

        assignees = request.POST.getlist('assignees')

        issue_instance = issue(name=title, description=desc,
                               project=Project.objects.get(project_id=project_id))
        if deadline != None and deadline != "":
            deadline = datetime.strptime(deadline, '%d-%m-%Y').date()
            issue_instance.deadline = deadline
        if prior != None:
            priority_obj = get_object_or_404(priority, id=int(prior))
            issue_instance.priority = priority_obj
        if stat != None:
            status_obj = get_object_or_404(status, id=int(stat))
            issue_instance.status = status_obj
        issue_instance.save()

        for assignee_id in assignees:

            assignee = get_object_or_404(customUser, custom_id=assignee_id)
            issue_assignee_bridge.objects.create(
                issue=issue_instance,
                assignee=assignee)

        return redirect('project_view', project_id, custom_id)
    custom_user = customUser.objects.get(user=request.user)
    context = {'workspaces': ws, 'current_ws': current_ws, 'project_id': project_id,
               'flag': flag, 'ws_code': code, 'custom_user':custom_user,'projects': projects, 'custom_id': custom_id, 'team_members': team_members,'profile_pic_url':profile_pic_url}
    return render(request, 'users/add_issue.html', context)


def add_subIssue(request, issue_id, custom_id):
    print("add sub issue  is triggered")
    subIssue = issue.objects.get(issue_id=issue_id)
    team_members = project_member_bridge.objects.filter(
        project=subIssue.project, active=True)
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenever navbar is needed in a page
    profile_pic_url = get_google_profile_pic(request.user)
    if request.method == "POST":
        title = request.POST.get('title')
        desc = request.POST.get('desc')
        prior = request.POST.get('priority')
        stat = request.POST.get('status')
        deadline = request.POST.get('deadline').strip()
        assignees = request.POST.getlist('assignees')
        issue_instance = issue(name=title, description=desc, project=Project.objects.get(
            project_id=subIssue.project.project_id), parent_task=issue.objects.get(issue_id=issue_id))
        if deadline != None and deadline != "":
            deadline = datetime.strptime(deadline, '%d-%m-%Y').date()
            issue_instance.deadline = deadline
        if prior != None:
            priority_obj = get_object_or_404(priority, id=int(prior))
            issue_instance.priority = priority_obj
        if stat != None:
            status_obj = get_object_or_404(status, id=int(stat))
            issue_instance.status = status_obj
        issue_instance.save()

        for assignee_id in assignees:

            assignee = get_object_or_404(customUser, custom_id=assignee_id)
            issue_assignee_bridge.objects.create(
                issue=issue_instance,
                assignee=assignee)
        return redirect('issue_view', issue_id, custom_id)
    custom_user = customUser.objects.get(user=request.user)
    context = {'workspaces': ws, 'current_ws': current_ws, 'issue_id': issue_id,
               'flag': flag, 'ws_code': code, 'projects': projects,'custom_user':custom_user, 'custom_id': custom_id, 'team_members': team_members,'profile_pic_url':profile_pic_url}
    return render(request, 'users/add_subissue.html', context)

# comments
def get_issueComments(request, issue_id):
    custom_user= customUser.objects.get(user=request.user.id)

    comments = Comments.objects.filter(
        issue_id=issue_id, parent_comment__isnull=True).select_related('author', 'issue')
    if not comments.exists():

        return JsonResponse({'comments': [], 'message': 'No comments available.'})
    comment_data = []
    
    for comment in comments:
        
        if custom_user not in comment.read_by.all():
        
            comment.read_by.add(custom_user)
            
            
            comment.save()
        users = comment.read_by.all()
        for user in users:
            print(user.user.first_name)
        replies_data = []
        for reply in comment.replies.select_related('author').all():
            if custom_user not in reply.read_by.all():
                reply.read_by.add(custom_user)
                reply.save()
            replies_data.append({
                'id': reply.id,
                'author': reply.author.user.first_name + " " + reply.author.user.first_name,
                'text': reply.comment,
                'created_at': reply.created_at.strftime('%d-%m-%Y %H:%M')
            })
        comment_data.append({
            'id': comment.id,
            'author': comment.author.user.first_name + " " + comment.author.user.last_name,
            'text': comment.comment,
            'created_at': comment.created_at.strftime('%d-%m-%Y %H:%M'),
            'replies': replies_data
        })

        unread_count = issue.objects.get(issue_id=issue_id).unread_comments_count(custom_user)
    return JsonResponse({'comments': comment_data, 'unread_count': unread_count})


def submit_comment(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        comment_text = data.get('comment')
        issue_id = data.get('issue_id')

        try:
            the_issue = issue.objects.get(issue_id=issue_id)
            comment = Comments.objects.create(
                issue=the_issue,
                author=customUser.objects.get(user=request.user),
                comment=comment_text
            )
            comment.save()
            print(f"Submitting sentiment task for comment ID: {comment.id}")
            get_sentiment_task.delay(comment.id)
            return JsonResponse({'success': True, 'comment': {
                    'id': comment.id,
                    'author': comment.author.user.first_name + comment.author.user.last_name ,  
                    'text': comment.comment,
                    'created_at': comment.created_at.strftime('%d-%m-%Y %H:%M')
                }})
        except issue.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Issue not found'})
        except Exception as e:
            print(f"Error: {e}")  # Log the error for debugging
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': ' Invalid request method'})

def submit_replies(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        reply_text = data.get('reply')
        issue_id = data.get('issueId')
        comment_id = data.get('comment_id')  
        try:
            the_issue = issue.objects.get(issue_id=issue_id)
            parent_comment = Comments.objects.get(id=comment_id) 
            user = customUser.objects.get(user=request.user)
            
            reply = Comments.objects.create(
                issue=the_issue,
                author=user,
                comment=reply_text,
                parent_comment=parent_comment  # Assign parent comment (which can be another reply)
            )
           
            return JsonResponse({
                'success': True,
                'reply': {
                    'id': reply.id,
                    'author': reply.author.user.first_name + reply.author.user.last_name,  
                    'text': reply.comment,
                    'created_at': reply.created_at.strftime('%d-%m-%Y %H:%M'),
                    'parent_comment_id': reply.parent_comment.id,  # Return parent comment ID to help handle nesting
                    'issue':reply.issue.issue_id
                }
            })
        except issue.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Issue not found'})
        except Comments.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Parent comment not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def check_if_project_lead(custom_id,current_ws_id):
    """ checks if user is a project lead in the current ws """
    projects = project_member_bridge.objects.filter(team_member=custom_id, role='Lead', project__ws__ws_id=current_ws_id)
    
    return projects.exists()

def get_project_deadlines_with_leads(active_projects):
    """ returns the deadlines of projects if they lie in the current month, along with lead names"""
    active_deadlines = []
    today = date.today()
    for project in active_projects:
        if project.deadline and project.deadline.year == today.year and project.deadline.month == today.month: 
            leads = [bridge.team_member for bridge in project.project_member_bridge_set.filter(role='Lead')]    
            active_deadlines.append({project.deadline:leads})
    return active_deadlines

def resource_allocation_details(active_projects):
    """ returns count of members in each project"""
    resource_details = {}
    for project in active_projects:
        members = project.team.all().distinct()
        member_count = len(members)
        resource_details[project.name] = member_count
    
    return resource_details
            
def get_closed_tasks_last_week(current_ws_id):
    """ returns the number of tasks closed in each project over last 7 days including projects with no closed tasks"""
    # Define the time range for the last week
    one_week_ago = timezone.now() - timedelta(days=7)

    closed_tasks_count = (
        Project.objects 
        .filter(ws__ws_id=current_ws_id, completed=False) 
        .annotate(
            closed_count=Count(
                'issues', 
                filter=Q(issues__completed_date__gte=one_week_ago, issues__status=4)  # Filter for closed tasks in the last week
            ),
            urgent_priority_count=Count(
                'issues',
                filter=Q(issues__priority=1, issues__completed_date__gte=one_week_ago, issues__status=4)
            ),
            high_priority_count=Count(
                'issues',
                filter=Q(issues__priority=2, issues__completed_date__gte=one_week_ago, issues__status=4)
            ),
            medium_priority_count=Count(
                'issues',
                filter=Q(issues__priority=3, issues__completed_date__gte=one_week_ago, issues__status=4)
            ),
            low_priority_count=Count(
                'issues',
                filter=Q(issues__priority=4, issues__completed_date__gte=one_week_ago, issues__status=4)
            ),
            no_priority_count=Count(
                'issues',
                filter=Q(issues__priority=5, issues__completed_date__gte=one_week_ago, issues__status=4)
            )
        )

    )
    
    return closed_tasks_count

def get_active_issues(current_ws_id):
    """ returns project wise active issues (for ws insights) """
    active_issues_per_project = (
        issue.objects
        .filter(project__ws__ws_id = current_ws_id)
        .exclude(status=4)  # Filter active issues
        .values('project')  # Group by project
        .annotate(active_count=Count('issue_id'))  # Count the active issues
    )

    return active_issues_per_project

def get_active_issue_count(active_issues_per_project):
    """ returns total active number of active issues in the current ws (for ws insights)"""
    active_issue_count = 0
    for project in active_issues_per_project:
        active_issue_count += project['active_count']
    return active_issue_count

def load_admin_specific_insights(custom_id, current_ws_id):
    """ loads insights for dashboard of ws admin """

    # project count
    project_count = Project.objects.filter(ws=current_ws_id).distinct().count()
    # active vs inactive projects 
    active_projects = Project.objects.filter(ws=current_ws_id, completed=False).distinct()
    active_projects_count = len(active_projects)
    # project progress(gannt) - already in default dashboard
    admin_insights = {'project_count': project_count, 'active_projects':active_projects, 'active_projects_count': active_projects_count}
    # upcoming deadlines
    if active_projects_count > 0:

        active_deadlines_w_leads = get_project_deadlines_with_leads(active_projects)
        if active_deadlines_w_leads is None:
            active_deadlines_w_leads = 0
        # Resource Allocation: Pie chart showing the allocation of resources (e.g., team members) across projects
        resource_details = resource_allocation_details(active_projects)
        # get the number of tasks closed by each project team in the last week (barchart)
        closed_tasks_last_week = get_closed_tasks_last_week(current_ws_id)
        # for card
        closed_tasks_last_week_num = closed_tasks_last_week.aggregate(total_closed=Sum('closed_count'))['total_closed'] or 0
        # barchart active issues per project
        project_wise_active_issues = get_active_issues(current_ws_id)
        active_issue_count = get_active_issue_count(project_wise_active_issues)
        admin_insights.update({'active_deadlines_w_leads': active_deadlines_w_leads, 'resource_details': resource_details, 'active_count': active_issue_count,
            'closed_tasks_last_week_num': closed_tasks_last_week_num,'closed_tasks_last_week': closed_tasks_last_week, 'project_wise_active_issues': project_wise_active_issues
            })
    return admin_insights

def get_projects_lead(custom_id, current_ws_id):
    """ retrieves a list of projects the user leads """
    projects_led = Project.objects.filter(
        project_member_bridge__team_member=custom_id, 
        project_member_bridge__role='Lead',
        ws=current_ws_id
    )
    

    return projects_led


def check_overdue(project_id):
    """ count number of tasks which are over due, retriev them and show as list 
    with assignees ordered in descending order of overdue days  (for project insights) """
    project = Project.objects.get(project_id=project_id)
    overdue_issues = (
        issue.objects.filter(
        project=project, 
        deadline__lt=timezone.localtime(timezone.now()).date(), 
        completed=False
    )
    .annotate(
        overdue_days=ExpressionWrapper(
                timezone.localtime(timezone.now()).date() - F('deadline'),
                output_field=fields.DurationField()
            )
        )
    )

    for issue_ in overdue_issues:
        issue_.overdue_days = (timezone.localtime(timezone.now()).date() - issue_.deadline).days  # Calculate overdue days
    
    # Sort issues by overdue days in descending order
    overdue_issues = sorted(overdue_issues, key=lambda x: x.overdue_days, reverse=True)
    return overdue_issues
    # overdue = []
    # for task in overdue_issues:
    #     assignees = task.assignee.all()
    #     overdue_by=(timezone.now().date()-task.deadline).days
    #     overdue.append({
    #         'task': task.name,
    #         'assignees': [user.user.username for user in assignees],
    #         'overdue by':overdue_by
    #     })
    
    

def task_priority(project_id):
    """ gets piechart data for number of tasks of varying priority (for project view), breakdown into completed and incompleted """
    project = Project.objects.get(project_id=project_id)
    task_status = issue.objects.filter(project=project).values('priority__name').annotate(
    total_issues=Count('issue_id'),
    completed_issues=Count('issue_id', filter=Q(completed=True)),
    in_progress_issues=Count('issue_id', filter=Q(completed=False))
    )
    return task_status

# def issues_per_team_member(project_id):
#     """ retrieve info on the number of issues assigned to each workspace member """
#     project = Project.objects.get(project_id=project_id)
#     team_issues = issue_assignee_bridge.objects.filter(issue__project=project).values(
#         'assignee__user__username', 'issue__priority__name'
#     ).annotate(
#         total_issues=Count('issue')
#     )
    
#     return team_issues

# def show_top_critical_issue(project_id):
#     """ urgent and high-priority issues that are unresolved, and showing the time they have remained open."""
#     project = Project.objects.get(project_id=project_id)
#     critical_issues = issue.objects.filter(
#         project=project,
#         priority__name__in=['Urgent', 'High Priority'],
#         completed=False
#     ).order_by('created_on')
    
#     results = []
#     for task in critical_issues:
#         open_duration = (timezone.now() - task.created_on).days  # Days since the task was created
#         results.append({
#             'task': task.name,
#             'priority': task.priority.name,
#             'open_for_days': open_duration
#         })
    
#     return results


def tasks_completed_last_week(project_id):
    """ breakdown by team member (for project view)"""
    project = Project.objects.get(project_id=project_id)
    one_week_ago = timezone.now() - timedelta(days=7)
    completed_issues = issue.objects.filter(project=project, completed=True, completed_date__gte=one_week_ago)
    
    team_completed = completed_issues.values('assignee__user__first_name').annotate(
        total_completed=Count('issue_id')
    )
    
    return team_completed

def tasks_assigned_per_member(project_id):
    """shows work division between members of a proejct (for project view)"""
    project = Project.objects.get(project_id=project_id)
    issues = issue.objects.filter(project=project)
    
    members_assigned = issues.values('assignee__user__first_name').annotate(
        issue_count=Count('issue_id')
    )
    
    return members_assigned

def count_tasks_completed_last_week(project_id):
    project = Project.objects.get(project_id=project_id)
    one_week_ago = timezone.now() - timedelta(days=7)
    return issue.objects.filter(project=project, completed=True, completed_date__gte=one_week_ago).count()
 

def active_issues(project_id):
    project = Project.objects.get(project_id=project_id)
    return issue.objects.filter(project=project, completed=False).count()

def tasks_completion_rate(project_id):
    """ get task completion rate (for project dashboard)"""

    all_issues = issue.objects.filter(project=Project.objects.get(project_id=project_id))  # Get all tasks for the project
    total_issues = all_issues.count()  # Get total number of tasks
    completed_issues = all_issues.filter(status=4).count()  # Count only completed tasks
    
    if total_issues == 0:  # Avoid division by zero
        return 0
    
    # Calculate completion rate as a percentage
    completion_rate = (completed_issues / total_issues) * 100
    return round(completion_rate, 2)  
    
def team_sentiment_analysis(project_id):
    
    # Assuming Comment model has a sentiment field storing 'positive', 'neutral', or 'negative'
    comments = Comments.objects.filter(issue__project__project_id=project_id)  # Fetch all comments
    if not comments.exists():
        return "No comments available for analysis."
    
    # Aggregating sentiments
    positive = comments.filter(sentiment_score=1).count()
    neutral = comments.filter(sentiment_score=0).count()
    negative = comments.filter(sentiment_score=-1).count()

    total_comments = comments.count()
    
    # Calculate sentiment percentages
    sentiment_summary = {
        "positive_percentage":round( (positive / total_comments) * 100,2),
        "neutral_percentage": round((neutral / total_comments) * 100,2),
        "negative_percentage": round((negative / total_comments) * 100,2)
    }
    
    return sentiment_summary




def get_project_insights( project_id):
    active_issues_ = active_issues(project_id)
    tasks_closed_last_week_count = count_tasks_completed_last_week(project_id)
    tasks_completed_last_week_by_member  = tasks_completed_last_week(project_id)
    work_division = tasks_assigned_per_member(project_id)
    overdue_tasks = check_overdue(project_id)
    task_priorities = task_priority(project_id)
    task_completion_rate = tasks_completion_rate(project_id)
    sentiment_summary = team_sentiment_analysis(project_id)
    context = {'active_issues':active_issues_, 'tasks_closed_last_week_count':tasks_closed_last_week_count,
               'tasks_completed_last_week':tasks_completed_last_week_by_member, 'work_division': work_division,
               "overdue_tasks":overdue_tasks, 'task_priorities':task_priorities,'task_completion_rate':task_completion_rate,
               'sentiment_summary': sentiment_summary}
    return context
def g_login(request):
    user_id=request.user.id 
    custom_user=customUser.objects.get(user=user_id)
    custom_id = custom_user.custom_id
    print(custom_id)
    if custom_user.last_ws: #already joined workspace
        request.session['current_ws'] = str(custom_user.last_ws.ws_id) #the last_ws id is stored in session as current_ws
    else:
        first_workspace = workspaceMember.objects.filter(customUser=custom_user).first() #retrieves the first workspace the user is a member of.
        if first_workspace: #atleast one workspace
            request.session['current_ws'] = str(first_workspace.workspace.ws_id)
            
        else:
            return redirect('first-signin', custom_id)
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)
    
    return redirect('dashboard')
# dashboard
def dashboard(request):
    """ sends user to dashboard based on their role """
    
    user_id=request.user.id 
    custom_user=customUser.objects.get(user=user_id)
    custom_id = custom_user.custom_id
   
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)
    profile_pic_url = get_google_profile_pic(request.user)
    # for all users 
    # treemap of priority
    treemap_data, priority_count = treemap_of_priority(custom_id,current_ws_id)
    # pie chart
    pie_data, status_count = status_pie(custom_id,current_ws_id)
    gantt = gantt_data(projects)
    custom_user = customUser.objects.get(user=request.user)
    scatter = scatter_plot_with_time(custom_id, current_ws_id)
    context = {'custom_id':custom_id,'workspaces': ws, 'current_ws': current_ws,
                'flag': flag, 'ws_code': code, 'projects': projects, 'treemap_data':treemap_data,
                    'priority_count':priority_count, 'pie_data':pie_data,
                    'status_count': status_count, 'gantt':gantt,'custom_user':custom_user, 'scatter':scatter, 'profile_pic_url':profile_pic_url}
   
 
    is_project_lead = check_if_project_lead(custom_id,current_ws_id)
       #  Additional data for workspace admins
    if flag:
       
        admin_specific_data = load_admin_specific_insights(custom_id,current_ws_id)
        if admin_specific_data is not None:
            context.update(admin_specific_data)
        if is_project_lead: # check if user is ws admin AND a project lead
            context.update({'is_project_lead':True})
            projects_lead = get_projects_lead(custom_id,current_ws_id) 

            if projects_lead is not None:
                project_details = []
                for project in projects_lead:
                    project_insights = get_project_insights(project.project_id)
                    project_insights.update({'project_name':project})
                    if project_insights is not None:
                        project_details.append(project_insights)  
                        # project_Details looks like [{project1_insights},{project2_insight}]
                print(project_details)      
                context.update({'project_details':project_details})
                #updating context here becuase projects_lead would have been empty if projects_lead was none
            # project_details:[{project_name:project,insigth1:insight1,insight2:insight2},{project_name:project,insigth1:insight1,insight2:insight2}]
        return render(request,'dashboard\ws_admin_dashboard.html',context)
    elif is_project_lead: # users who are not ws admin but is project lead
        context.update({'is_project_lead':True})
        projects_lead = get_projects_lead(custom_id,current_ws_id)
        if projects_lead is not None:
                project_details = []
                for project in projects_lead:
                    project_insights = get_project_insights(project.project_id)
                    project_insights.update({'project_name':project})
                    if project_insights is not None:
                        project_details.append(project_insights)  
                        # project_Details looks like [{project1_insights},{project2_insight}]
               
                context.update({'project_details':project_details})
        return render(request,'dashboard\ws_admin_dashboard.html',context)
    else:
        return render (request,'dashboard\default_dashboard.html', context)

# default dashboard
def treemap_of_priority(custom_id,current_ws_id):
    """ retrieves all active & pending issues assigned to a person and sorts them into priority groups """

    issues_assigned = issue_assignee_bridge.objects.filter(
                        assignee=custom_id,active=True, issue__project__ws__ws_id=current_ws_id).exclude(
                                    issue__status=4).select_related('issue', 'issue__project')
    
    tree_data = {'Urgent':{}, 'High Priority':{}, 'Medium Priority':{}, 'Low Priority':{},
                  'No Priority':{}}
    priority_count = {'Urgent':0, 'High Priority':0, 'Medium Priority':0, 'Low Priority':0,
                  'No Priority':0}
    for issue in issues_assigned:
        if issue.issue.priority:
            prior = issue.issue.priority.name
        else:
            prior = "No Priority"
        
        project = issue.issue.project.name            
        tree_data[prior][project] = tree_data[prior].get(project,0) + 1
        priority_count[prior] += 1
    

    return tree_data, priority_count

def status_pie(custom_id,current_ws_id):
    """ retrievs active issues in the current ws and their statuses assigned to user with given custom_id """
    issues_assigned = issue_assignee_bridge.objects.filter(
                        assignee=custom_id,active=True, issue__project__ws__ws_id=current_ws_id).select_related('issue', 'issue__project')
    
    pie_data = {'Open':{}, 'In progress':{}, 'Paused':{}, 'Closed':{}}
    status_count = {'Open':0, 'In progress':0, 'Paused':0, 'Closed':0}

    for issue in issues_assigned:
        if issue.issue.status:
            stat = issue.issue.status.name
        else:
            stat = "Open"
        project = issue.issue.project.name
        pie_data[stat][project] = pie_data[stat].get(project,0) + 1
        status_count[stat] += 1
    
    return pie_data, status_count

def gantt_data(projects):
    gantt = {}
    for project in projects:

        lead = project_member_bridge.objects.filter(
        project_id=project.project_id, role="Lead", active=True)
        gantt[project.name] = {'project':project,'lead':lead,'issues':{},'completion_percent':0}
        top_level_issues = issue.objects.filter(project=project,parent_task__isnull = True)
        project_issues=top_level_issues.count()
        project_issue_completed=0
        
        for issue_ in top_level_issues:
        
            assignees = issue_assignee_bridge.objects.filter(
            active=True, issue=issue_)
            if issue_.status==4:
                project_issue_completed+=1
            if not issue_.deadline:
                deadline=date.today()+timedelta(days=60)
            else:
                deadline=issue_.deadline
            # check for child tasks
            sub_issues = issue.objects.filter(project=project,parent_task = issue_)

            if len(sub_issues)!=0:
                total=len(sub_issues)
                
                completed=sub_issues.filter(status=3).count()
                percent=round((completed/total),2)
            else:
                # No sub-issues; determine based on the main issue's status
                if issue_.status:
                    if issue_.status.name == 'Closed':
                        percent = 1  # Issue is completed (100%)
                    else:
                        percent = 0  # Issue is not completed (0%)

            project_completion_percent=round(project_issue_completed/project_issues, 2)

            gantt[project.name]['issues'][issue_.name] = {'issue':issue_,'assignees':assignees,'created_on':issue_.created_on.date().strftime('%Y-%m-%d'),'deadline':deadline.strftime('%Y-%m-%d'),'percent':percent} # sending created on separately cos otherwise, too much processing in front end
            gantt[project.name]['completion_percent']=project_completion_percent
    return gantt


def scatter_plot_with_time(custom_id,ws_id):
    issues_=issue.objects.filter(completed=True,assignee=custom_id,project__ws=ws_id)
    
    issue_data = []
    for i in issues_:
        if i.deadline and i.completed_date: # should have deadline as well
            # expected duration
            expected_duration = (i.deadline - i.created_on.date()).days
            actual_duration = (i.completed_date.date() - i.created_on.date()).days
            issue_data.append({
                "name":i.name,
                "category":i.priority.id,
                "expected_duration":expected_duration,
                "actual_duration":actual_duration
            })
    
    return issue_data

# ws admin dashboard

# user profile
def user_profile(request,custom_id):
    current_ws_id = request.session.get('current_ws', None)
    req_user = customUser.objects.get(user=request.user).custom_id # user who is sending the request
    profile_owner = False
    print(type(req_user))
    print(type(custom_id))
    print(str(req_user) == custom_id)
    if str(req_user) == custom_id:
        profile_owner = True
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)
    custom_user = customUser.objects.get(custom_id=custom_id)
    profile_pic_url = get_google_profile_pic(customUser.objects.get(custom_id=req_user).user)
    searched_profile_pic_url = get_google_profile_pic(customUser.objects.get(custom_id=custom_id).user)

        # The result will include the 'a3/media/' part, 
    workspace_count = workspaceMember.objects.filter(active=True, customUser=customUser.objects.get(custom_id=custom_id)).count()
    projects_lead_count = project_member_bridge.objects.filter(team_member=customUser.objects.get(custom_id=custom_id),role='Lead').count()
    completed_project_count = project_member_bridge.objects.filter(team_member=customUser.objects.get(custom_id=custom_id), project__status = 4).count()
    handled_issues_count = issue_assignee_bridge.objects.filter(assignee=customUser.objects.get(custom_id=custom_id),issue__status=4).count()
  
    context = {"custom_id": custom_id,'searched_profile_pic_url':searched_profile_pic_url, 'workspaces': ws, 'current_ws': current_ws,
               'flag': flag, 'ws_code': code, 'projects': projects, 'custom_user':custom_user,'profile_pic_url':profile_pic_url,'workspace_count':workspace_count,'projects_lead_count':projects_lead_count,
               'completed_project_count':completed_project_count, 'handled_issues_count':handled_issues_count, 'profile_owner':profile_owner}
    return render(request, 'users/user_profile.html', context)

def edit_profile(request,custom_id):
    if request.method == 'POST':
        email_id = request.POST.get('email')
        profile_pic = request.FILES.get('file')
        customer = customUser.objects.get(custom_id=custom_id)
        customer.email = email_id
        if profile_pic:
            customer.profile_pic = profile_pic
        customer.save()
        return redirect('user-profile',custom_id)
    
# manage ws
def manage_workspace(request, custom_id, ws_id):
    
    ws, current_ws, projects, flag, code = req_for_navbar(custom_id, ws_id)
    workspace_members=workspaceMember.objects.filter(workspace=ws_id)
    
    project_count_for_members = []
    
    for member in workspace_members:
        project_count = project_member_bridge.objects.filter(team_member=custom_id, active=True, project__ws__ws_id=ws_id).count()
        project_count_for_members.append(project_count)
    
    context = {"custom_id": custom_id, 'workspaces': ws, 'current_ws': current_ws,
               'flag': flag, 'ws_code': code, 'projects': projects, 'members':workspace_members, 'project_count':project_count_for_members}
    return render(request,'users/manage_ws.html',context)

def remove_ws_member(request, user_custom_id, custom_id, ws_id):
    """ removes user with custom_id 'custom_id' from workspace having id 'ws_id' """
    ws_member=workspaceMember.objects.get(workspace=ws_id,customUser=custom_id)
    ws_member.delete()
    
    messages.success(request,"Workspace member removed succesfully")
    return redirect('manage_ws',user_custom_id,ws_id )

def deactivate_ws_member(request, user_custom_id, custom_id, ws_id):
    """ deactivates, not remove a user with id 'custom_id' from ws with id 'ws_id' """
    ws_member=workspaceMember.objects.get(workspace=ws_id,customUser=custom_id)
    ws_member.active = False
    ws_member.save()
    messages.success(request,"Workspace member deactivated succesfully")
    return redirect('manage_ws',user_custom_id,ws_id )




def toggle_ws_member_status(request, user_custom_id, custom_id, ws_id):
    """Toggles the active status of a workspace member."""
    ws_member = workspaceMember.objects.get(workspace=ws_id, customUser=custom_id)
    ws_member.active = not ws_member.active  # Toggle the status
    ws_member.save()

    # Return a JSON response with the new status
    return JsonResponse({
        'success': True,
        'active': ws_member.active,
        'user':user_custom_id
    })
    
def create_new_code(request,custom_id,ws_id):
    new_code = create_code(ws_id)
    return JsonResponse({'new_code': new_code}) 


# send email invites




@csrf_exempt
def send_invite_emails(request, custom_id, ws_id):
    if request.method == 'POST':
        emails = request.POST.getlist('emails[]')  # Retrieve the list of emails from the request
        workspace_ = workspace.objects.get(ws_id=ws_id) 
        ws_code = workspaceCode.objects.filter(ws=workspace_, is_active=True).first()

        if ws_code:
            code = ws_code.code  # Access the code
        else:
            code=create_code(ws_id)

        send_email_task.delay(emails,workspace_.ws_name,code)
                
        return JsonResponse({'message': 'Invitations sent successfully'})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def search_user(request):
    current_ws_id = request.session.get('current_ws', None)
    custom_id = customUser.objects.get(user=request.user).custom_id
    ws, current_ws, projects, flag, code = req_for_navbar(custom_id, current_ws_id)
    users = []
    query = request.POST.get('search-input', '')
    profile_pic_url = get_google_profile_pic(request.user)
    if query:
        queries = Q()
        query = query.strip()
        terms = query.split()
        for term in terms:
            queries |= Q(user__first_name__icontains=term) | Q(user__last_name__icontains=term) | Q(user__username__icontains = term)
        users = customUser.objects.filter(queries)
        google_profile = []
        for user in users:
            print(user.user)
            google_profile.append(get_google_profile_pic(user.user))

    user_details = list(zip(users,google_profile))  
    
    return render(request, 'users\search_results.html', {'user_details':user_details, 'profile_pic_url':profile_pic_url,'users': users, 'query': query,'workspaces':ws,'current_ws':current_ws,'projects':projects,'flag':flag,'code':code, 'custom_id':custom_id})

def get_user(user_id):
    custom_id = customUser.objects.get(user = user_id)
    return redirect('user-profile',custom_id)