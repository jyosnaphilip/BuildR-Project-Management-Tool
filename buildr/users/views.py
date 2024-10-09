from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login,logout
from .models import customUser, workspace, workspaceMember, workspaceCode, Project, priority, status, project_member_bridge, issue, issue_assignee_bridge, Comments
from django.utils import timezone
import json
from datetime import datetime
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.core.mail import send_mail
import random
from .models import EmailVerification
from datetime import timedelta,date
from django.utils.dateformat import format
from highcharts_gantt.chart import Chart
from highcharts_gantt.global_options.shared_options import SharedOptions
from highcharts_gantt.options import HighchartsGanttOptions
from highcharts_gantt.options.plot_options.gantt import GanttOptions
from highcharts_gantt.options.series.gantt import GanttSeries
from users.tasks import get_sentiment_task

# shared_options = SharedOptions.from_js_literal('buildr\\static\\scripts\\highcharts_config\\shared_options.js')
# js_shared_options = shared_options.to_js_literal()
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
# Create your views here.


def get_projects(ws_id):
    """ retrieves all projects of a workspace """
    projects = Project.objects.filter(ws=ws_id.ws_id).distinct()
    return projects


def req_for_navbar(custom_id, current_ws_id):
    """ retrieves all things necessary for rendering of sidebar """
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


def logout_user(request):
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

# ws-related
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
                messages.error(request, message="Invalid Code!")
                return redirect('join-workspace', custom_id )
        else:
            messages.error(request,message="Invalid Code!")
            return redirect('join-workspace', custom_id)
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

            return render(request, 'users/home.html', {'custom_id': custom_id, "ws_id": ws, 'code': code})
        else:
            messages.error(request, 'Workspace name already exists!')
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
        if deadline != None and deadline!="":
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

# project-issues
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
        subissue_count=Count('child'), unread_comments_count=Count('comments', filter=~Q(comments__read_by=customUser.objects.get(user=request.user)))).order_by('priority__id')
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
            
            previous_stat=the_issue.status_id
            the_issue.status_id = int(value) 
            if previous_stat!=4 and int(value)==4:
                the_issue.mark_completed()
                
                
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


def update_project_field(request):
    if request.method == "POST":
        project_id = request.POST.get('project_id')
        field_name = request.POST.get('field_name')
        value = request.POST.get('value')

        the_project = Project.objects.get(project_id=project_id)

        # Update the appropriate field
        if field_name == 'status':
            previous_stat=the_project.status_id
            the_project.status_id = value
            if value==4 and previous_stat!=4:
                the_project.mark_completed()
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

    subIssues = issue.objects.filter(parent_task=issue_id).order_by('priority__id')
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

# comments
def get_issueComments(request, issue_id):

    comments = Comments.objects.filter(
        issue_id=issue_id, parent_comment__isnull=True).select_related('author', 'issue')
    if not comments.exists():

        return JsonResponse({'comments': [], 'message': 'No comments available.'})
    custom_id = customUser.objects.get(user=request.user.id).custom_id
    comment_data = []
    
    for comment in comments:
        comment_is_read=custom_id in comment.read_by.all()
        
        comment.read_by.add(custom_id)
        replies = comment.replies.select_related('author').all()
        replies_data = []
        for reply in replies:
            reply_is_read=custom_id in reply.read_by.all()
            if not reply_is_read:
                reply.read_by.add(custom_id)
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
    """ returns project wise active issues """
    active_issues_per_project = (
        issue.objects
        .filter(project__ws__ws_id = current_ws_id)
        .exclude(status=4)  # Filter active issues
        .values('project')  # Group by project
        .annotate(active_count=Count('issue_id'))  # Count the active issues
    )

    return active_issues_per_project

def get_active_issue_count(active_issues_per_project):
    """ returns total active number of active issues in the current ws"""
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

def load_project_lead_insights(custom_id,current_ws_id):
    pass
def check_overdue(project_id):
    """ count number of tasks which are over due, retriev them and show as list when clicked with assignee"""
    project = Project.objects.get(project_id=project_id)
    overdue_issues = issue.objects.filter(project=project,deadline__lt=timezone.now(), completed=False)
    overdue = []
    for task in overdue_issues:
        assignees = task.assignee.all()
        overdue_by=(timezone.now().date()-task.deadline).days
        overdue.append({
            'task': task.name,
            'assignees': [user.user.username for user in assignees],
            'overdue by':overdue_by
        })
    return overdue
    

def task_completion_status(project_id):
    """ drilldown : priority """
    project = Project.objects.get(project_id=project_id)
    task_status = issue.objects.filter(project=project).values('priority__name').annotate(
    total_issues=Count('issue_id'),
    completed_issues=Count('issue_id', filter=Q(completed=True)),
    in_progress_issues=Count('issue_id', filter=Q(completed=False))
    )
    print(task_status)
    return task_status

def issues_per_team_member(project_id):
    """ drilldown by priority """
    project = Project.objects.get(project_id=project_id)
    team_issues = issue_assignee_bridge.objects.filter(issue__project=project).values(
        'assignee__user__username', 'issue__priority__name'
    ).annotate(
        total_issues=Count('issue')
    )
    
    return team_issues

def show_top_critical_issue(project_id):
    """ urgent and high-priority issues that are unresolved, and showing the time they have remained open."""
    project = Project.objects.get(project_id=project_id)
    critical_issues = issue.objects.filter(
        project=project,
        priority__name__in=['Urgent', 'High Priority'],
        completed=False
    ).order_by('created_on')
    
    results = []
    for task in critical_issues:
        open_duration = (timezone.now() - task.created_on).days  # Days since the task was created
        results.append({
            'task': task.name,
            'priority': task.priority.name,
            'open_for_days': open_duration
        })
    
    return results


def tasks_completed_last_week(project_id):
    """ breakdown by team member """
    project = Project.objects.get(project_id=project_id)
    one_week_ago = timezone.now() - timedelta(days=7)
    completed_issues = issue.objects.filter(project=project, completed=True, completed_date__gte=one_week_ago)
    
    team_completed = completed_issues.values('assignee__user__username').annotate(
        total_completed=Count('issue_id')
    )
    
    return team_completed

def count_tasks_completed_last_week(project_id):
    project = Project.objects.get(project_id=project_id)
    one_week_ago = timezone.now() - timedelta(days=7)
    return issue.objects.filter(project=project, completed=True, completed_date__gte=one_week_ago).count()
 

def active_issues(project_id):
    project = Project.objects.get(project_id=project_id)
    return issue.objects.filter(project=project, completed=False).count()

def tasks_closed_per_week(project_id):
    pass
def team_sentiment_analysis():
    pass



def get_project_insights(request, project_id):
    current_ws_id = request.session.get('current_ws', None)
    custom_id = customUser.objects.get(user=request.user.id).custom_id
    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)
    context = {'custom_id':custom_id,'workspaces': ws, 'current_ws': current_ws,
                'flag': flag, 'ws_code': code, 'projects': projects}
    return render(request, 'dashboard\project_wise_dashboard.html', context)


# dashboard
def dashboard(request,custom_id):
    """ sends user to dashboard based on their role """
    current_ws_id = request.session.get('current_ws', None)

    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)
    
    # for all users 
    # treemap of priority
    treemap_data, priority_count = treemap_of_priority(custom_id,current_ws_id)
    # pie chart
    pie_data, status_count = status_pie(custom_id,current_ws_id)
    gantt = gantt_data(projects)
    scatter = scatter_plot_with_time(custom_id, current_ws_id)
    context = {'custom_id':custom_id,'workspaces': ws, 'current_ws': current_ws,
                'flag': flag, 'ws_code': code, 'projects': projects, 'treemap_data':treemap_data,
                    'priority_count':priority_count, 'pie_data':pie_data,
                    'status_count': status_count, 'gantt':gantt, 'scatter':scatter}
   
 
    is_project_lead = check_if_project_lead(custom_id,current_ws_id)
       #  Additional data for workspace admins
    if flag:
       
        admin_specific_data = load_admin_specific_insights(custom_id,current_ws_id)
        if admin_specific_data is not None:
            context.update(admin_specific_data)
        if is_project_lead: # check if user is ws admin AND a project lead
            context.update({'is_project_lead':True})
            projects_lead = get_projects_lead(custom_id,current_ws_id)
            # print(projects_lead)
            # if projects_lead is not None:
            #     for project in projects_lead:
                    # project_insights = get_projects_lead_data(project, current_ws_id)
                    # if project_insights is not None:
                    #     context.update(project_insights)
            context.update({'projects_lead':projects_lead})
            
        return render(request,'dashboard\ws_admin_dashboard.html',context)

    
    elif is_project_lead: # users who are not ws admin but is project lead
        context.update({'is_project_lead':True})
        projects_lead = get_projects_lead(custom_id,current_ws_id)
        # for project in projects_lead:
        #     project_insights = get_projects_lead_data(project)
        #     if project_insights is not None:
        #             context.update(project_insights)
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

    ws, current_ws, projects, flag, code = req_for_navbar(
        custom_id, current_ws_id)
    custom_user = customUser.objects.get(custom_id=custom_id)
    context = {"custom_id": custom_id, 'workspaces': ws, 'current_ws': current_ws,
               'flag': flag, 'ws_code': code, 'projects': projects, 'custom_user':custom_user}
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



def toggle_ws_member_status(request, custom_id, ws_id):

    """Toggle the active state of a workspace member."""
    try:
        ws_member = workspaceMember.objects.get(workspace=ws_id, customUser=custom_id)
        ws_member.active = not ws_member.active  # Toggle the active state
        ws_member.save()
        return JsonResponse({'status': 'success', 'active': ws_member.active})
    except workspaceMember.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Member not found'}, status=404)
    
def create_new_code(request,custom_id,ws_id):
    new_code = create_code(ws_id)
    return JsonResponse({'new_code': new_code}) 