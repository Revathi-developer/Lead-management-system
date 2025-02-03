from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError 
from django.contrib.auth.models import User
from django.utils.timezone import now
import re
from django.db import transaction


class UserActivity(models.Model):

    ACTION_CHOICES = [
        ('ADD', 'Added'),
        ('EDIT', 'Edited'),
        ('DELETE', 'Deleted'),
    ]

    # User activity is linked to a user (nullable)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Path where the action occurred
    path = models.CharField(max_length=250)

    # Action performed, constrained to choices
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)

    # Timestamp of when the activity occurred
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.path}"

    class Meta:
        db_table = 'user_activity'



def validate_phone_number(value):
    if not value.isdigit() or len(value) != 10:
        raise ValidationError("Phone number must be 10 digits long.")

class Course(models.Model):  # Moved Course above Lead
    COURSES_CHOICES = [
        ('Human Resources', 'Human Resources'),
        ('Data Analyst', 'Data Analyst'),
        ('Digital Marketing', 'Digital Marketing'),
        ('UI Development', 'UI Development'),
        ('Full stack Python', 'Full stack Python'),
        ('UI/UX Designing', 'UI/UX Designing'),
        ('Full stack Java', 'Full stack Java'),
        ('AWS DevOps', 'AWS DevOps'),
        ('Gen AI', 'Gen AI'),
        # Add other courses here
    ]
    course_name = models.CharField(max_length=255, unique=True, choices=COURSES_CHOICES)

    def __str__(self):
        return self.course_name

    class Meta:
        ordering = ['course_name']  # Ascending order



class Lead(models.Model):
    SOURCE_CHOICES = [
        ('LinkedIn', 'LinkedIn'),
        ('Facebook', 'Facebook'),
        ('Instagram', 'Instagram'),
        ('JustDial', 'JustDial'),
        ('Webenquiry', 'Webenquiry'),
        ('GoogleAds', 'GoogleAds'),
        ('BNI leads', 'BNI leads'),
        # Add other sources here
    ]

    STATUS_CHOICES = [
        ('Strong', 'Strong'),
        ('Follow up', 'Follow up'),
        ('Interested', 'Interested'),
        ('Not Interested', 'Not Interested'),
        ('Wrong Number', 'Wrong Number'),
        ('Joined', 'Joined'),
        ('New', 'New'),
    ]
    
    lead_name = models.CharField(max_length=100)  # Unique lead name
    email = models.EmailField()
    phone = models.CharField(max_length=15,  validators=[RegexValidator(r'^\+91\d{10}$', 'Phone number must be in the format +91XXXXXXXXXX')])
    location = models.CharField(max_length=100)
    status = models.CharField(max_length=40, default='New', choices=STATUS_CHOICES, blank=True, null=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, blank=True, null=True)
    lead_number = models.IntegerField(blank=True, null=True)
      # New field to track join date
    
    created_at = models.DateTimeField(auto_now_add=True)
    date_joined = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if self.lead_number is None:  # If lead_number is not provided (i.e., None)
            last_lead = Lead.objects.all().order_by('lead_number').last()
            self.lead_number = last_lead.lead_number + 1 if last_lead else 1  # Increment lead_number
        super(Lead, self).save(*args, **kwargs)


    

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')

    # Remove spaces and dashes from the phone number
        phone = phone.replace(" ", "").replace("-", "")

    # If the phone starts with +91, leave it as is (for editing)
        if phone.startswith('+91'):
            phone = phone[3:]  # Remove the +91 to validate the digits

    # Check if the phone number contains only digits
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

    # Ensure the phone number has exactly 10 digits
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

    # Add +91 to the phone number before returning it
        phone = "+91" + phone

        return phone


    def __str__(self):
        return self.lead_name  # Return lead name for better readability

    class Meta:
        ordering = ['lead_number']  # Ascending order





class Trainer(models.Model):

    ONLINE_OFFLINE_CHOICES=[
        ('online', 'online'),
        ('offline', 'offline')
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    # Add missing fields
    bio = models.TextField()  # Bio field
    expertise = models.CharField(max_length=200)  # Expertise field
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=50, choices=ONLINE_OFFLINE_CHOICES, default='online')
    date_of_joining = models.DateField(default=timezone.now) 
    trainer_number = models.IntegerField(unique=True, blank=True ,null=True)
    courses_opted=models.ManyToManyField(Course, blank=True)
    
    


    def save(self, *args, **kwargs):
        if not self.trainer_number:  # If no trainer_number is set, assign one
            last_trainer = Trainer.objects.last()
            if last_trainer and last_trainer.trainer_number is not None:
                self.trainer_number = last_trainer.trainer_number + 1
            else:
                self.trainer_number = 1  # Start from 1 if there are no trainers yet
        super().save(*args, **kwargs) 



    def clean(self):
    # Validate that the same course is not enrolled multiple times
        if self.pk:  # Only validate if the instance already has a primary key
            for course in self.courses_opted.all():
                if Enrollment.objects.filter(name=self.name, courses_opted=course).exclude(pk=self.pk).exists():
                # Ensure course has a name attribute
                    if hasattr(course, 'name'):
                        raise ValidationError(f"{self.name} has already enrolled in the {course.name} course.")
                    else:
                        raise ValidationError("Course does not have a 'name' attribute.")



   
    def __str__(self):
        return self.name






class Enrollment(models.Model):
    ONLINE_OFFLINE_CHOICES=[
        ('online', 'online'),
        ('offline', 'offline')
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15,  validators=[RegexValidator(r'^\+91\d{10}$', 'Phone number must be in the format +91XXXXXXXXXX')])
    address = models.TextField()  # Change to TextField for multiline input
    courses_opted = models.ManyToManyField(Course)  # Use ManyToManyField to link courses
    mode_of_training = models.CharField(
        max_length=50, choices=ONLINE_OFFLINE_CHOICES, default='online'
    )
    status = models.CharField(max_length=8, choices=[('active', 'Active'), ('archived', 'Archived')])

    tentative_date_of_joining_course = models.DateField(default=timezone.now)
    enrollment_number = models.PositiveIntegerField(null=True, blank=True)
    archived = models.BooleanField(default=False) 

    def clean(self):
        super().clean()

    # Validate phone number
        phone = self.phone.replace(" ", "").replace("-", "")
        if len(phone) == 10 and phone.isdigit():
            self.phone = "+91" + phone
        elif not phone.startswith("+91") or len(phone) != 13:
            raise ValidationError({"phone": "Phone number must start with +91 and have 10 digits."})

    # Validate duplicate course enrollment
        if self.pk:
            for course in self.courses_opted.all():
                if Enrollment.objects.filter(name=self.name, courses_opted=course).exclude(pk=self.pk).exists():
                    raise ValidationError(f"{self.name} has already enrolled in the {course.name} course.")




   

    def save(self, *args, **kwargs):
        if not self.enrollment_number:
        # Get all existing enrollment numbers from the database
            existing_numbers = Enrollment.objects.values_list('enrollment_number', flat=True).order_by('enrollment_number')
        
        # Find the first missing enrollment number in the sequence
            for i in range(1, len(existing_numbers) + 2):
                if i not in existing_numbers:
                    self.enrollment_number = i
                    break
        # If no gaps, assign the next number after the last enrollment
            if not self.enrollment_number:
                self.enrollment_number = existing_numbers[-1] + 1 if existing_numbers else 1
    
        super().save(*args, **kwargs)




    
    # Validate ManyToManyField relationships
        for course in self.courses_opted.all():
            if Enrollment.objects.filter(name=self.name, courses_opted=course).exclude(pk=self.pk).exists():
                raise ValidationError(f"{self.name} has already enrolled in the {course.name} course.")





    




    @staticmethod
    @transaction.atomic
    def renumber_enrollment(course):
        if not course:
            raise ValueError("Course must be provided to renumber enrollments.")
    
    # Fetch enrollments related to the course, ordered by ID
        enrollments = Enrollment.objects.filter(courses_opted=course).order_by('id')
    
    # Renumber enrollments sequentially
        for idx, enrollment in enumerate(enrollments, start=1):
            enrollment.enrollment_number = idx
            enrollment.save()




    

    

    


    def __str__(self):
        return self.name

    class Meta:
        ordering = ['enrollment_number']



    



       

    




