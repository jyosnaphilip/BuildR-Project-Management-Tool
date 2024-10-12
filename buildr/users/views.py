# Create your views here.

from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import customUser, workspace, workspaceMember, workspaceCode, Project, priority, status, project_member_bridge, issue, issue_assignee_bridge, Comments
from django.utils import timezone
import json
from datetime import datetime
from django.http import JsonResponse
from django.db.models import Count
from django.core.exceptions import PermissionDenied, ValidationError
import random
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date  # Make sure to import this if you're parsing dates




def check_code(ws_code):
    ws_code = workspaceCode.objects.get(
        code=ws_code[0]['code'], is_active=True)
    if ws_code.has_expired():
        ws_code.regenerate_code()
        return ws_code.code
    else:
        return ws_code.code

def create_code(ws_id):
    ws_code = workspaceCode(ws_id=ws_id)
    ws_code.regenerate_code()
    ws_code.save()
    return ws_code.code

def get_projects(ws_id):
    projects = Project.objects.filter(ws=ws_id.ws_id).distinct()
    return projects

def req_for_navbar(custom_id, current_ws_id): #retrieves workspaces, current workspaces, projects. if user is admin, it fetches or creates a workspace code.dd-
    ws = get_ws(custom_id, current_ws_id)  # all ws #nav
    current_ws = workspace.objects.get(ws_id=current_ws_id) #retrieves current_ws based on current_ws_id
    projects = get_projects(current_ws)  # nav #retrieve projects associated with the current workspace.
    if str(current_ws.admin.custom_id) == custom_id:  # nav
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
    # if request.user.is_authenticated:
    # print("i am here")
    # return redirect('dashboard')
    current_ws_id = request.session.get('current_ws', None)  # nav #session store and retrieve data of a particular user.
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    user_issues = issue.objects.filter(
        project__ws__ws_id=current_ws_id, issue_assignee_bridge__assignee=custom_id) #fetches all issues assigned to the current user for current workspace.
    return render(request, 'users\home.html', {'custom_id': custom_id, 'workspaces': ws, 'current_ws': current_ws, 'flag': flag, 'ws_code': code, 'projects': projects, 'user_issues': user_issues}) #renders home page including custom ID, workspaces, current workspace. projects, user issues, flag for admin status

def change_ws(request):
    if request.method == 'POST' and request.user.is_authenticated:
        data = json.loads(request.body) #loading the request body as json data
        ws_id = data.get('ws_id')
        custom_user = customUser.objects.get(user=request.user) #retrieves customuser object for authenticated user
        if workspaceMember.objects.filter(customUser=custom_user, workspace__ws_id=ws_id).exists(): #customUser in workspaceMember 
            request.session['current_ws'] = ws_id #updating the current workspace id in the users session
            return JsonResponse({'status': 'success'})
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
            print("Password not matching")
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


def join_workspace(request, custom_id):
    if request.method == "POST":
        code = request.POST.get('ws-code') #retrieves the value associated with 'ws-code' from submitted form data. if key doesn't exist, code will be None.
        if workspaceCode.objects.filter(code=code, is_active=True).exists():
            ws_code = workspaceCode.objects.filter(
                code=code, is_active=True).values('code', 'ws_id') #retrieves the ws-code and ws-id 

            actual_code = check_code(ws_code) #validating the code and storing it in actual_code.

            if (code == actual_code):

                ws_member = workspaceMember(workspace=workspace.objects.get(
                    ws_id=ws_code[0]['ws_id']), customUser=customUser.objects.get(custom_id=custom_id)) #creating a ws_member
                ws_member.save()

                request.session['current_ws'] = str(ws_code[0]['ws_id']) #storing 

                return redirect('home', custom_id)
            else:
                messages.error("Invalid Code!")
                return redirect('join_workspace')
        else:
            messages.error("Invalid Code!")
            return redirect('join_workspace')
    return render(request, 'partials/join_workspace.html', {'custom_id': custom_id})


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
                        code=workspaceCode.generate_unique_code(),
                        expires_on=expires_on
                    )
                    code.save()

                return render(request, 'users/home.html', {'custom_id': custom_id, "ws_id": ws, 'code': code})
            else:
                messages.error(request, 'Code incorrect!')
            return redirect('new_workspace', custom_id)

    return render(request, 'partials/new_workspace.html', {'custom_id': custom_id})


def add_project(request, custom_id):  # need to check again
    current_ws_id = request.session.get('current_ws', None) #retrieves current_ws_id from session. no ws_id , default to None.
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    
    # Restrict project creation to the workspace admin only
    if not access_control_admin(custom_id, current_ws):
        messages.error(request, "You do not have permission to create a project.")
        return redirect('home', custom_id=custom_id)  # Redirect to project view after creation

    
    ws_members = workspaceMember.objects.filter(workspace=current_ws, active=True)

    if request.method == "POST":
        project_name = request.POST.get('project_name')
        desc = request.POST.get('desc')
        prior = request.POST.get('priority')
        stat = request.POST.get('status')
        deadline = request.POST.get('deadline')

        lead = request.POST.getlist('lead')
        members = request.POST.getlist('members')

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
                   'flag': flag, 'ws_code': code, 'projects': projects})


def get_priority_status_list():
    statuses = status.objects.all()
    priorities = priority.objects.all()

    return statuses, priorities

def access_control(team, lead, custom_id, current_ws):
    # Checking whether the user can edit or not
    flag_edit = False 

    # Check if the user is the workspace admin
    if str(custom_id) == str(current_ws.admin.custom_id):
        flag_edit = True
        print(f"Flag edit is: {flag_edit}") 

    # Check if the user is a lead 
    else:
        for leader in lead:
            if str(custom_id) == str(leader.team_member.custom_id):
                flag_edit = True
                print(f"Flag edit granted to project lead: {custom_id}")
                break
    
    # Check if the user is a team member in the project
    if not flag_edit:
        for member in team:
            if str(custom_id) == str(member.team_member.custom_id):
                flag_edit = True
                print(f"Flag edit granted to project member: {custom_id}")
                break
        
    return flag_edit

def access_control_admin(custom_id, current_ws):
    flag_edit = False

    if str(custom_id) == str(current_ws.admin.custom_id):
        flag_edit = True
        print(f"Flag edit is: {flag_edit}")
        print(f"Custom ID: {custom_id}, Workspace ID: {current_ws}, Admin: {current_ws.admin.custom_id}")

    return flag_edit

def access_control_assignee(issue, custom_id):
    # Checking if the current user is the assignee of the issue
    return issue.assignee.filter(custom_id=str(custom_id)).exists()

def change_issue_status(request, project_id):
    print("change issue status is triggered")
    try:
        issues = issue.objects.filter(project_id=project_id)
        custom_id = request.user.customuser.custom_id  # Fetch the current user's custom_id

        # Prepare a list to hold issue details with assignee status for each issue
        issue_list = []
        for issue_instance in issues:
            # Check if the current user is an assignee for each issue using the helper function
            is_assignee = access_control_assignee(issue_instance, custom_id)

            # Add issue data along with assignee status to the list
            issue_list.append({
                'issue': issue_instance,
                'is_assignee': is_assignee,
            })

        # Pass the issues along with assignee status to the template
        context = {
            'issue_list': issue_list,
            'status': status.objects.all(),  # Assuming you have this passed from your view
            'priority': priority.objects.all(),  
        }
        return render(request, 'project_view.html', context)

    except issue.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Issue does not exist.'})


def project_view(request, project_id, custom_id):
    print(" project view is triggered")
    # stuff for navbar
    current_ws_id = request.session.get('current_ws', None) #if no current_ws key, it defaults is None. to display the current ws
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page

    project = Project.objects.get(project_id=project_id) #retrieves the project
    team = project_member_bridge.objects.filter(
        project_id=project_id, role="Team member", active=True) #retrieves all the team members related to that project
    lead = project_member_bridge.objects.filter(
        project_id=project_id, role="Lead", active=True) #fetches lead of the project
    

    flag_edit = access_control(team, lead, custom_id, current_ws)

    statuses, priorities = get_priority_status_list() #fetches status and priority
    lead_user_ids = lead.values_list('team_member__custom_id', flat=True) #flat = true returns list instead of tuples. 
    team_ids = team.values_list('team_member__custom_id', flat=True) #to differentiate lead and team members

    # Get all users in the workspace
    workspace_members = workspaceMember.objects.filter(workspace=current_ws)

    issues = issue.objects.filter(project_id=project_id, parent_task__isnull=True).annotate(
        subissue_count=Count('child')) #parent_task_isnull = true means top level issues, not sub issues. counts no.of sub issues.
    context = {'project': project, 'lead': lead, 'team': team, 'status': statuses,
               'priority': priorities, 'issues': issues, 'workspace_memb': workspace_members,
               'lead_user_ids': lead_user_ids, 'team_ids': team_ids, 'workspaces': ws, 'current_ws': current_ws,
               'flag': flag, 'ws_code': code, 'projects': projects, 'custom_id': custom_id, 'flag_edit': flag_edit}
            #    'flag': flag, 'ws_code': code, 'projects': projects, 'custom_id': custom_id}

    return render(request, 'users\project_view.html', context)


def edit_project(request, project_id, custom_id):
    print("edit_project view is triggered") 
    project = get_object_or_404(Project, project_id=project_id) #raises an error if project doesn't exist.

    current_ws = project.ws #getting the current workspace the project belongs to
    lead = project_member_bridge.objects.filter(project=project, role='Lead', active=True)
    team = project_member_bridge.objects.filter(project=project, active=True)  # Get all active team members

     # Check access control by passing the correct arguments: lead, custom_id, and current_ws
    flag_edit = access_control_admin(custom_id, current_ws)
    print(f"Custom ID: {custom_id}, Workspace ID: {current_ws}, Admin: {current_ws.admin.custom_id}")

    
    # Ensure only the workspace admin can edit
    if not flag_edit:
        messages.error(request, "You do not have permission to edit this project.")
        return redirect('project_view', project_id=project_id, custom_id=custom_id)
    
    if request.method == 'POST':
        print("POST request received")
        name = request.POST.get('name')
        desc = request.POST.get('description')
        prior_id = request.POST.get('priority')
        status_id = request.POST.get('status')
        deadline = request.POST.get('deadline').strip()
        lead_ids = request.POST.getlist('lead')
        team_ids = request.POST.getlist('team')

        print(f"Received name: {name}, description: {desc}, priority ID: {prior_id}, status ID: {status_id}, deadline: {deadline}")

# Update
        project.name = name
        project.description = desc
        print(f"Received name: {project.name}, description: {project.description}")


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
                print(f'Deadline updated to: {deadline_date}')
            except ValueError as ve:
                # Handle invalid date format
                messages.error(request, 'Invalid date format. Please use dd-mm-yyyy.')
                print(f'Error: {ve}')
                return redirect('edit_project', project_id=project_id, custom_id=custom_id)
        project.save()
        print(f'Updated project with deadline: {project.deadline}')


    # update lead
        project_member_bridge.objects.filter(project=project, role='Lead').update(
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
        project_member_bridge.objects.filter(project=project, role='Team member').update(
            active=False)  # Remove current team members
        for team_id in team_ids:
            team_memb = get_object_or_404(customUser, custom_id=team_id)
            if team_memb:
                team_instance, create = project_member_bridge.objects.get_or_create(
                    team_member=team_memb, project=project)
                # Update team member details
                team_instance.role = 'Team member'
                team_instance.active = True
                team_instance.save()

        messages.success(request, 'Project updated successfully!')
        return redirect('project_view', project_id=project_id, custom_id=custom_id)
        
    return render(request, 'users/project_view.html', {'project': project, 'custom_id': custom_id, 'flag_edit':flag_edit})


def edit_issue(request, issue_id, custom_id):
    print("edit issue is triggered")
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


def update_issue_field(request):
    print("update issue field is triggered")
    if request.method == "POST":
        issue_id = request.POST.get('issue_id')
        field_name = request.POST.get('field_name')
        value = request.POST.get('value')
        try:
            the_issue = issue.objects.get(issue_id=issue_id) #retrieving the issue.
        except issue.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Issue not found'}, status=404)

        if field_name == 'status': #if field name is status
            the_issue.status_id = value #updates sttaus of the issue
        elif field_name == 'priority':
            the_issue.priority_id = value
        elif field_name == 'assignee':
            try:
                the_assignee = customUser.objects.filter(custom_id__in=value)
                the_issue.assignee = the_assignee
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
    print("update project_field view is triggered")
    if request.method == "POST":
        project_id = request.POST.get('project_id')
        field_name = request.POST.get('field_name')
        value = request.POST.get('value')
        the_project = Project.objects.get(project_id=project_id)
        # Get the current workspace and check for admin access
        current_ws = the_project.ws
        print(f"Received project id: {project_id}, field name: {field_name}, priority : {the_project},  value: {value}")
        
        try:
            # Fetch the custom user instance
            custom_user = customUser.objects.get(user=request.user)  # Get the custom user instance associated with the logged-in user
            custom_id = custom_user.custom_id  # Now access the custom_id from the custom user instance
        except customUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User does not have a custom profile.'}, status=404)
            
        # Access control: Only the admin of the workspace can edit the project
        is_admin = access_control_admin(custom_id, current_ws)
        is_member = project_member_bridge.objects.filter(project=the_project,team_member=custom_user).exists()

        # Handle deadline updates
        if field_name == 'deadline':
            if not is_admin:
                return JsonResponse({'success': False, 'error': 'Only the workspace admin can change the deadline.'}, status=403)
            try:
                # Convert the deadline to a date object
                deadline_date = datetime.strptime(value, '%d-%m-%Y').date()
                the_project.deadline = deadline_date
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date format.'}, status=400)

        else:
            # For status or priority, check if the user is a project member
            if not is_member:
                return JsonResponse({'success': False, 'error': 'You do not have permission to update this project.'}, status=403)

            if field_name == 'status':
                # Check if the member has permission to update the status
                if not access_control_admin(custom_id, current_ws):
                    return JsonResponse({'success': False, 'error': 'You do not have permission to change the status.'}, status=403)
                the_project.status_id = value

            elif field_name == 'priority':
                # Only allow certain roles to change priority
                if not access_control_admin(custom_id, current_ws):
                    return JsonResponse({'success': False, 'error': 'You do not have permission to change the priority.'}, status=403)
                the_project.priority_id = value
            else:
                return JsonResponse({'success': False, 'error': 'Invalid field.'}, status=400)

        # Save the changes
        the_project.save()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)


# def update_project_field(request,project_id):
#     print("update project_field view is triggered") 
#     if request.method == "POST":
#         project_id = request.POST.get('project_id')
#         field_name = request.POST.get('field_name')
#         value = request.POST.get('value')
#         the_project = Project.objects.get(project_id=project_id)

#         # Get the current workspace and check for admin access
#         current_ws = the_project.ws  # Assuming the project has a foreign key to the workspace (ws)
#         # Fetch the custom user instance
#         try:
#             custom_user = customUser.objects.get(user=request.user)  # Get the custom user instance associated with the logged-in user
#             custom_id = custom_user.custom_id  # Now access the custom_id from the custom user instance
#         except customUser.DoesNotExist:
#             return JsonResponse({'success': False, 'error': 'User does not have a custom profile.'}, status=404)

#         # Access control: Only the admin of the workspace can edit the project
#         is_admin = access_control_admin(custom_id, current_ws)


#         # Update the appropriate field
#         if field_name == 'deadline':
#             # Only the workspace admin is allowed to change the deadline
#             if not is_admin:
#                 return JsonResponse({'success': False, 'error': 'Only the workspace admin can change the deadline.'}, status=403)
#             try:
#                 # Convert the deadline to a date object
#                 deadline_date = datetime.strptime(value, '%d-%m-%Y').date()
#                 the_project.deadline = deadline_date
#             except ValueError:
#                 return JsonResponse({'success': False, 'error': 'Invalid date format.'}, status=400)
#         else:
#             # For status or priority, check if the user has edit permissions (admin, lead, team member)
#             if not access_control(the_project.team, the_project.lead, custom_id, current_ws):
#                 return JsonResponse({'success': False, 'error': 'You do not have permission to update this project.'}, status=403)

#             if field_name == 'status':
#                 the_project.status_id = value
#             elif field_name == 'priority':
#                 # For updating priority, ensure the user has the necessary permissions
#                 if not access_control(the_project.team, the_project.lead, custom_id, current_ws):
#                     return JsonResponse({'success': False, 'error': 'You do not have permission to update the priority.'}, status=403)

#                 # Update the project priority
#                 try:
#                     # Assuming `value` is the ID of the priority object
#                     the_project.priority_id = value
#                 except Exception as e:
#                     return JsonResponse({'success': False, 'error': str(e)}, status=400)
#                 else:
#                     return JsonResponse({'success': False, 'error': 'Invalid field.'}, status=400)
        
#         # Save the changes
#         the_project.save()

#         return JsonResponse({'success': True})

#     return JsonResponse({'success': False}, status=400)


# #updating deadline from project_view
# def update_deadline(request):
#     print("update_deadline triggered")
#     if request.method == 'POST':
#         project_id = request.POST.get('project_id')
#         new_deadline = request.POST.get('new_deadline')

#         try:
#             project = Project.objects.get(id=project_id)
#             project.deadline = datetime.strptime(new_deadline, '%d-%m-%Y')
#             project.save()

#             return JsonResponse({'success': True})
#         except Project.DoesNotExist:
#             return JsonResponse({'error': 'Project not found'}, status=404)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)

#     return JsonResponse({'error': 'Invalid request'}, status=400)


#richtexteditor file uploading
@csrf_exempt  # Exempt from CSRF checks if handling via frontend directly
def file_upload_view(request):
    print("file upload vie / rich text editor is triggered")
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        # You can save the file to the filesystem or the database
        with open(f'media/uploads/{uploaded_file.name}', 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        return JsonResponse({'status': 'READY:' + uploaded_file.name})
    return JsonResponse({'error': 'Invalid file upload'}, status=400)


# updates status of the project by admin
@require_POST
def update_status(request, project_id):
    print("update status is triggered from form")
    project = get_object_or_404(Project, project_id=project_id)

    # Check if the user is the workspace admin
    current_ws_id = request.session.get('current_ws', None)
    if current_ws_id is not None:
        current_ws = get_object_or_404(workspace, ws_id=current_ws_id)  # Assuming you have a Workspace model
        if str(request.user.customUser.custom_id) != str(current_ws.admin.custom_id):
            return JsonResponse({'success': False, 'error': 'You do not have permission to edit the project status.'}, status=403)


    new_status_id = request.POST.get('status_id')
    if new_status_id:
        new_status = get_object_or_404(status, id=new_status_id)
        project.status = new_status
        project.save()
        return JsonResponse({'success': True, 'new_status': new_status.name})
    return JsonResponse({'success': False, 'error': 'invalid_status'})

#updates project status from project_view
def update_project_status(request, project_id):
    print("update_project_status trigerred")
    if request.method == 'POST':
        the_project = Project.objects.get(project_id=project_id)
        current_ws = the_project.ws
        custom_user = customUser.objects.get(user=request.user)  # Get the custom user instance associated with the logged-in user
        custom_id = custom_user.custom_id
        project = get_object_or_404(Project, project_id=project_id)
        if access_control_admin(custom_id,current_ws):  # Ensure only admin can change status
            new_status = request.POST.get('status')
            project.status = new_status  # Assuming status_id is the foreign key
            project.save()
            return JsonResponse({'success': True, 'new_status': new_status})  # Return a JSON response
    return JsonResponse({'success': False}, status=400)



def issue_view(request, issue_id, custom_id):
    print(" issue view is triggered")
    the_issue = issue.objects.select_related('project').prefetch_related(
        'project__project_member_bridge_set').get(issue_id=issue_id)
    # if we dont put project__ as prefix in prefetch related, project member bridge instances for issue objects are searched, which doesnt exist
    current_ws_id = request.session.get('current_ws', None)

    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    project_members = project_member_bridge.objects.filter(
        active=True, project=the_issue.project)
    assignees = issue_assignee_bridge.objects.filter(
        active=True, issue=the_issue)
    assignee_ids = assignees.values_list('assignee__custom_id', flat=True)

    subIssues = issue.objects.filter(parent_task=issue_id)
    statuses, priorities = get_priority_status_list()
    context = {'subIssues': subIssues, 'issue': the_issue, 'issue_id': issue_id,
               "custom_id": custom_id, 'priority': priorities, 'status': statuses, 'workspaces': ws, 'current_ws': current_ws,
               'flag': flag, 'ws_code': code, 'projects': projects, 'project_members': project_members, 'assignee_id': assignee_ids, 'assignees': assignees}
    return render(request, 'users\issue_view.html', context)


def add_issue(request, custom_id, project_id):
    print("add issue is triggered")
    team_members = project_member_bridge.objects.filter(
        project=project_id, active=True)
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page

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

    context = {'workspaces': ws, 'current_ws': current_ws, 'project_id': project_id,
               'flag': flag, 'ws_code': code, 'projects': projects, 'custom_id': custom_id, 'team_members': team_members}
    return render(request, 'users/add_issue.html', context)


def add_subIssue(request, issue_id, custom_id):
    print("add sub issue  is triggered")
    subIssue = issue.objects.get(issue_id=issue_id)
    team_members = project_member_bridge.objects.filter(
        project=subIssue.project, active=True)
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenever navbar is needed in a page

    if request.method == "POST":
        title = request.POST.get('title')
        desc = request.POST.get('desc')
        prior = request.POST.get('priority')
        stat = request.POST.get('status')
        deadline = request.POST.get('deadline').strip()
        assignees = request.POST.getlist('assignees')
        issue_instance = issue(name=title, description=desc, project=Project.objects.get(
            project_id=subIssue.project.project_id), parent_task=issue.objects.get(issue_id=issue_id))
        print('deadline', deadline)
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
    context = {'workspaces': ws, 'current_ws': current_ws, 'issue_id': issue_id,
               'flag': flag, 'ws_code': code, 'projects': projects, 'custom_id': custom_id, 'team_members': team_members}
    return render(request, 'users/add_subissue.html', context)


def get_issueComments(request, issue_id):

    comments = Comments.objects.filter(
        issue_id=issue_id, parent_comment__isnull=True).select_related('author', 'issue')
    if not comments.exists():

        return JsonResponse({'comments': [], 'message': 'No comments available.'})

    comment_data = []
    for comment in comments:
        replies = comment.replies.select_related('author').all()
        replies_data = []
        for reply in replies:
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
    return JsonResponse({'comments': comment_data})


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
            return JsonResponse({'success': True, 'comment': {
                    'id': comment.id,
                    'author': comment.author.user.first_name + comment.author.user.last_name ,  
                    'text': comment.comment,
                    'created_at': comment.created_at.strftime('%d-%m-%Y %H:%M')
                }})
        except issue.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Issue not found'})
    return JsonResponse({'success': False, 'error': ' Invalid request method'})

def submit_replies(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        reply_text = data.get('reply')
        issue_id = data.get('issueId')
        comment_id = data.get('comment_id')  
        print(issue_id)
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

def dashboard(request):
    return render (request,'dashboard\Dashboard.html')

