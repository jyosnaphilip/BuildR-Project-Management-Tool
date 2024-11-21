import os
import django
from django.core.management.base import BaseCommand
os.environ.setdefault('DJANGO_SETTINGS_MODULE','buildr.settings')
django.setup()

from faker import Faker
from users.models import customUser, workspace, workspaceMember, Project, project_member_bridge, issue, issue_assignee_bridge, Comments,priority,status
from django.contrib.auth.models import User
import random

fake = Faker()

ws = workspace.objects.filter(active=True)[3]
project = Project.objects.filter(ws=ws)[0]

def create_dummy_data(num_users=10,num_issues=5,num_comments=50):
    users = customUser.objects.all()
    ws_members=[]
    # for _ in range(num_users):
    #     user = User.objects.create_user(username=fake.user_name(), email=fake.email(), password='123')
    #     custom_user = customUser.objects.create(
    #         user=user,
    #         profile_pic=None,
    #         gameMode=random.choice([True, False])
    #     )
    #     users.append(custom_user)
    #     ws_member = workspaceMember.objects.create(workspace=ws, customUser=custom_user)
    #     ws_members.append(ws_member)
    #     proj_member=project_member_bridge.objects.create(
    #                 team_member=custom_user,
    #                 project=project,
    #                 role=random.choice(['Lead', 'Team member'])
    #             )
    
    issues = []

    for _ in range(num_issues):
        issue_obj = issue.objects.create(
            name=fake.catch_phrase(),description=fake.text(),
            deadline=fake.date_this_year(),project=project,priority=random.choice(priority.objects.all()),
                status=random.choice(status.objects.all()))
        issues.append(issue_obj)

    
    for user in random.sample(users, 2):
                issue_assignee_bridge.objects.create(
                    assignee=user,
                    issue=issue_obj
                )
    comments={}
    for issue_obj in issues:
        comments[issue_obj]=[]
        for _ in range(3):
            author = random.choice(users)
            comment=Comments.objects.create(
                comment=fake.sentence(),
                author=author,
                issue=issue_obj
            )
            comments[issue_obj].append(comment)

    for issue_obj in issues:
        for _ in range(3):
            author = random.choice(users)
            Comments.objects.create(
                comment=fake.sentence(),
                author=author,
                issue=issue_obj
            )
        for _ in  range(2):
            author = random.choice(users)
            Comments.objects.create(
                comment=fake.sentence(),
                author=author,
                issue=issue_obj,
                parent_comment=random.choice(comments[issue_obj])
            )
        
if __name__ == "__main__":
    create_dummy_data()