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
from django.core.mail import send_mail
import random
from .models import EmailVerification


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
# Create your views here.


def get_projects(ws_id):
    projects = Project.objects.filter(ws=ws_id.ws_id).distinct()
    return projects


def req_for_navbar(custom_id, current_ws_id):
    ws = get_ws(custom_id, current_ws_id)  # all ws #nav
    current_ws = workspace.objects.get(ws_id=current_ws_id)
    projects = get_projects(current_ws)  # nav
    if str(current_ws.admin.custom_id) == custom_id:  # nav
        flag = True
        ws_code = workspaceCode.objects.filter(
            ws=current_ws_id, is_active=True).values('code', 'ws_id')
        if len(ws_code) == 0:
            code = create_code(current_ws_id)
        else:
            code = check_code(ws_code)

    else:
        flag = False
        code = None
    return ws, current_ws, projects, flag, code


def home(request, custom_id):
    current_ws_id = request.session.get('current_ws', None)  # nav
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    user_issues = issue.objects.filter(
        project__ws__ws_id=current_ws_id, issue_assignee_bridge__assignee=custom_id)
    return render(request, 'users\home.html', {'custom_id': custom_id, 'workspaces': ws, 'current_ws': current_ws, 'flag': flag, 'ws_code': code, 'projects': projects, 'user_issues': user_issues})


def change_ws(request):
    if request.method == 'POST' and request.user.is_authenticated:
        data = json.loads(request.body)
        ws_id = data.get('ws_id')
        custom_user = customUser.objects.get(user=request.user)
        if workspaceMember.objects.filter(customUser=custom_user, workspace__ws_id=ws_id).exists():
            request.session['current_ws'] = ws_id
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
                user.set_password(password1)
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


def get_ws(user_id, ws_id=None):
    if ws_id:
        ws_lst = workspaceMember.objects.filter(customUser=user_id).exclude(
            workspace__ws_id=ws_id).values('workspace__ws_id', 'workspace__ws_name')
        # for a user with only one workspace we end up removing that from ws_lst in above line
        # to mitigate that, im putting this if condn
        if len(ws_lst) == 0:
            ws_lst = workspaceMember.objects.filter(customUser=user_id).values(
                'workspace__ws_id', 'workspace__ws_name')
    else:
        ws_lst = workspaceMember.objects.filter(customUser=user_id).values(
            'workspace__ws_id', 'workspace__ws_name')

    return ws_lst


def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            custom_user = customUser.objects.get(user=user)
            customUser_id = custom_user.custom_id
            if custom_user.last_ws:
                request.session['current_ws'] = str(custom_user.last_ws.ws_id)
            else:
                first_workspace = workspaceMember.objects.filter(
                    customUser=custom_user).first()
                if first_workspace:
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


def logout(request):
    if request.user.is_authenticated:
        custom_user = customUser.objects.get(user=request.user)
        current_ws = request.session.get('current_ws')
        if current_ws:
            custom_user.last_workspace = workspace.objects.get(
                ws_id=current_ws)
            custom_user.save()
    logout(request)
    return redirect('login')
# auth end------------------------


def join_workspace(request, custom_id):
    if request.method == "POST":
        code = request.POST.get('ws-code')
        if workspaceCode.objects.filter(code=code, is_active=True).exists():
            ws_code = workspaceCode.objects.filter(
                code=code, is_active=True).values('code', 'ws_id')

            actual_code = check_code(ws_code)

            if (code == actual_code):

                ws_member = workspaceMember(workspace=workspace.objects.get(
                    ws_id=ws_code[0]['ws_id']), customUser=customUser.objects.get(custom_id=custom_id))
                ws_member.save()

                request.session['current_ws'] = str(ws_code[0]['ws_id'])

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

        name_check = check_ws(ws_name)

        if (not name_check):
            ws = workspace(ws_name=ws_name,
                           admin=customUser.objects.get(custom_id=custom_id))
            ws.save()

            ws_member = workspaceMember(workspace=workspace.objects.get(
                ws_id=ws.ws_id), customUser=customUser.objects.get(custom_id=custom_id))
            ws_member.save()
            code = workspaceCode.objects.filter(
                ws=ws).order_by('-created_on').first()

            if not code or code.has_expired():
                if code:
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
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page
    ws_members = workspaceMember.objects.filter(
        workspace=current_ws, active=True)
    if request.method == "POST":
        project_name = request.POST.get('project_name')
        desc = request.POST.get('desc')
        prior = request.POST.get('priority')
        stat = request.POST.get('status')
        deadline = request.POST.get('deadline')

        lead = request.POST.getlist('lead')
        members = request.POST.getlist('members')

        project = Project(name=project_name, description=desc, ws=current_ws)
        if deadline != None:
            deadline = datetime.strptime(deadline, '%d-%m-%Y').date()
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


def access_control(lead, custom_id, current_ws):
    # access control for editing things
    flag_edit = False
    for _ in lead:
        if str(custom_id) == str(_.team_member.custom_id) or str(custom_id) == str(current_ws.admin.custom_id):
            flag_edit = True
            break
    return flag_edit


def project_view(request, project_id, custom_id):
    # stuff for navbar
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page

    project = Project.objects.get(project_id=project_id)
    team = project_member_bridge.objects.filter(
        project_id=project_id, role="Team member", active=True)
    lead = project_member_bridge.objects.filter(
        project_id=project_id, role="Lead", active=True)
    # access control for editing project
    flag_edit = access_control(lead, custom_id, current_ws)

    statuses, priorities = get_priority_status_list()
    lead_user_ids = lead.values_list('team_member__custom_id', flat=True)
    team_ids = team.values_list('team_member__custom_id', flat=True)
    # Get all users in the workspace
    workspace_members = workspaceMember.objects.filter(workspace=current_ws)

    issues = issue.objects.filter(project_id=project_id, parent_task__isnull=True).annotate(
        subissue_count=Count('child'))
    context = {'project': project, 'lead': lead, 'team': team, 'status': statuses,
               'priority': priorities, 'issues': issues, 'workspace_memb': workspace_members,
               'lead_user_ids': lead_user_ids, 'team_ids': team_ids, 'workspaces': ws, 'current_ws': current_ws,
               'flag': flag, 'ws_code': code, 'projects': projects, 'custom_id': custom_id, 'flag_edit': flag_edit}

    return render(request, 'users\project_view.html', context)


def edit_project(request, project_id, custom_id):
    project = get_object_or_404(Project, project_id=project_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc')
        prior_id = request.POST.get('priority')
        status_id = request.POST.get('status')
        deadline = request.POST.get('deadline').strip()
        lead_ids = request.POST.getlist('lead')
        team_ids = request.POST.getlist('team')
# Update
        project.name = name
        project.desc = desc
        if prior_id != None:
            project.priority = get_object_or_404(priority, id=prior_id)
        if status_id != None:
            project.status = get_object_or_404(status, id=status_id)
        if deadline != None and deadline != "":
            deadline = datetime.strptime(deadline, '%d-%m-%Y').date()
            project.deadline = deadline
        project.save()

    # update lead
        project_member_bridge.objects.filter(project=project, role='Lead').update(
            active=False)  # Remove current leads
        for lead_id in lead_ids:
            lead = get_object_or_404(customUser, custom_id=lead_id)
            if lead != None:
                lead, created = project_member_bridge.objects.get_or_create(
                    team_member=customUser.objects.get(custom_id=lead_id), project=project)
                # get or create returns a tuple with object and creation status
                lead.role = 'Lead'
                lead.active = True
                lead.save()
        # Update team members
        project_member_bridge.objects.filter(project=project, role='Team member').update(
            active=False)  # Remove current team members
        for team_id in team_ids:
            team_memb = get_object_or_404(customUser, custom_id=team_id)
            if team_memb != None:
                team_, create = project_member_bridge.objects.get_or_create(
                    team_member=team_memb, project=project)
                team_.role = 'Team member'
                team_.active = True
                team_.save()
        messages.success(request, 'Project updated successfully!')
        return redirect('project_view', project_id, custom_id)


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


def update_issue_field(request):
    if request.method == "POST":
        issue_id = request.POST.get('issue_id')
        field_name = request.POST.get('field_name')
        value = request.POST.get('value')
        try:
            the_issue = issue.objects.get(issue_id=issue_id)
        except issue.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Issue not found'}, status=404)

        if field_name == 'status':
            the_issue.status_id = value
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


def update_project_field(request):
    if request.method == "POST":
        project_id = request.POST.get('project_id')
        field_name = request.POST.get('field_name')
        value = request.POST.get('value')

        the_project = Project.objects.get(project_id=project_id)

        # Update the appropriate field
        if field_name == 'status':
            the_project.status_id = value
        elif field_name == 'priority':
            the_project.priority_id = value
        else:
            pass

        # Save the issue
        the_project.save()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@require_POST
def update_status(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    new_status_id = request.POST.get('status_id')
    if new_status_id:
        new_status = get_object_or_404(status, id=new_status_id)
        project.status = new_status
        project.save()
        return JsonResponse({'success': True, 'new_status': new_status.name})
    return JsonResponse({'success': False, 'error': 'invalid_status'})


def issue_view(request, issue_id, custom_id):
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
    subIssue = issue.objects.get(issue_id=issue_id)
    team_members = project_member_bridge.objects.filter(
        project=subIssue.project, active=True)
    current_ws_id = request.session.get('current_ws', None)
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)  # use whenevr navbar is needed in a page

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