from transformers import pipeline
from celery import shared_task, chain
from users.models import Comments, issue, project_member_bridge, customUser
import logging
from django.core.mail import send_mail
from buildr import settings
from django.urls import reverse
logger = logging.getLogger(__name__)


@shared_task(bind=True) # THIS BIND AUTOMATICALY ADDS A SELF ARGUMENT IN THE BEGINNING !!!
def get_sentiment_task(self, comment_id): # DO NOT, I REPEAT, DO NOT REMOVE THE SELF PARAMETER!!!
    """ Get sentiment score for new comment"""
    
    comment = Comments.objects.get(id=comment_id)
    print("before pipe")
    pipe = pipeline("text-classification", model="finiteautomata/bertweet-base-sentiment-analysis")  # output labels: POS, NEG, NEU
    print("adter pipe")

    # Save sentiment score back to the database
    result = pipe(comment.comment)
    print("adter result")
    label = result[0]['label'] 
    if label == 'NEG':
        comment.sentiment_score = -1
    elif label == 'NEU':
        comment.sentiment_score = 0
    else:
        comment.sentiment_score = 1
    print("adter assign")
    
    comment.save()
    
    issue_id = comment.issue.issue_id
    chain(
                recalculate_issue_sentiment_task.s(issue_id)
            ).apply_async()      


@shared_task
def recalculate_issue_sentiment_task(issue_id):
    """ Recalculates over sentiment for an issue, after new comment is added"""
    issue_ = issue.objects.get(issue_id = issue_id)
    comments = Comments.objects.filter(issue = issue_)

    if comments is not None:
        sentiment_scores = []
        for comment in comments:
            if comment.sentiment_score is not None:
                sentiment_scores.append(comment.sentiment_score)
        if not sentiment_scores:
            return  None # no sentiments
        
        avg_sentiment = sum(sentiment_scores)/len(sentiment_scores)
        previous_sentiment_score = issue_.overall_sentiment_score
        issue_.overall_sentiment_score = avg_sentiment
        issue_.save()
        # if avg_sentiment < 0:
        #     if previous_sentiment_score is None or previous_sentiment_score >= 0:
        #         notify_user_of_neg_sentiment_task.s(issue_id).apply_async()
    
        return None
        
        

@shared_task
def notify_user_of_neg_sentiment_task(self,issue_id):
    issue_ = issue.objects.get(issue_id=issue_id)
    project = issue_.project
    leads = project_member_bridge.objects.filter(project=project.project_id,active=True,role='Lead')
    
    if leads is not None:
        emails = []

        for lead in leads:
            pass
    
    # TO DO: code for sending in app notifications
    return None

@shared_task(bind=True)
def send_email_task(self,emails, workspace_name, workspace_code):
    # logic for sending emails
    join_workspace_url = f"{settings.BASE_URL}{reverse('join-workspace')}?code={workspace_code}"
    
    for email in emails:
        mail_subject = f"You are invited to workspace {workspace_name}"
        message = (
            f"You are invited to join the workspace '{workspace_name}'.\n If you already have an account with us, click the link below to join."
            f"Click on the link below to join:\n\n{join_workspace_url}"
            f"If the above link doesnt work, please copy the workspace code and join the workspace manually. \nWorkspace code: {workspace_code}"
        )
        send_mail(
            subject=mail_subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
    print("Celery is working!")