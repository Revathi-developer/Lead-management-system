from django.contrib import admin
from .models import Lead,Course,Trainer,Enrollment # Import your Lead model

# Register your models here.

class LeadAdmin(admin.ModelAdmin):
   list_display = (
        'lead_name',        # Correct field name
        'lead_number',      # Correct field name
        'date_joined',      # Correct field name
        'email',            # Correct field name
        'phone',            # Correct field name
        'location',         # Correct field name
        'status',           # Correct field name
        'source',           # Correct field name
        'course',           # Correct field name
    )
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_name',)  # Display the course name in the admin list view

    list_filter = ('course_name',)  # Add a filter for course choices

class TrainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'bio', 'expertise', 'location', 'type', 'date_of_joining', 'trainer_number')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('type', 'courses_opted')
    ordering = ['trainer_number']  # Sort by trainer_number in ascending order


class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'status', 'tentative_date_of_joining_course', 'enrollment_number', 'archived')  # Fields to display in the list view
    search_fields = ('name', 'email', 'phone')  # Fields to search in the admin panel
    list_filter = ('status', 'archived')  # Add filters on status and archived fields
    ordering = ['enrollment_number']  # Ensure ordering is specified here too

admin.site.register(Lead,LeadAdmin)
admin.site.register(Course,CourseAdmin)
admin.site.register(Trainer,TrainerAdmin)
admin.site.register(Enrollment,EnrollmentAdmin)
