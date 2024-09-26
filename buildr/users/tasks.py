from transformers import pipeline
from celery import shared_task, chain
from users.models import Comments, issue, project_member_bridge, customUser
import logging
logger = logging.getLogger(__name__)


@shared_task(bind=True)
def get_sentiment_task(comment_id):
    """ Get sentiment score for new comment"""
    logger.info("here1")
    comment = Comments.objects.get(id=comment_id)

    pipe = pipeline("text-classification", model="finiteautomata/bertweet-base-sentiment-analysis")  # output labels: POS, NEG, NEU

    # Save sentiment score back to the database
    result = pipe(comment.comment)
    label = result[0]['label'] 
    print(f"Sentiment analysis result: {label}")
    if label == 'NEG':
        comment.sentiment_score = -1
    elif label == 'NEU':
        comment.sentiment_score = 0
    else:
        comment.sentiment_score = 1

    
    comment.save()
    
    print(f"Saved sentiment score: {comment.sentiment_score}")
    # issue_id = comment.issue.issue_id
    # chain(
    #         recalculate_issue_sentiment_task.s(issue_id),
    #         notify_user_of_neg_sentiment_task.s(issue_id)
    #     ).apply_async()      
    

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
            return  # no sentiments
        
        avg_sentiment = sum(sentiment_scores)/len(sentiment_scores)
        previous_sentiment_score = issue_.overall_sentiment_score
        issue_.overall_sentiment_score = avg_sentiment
        issue_.save()
        if avg_sentiment < 0:
            if previous_sentiment_score is None or previous_sentiment_score >= 0:
                notify_user_of_neg_sentiment_task.delay_on_commit(issue_id, debug = True)

           
        
        

@shared_task
def notify_user_of_neg_sentiment_task(issue_id):
    issue_ = issue.objects.get(issue_id=issue_id)
    project = issue_.project
    leads = project_member_bridge.objects.filter(project=project.project_id,active=True,role='Lead')
    
    if leads is not None:
        emails = []

        for lead in leads:
            pass
    
    # TO DO: code for sending in app notifications

@shared_task
def test_task():
    print("Celery is working!")