# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from transformers import pipeline
# from .models import Comments,issue,project_member_bridge
# from users.tasks import get_sentiment_task

# @receiver(post_save, sender=Comments)
# def sentiment_analysis_on_save(sender, instance, created, **kwargs):
#     if created: # check if comments were actually created
#         print("here 0")
#         get_sentiment_task.delay(instance.id)   # call celery tasks async
#         comment = Comments.objects.get(id=instance.id)

#         pipe = pipeline("text-classification", model="finiteautomata/bertweet-base-sentiment-analysis")  # output labels: POS, NEG, NEU

#     # Save sentiment score back to the database
#         result = pipe(comment.comment)
#         label = result[0]['label'] 
#         print(f"Sentiment analysis result: {label}")
#         if label == 'NEG':
#             comment.sentiment_score = -1
#             # notify fn
#         elif label == 'NEU':
#             comment.sentiment_score = 0
#         else:
#             comment.sentiment_score = 1

    
#         comment.save()
    
    
#         issue_id = comment.issue.issue_id
    
    

# def recalculate_issue_sentiment_task(issue_id):
#     """ Recalculates over sentiment for an issue, after new comment is added"""
#     issue_ = issue.objects.get(issue_id = issue_id)
#     comments = Comments.objects.filter(issue = issue_)

#     if comments is not None:
#         sentiment_scores = []
#         for comment in comments:
#             if comment.sentiment_score is not None:
#                 sentiment_scores.append(comment.sentiment_score)
#         if not sentiment_scores:
#             return  # no sentiments
        
#         avg_sentiment = sum(sentiment_scores)/len(sentiment_scores)
#         previous_sentiment_score = issue_.overall_sentiment_score
#         issue_.overall_sentiment_score = avg_sentiment
#         issue_.save()
#         if avg_sentiment < 0:
#             if previous_sentiment_score is None or previous_sentiment_score >= 0:
#                 pass

           
        
        


# def notify_user_of_neg_sentiment_task(issue_id):
#     issue_ = issue.objects.get(issue_id=issue_id)
#     project = issue_.project
#     leads = project_member_bridge.objects.filter(project=project.project_id,active=True,role='Lead')
    
#     if leads is not None:
#         emails = []

#         for lead in leads:
#             pass
    
#     # TO DO: code for sending in app notifications

