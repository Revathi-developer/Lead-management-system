import datetime
from django.core.management.base import BaseCommand
from website.models import UserActivity  # Replace 'your_app' with your app name

class Command(BaseCommand):
    help = "Deletes user activities older than one month."

    def handle(self, *args, **kwargs):
        # Calculate the date one month ago
        one_month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        old_activities = UserActivity.objects.filter(timestamp__lt=one_month_ago)
        
        # Get the count and delete them
        count = old_activities.count()
        old_activities.delete()
        
        # Output the result
        self.stdout.write(f"Deleted {count} user activities older than one month.")
