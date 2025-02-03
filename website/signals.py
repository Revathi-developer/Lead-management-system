from django.db.models.signals import post_delete,post_save
from django.dispatch import receiver
from website.models import Lead, Course,Trainer,Enrollment
from website.views import renumber_leads,renumber_trainers,renumber_enrollment
from django.utils import timezone

@receiver(post_delete, sender=Course)
def adjust_lead_numbers_on_course_delete(sender, instance, **kwargs):
    course = instance  # This ensures you're using the correct course instance
    print(f"Course '{instance.course_name}' deleted, adjusting related records...")
    
    # Update leads associated with the course
    leads = Lead.objects.filter(course=instance)
    leads.update(course=None)

    # Update enrollments associated with the course
    enrollments = Enrollment.objects.filter(courses_opted=instance)
    for enrollment in enrollments:
        enrollment.courses_opted.remove(instance)
        
        if not enrollment.courses_opted.exists():
            enrollment.delete()  # Delete the enrollment if no courses remain
        else:
            # Save the enrollment without triggering validation
            enrollment.save(force_update=True, validate=False)
    
    # Renumber the leads after deleting the course
    renumber_leads()  # This will renumber lead numbers
    
    # Renumber the enrollments (passing the course object)
    renumber_enrollment(course)  # Pass the course variable here
    
    # Optionally, renumber trainers (if that's part of your logic)
    renumber_trainers()


# Signal handler for trainer deletion
@receiver(post_delete, sender=Trainer)
def trainer_deleted(sender, instance, **kwargs):
    print(f"Trainer '{instance.name}' deleted, adjusting trainer numbers...")  # Debugging line
    renumber_trainers()  # Call the renumber function after a trainer is deleted

@receiver(post_save, sender=Lead)
def create_enrollment_for_joined_lead(sender, instance, created, **kwargs):
    if instance.status == 'Joined':
        enrollment, created = Enrollment.objects.get_or_create(
            name=instance.lead_name,
            defaults={
                'email': instance.email,
                'phone': instance.phone,
                'address': instance.location,
                'mode_of_training': "online",
                'tentative_date_of_joining_course': timezone.now(),
            }
        )
        if created and instance.course:
            enrollment.courses_opted.add(instance.course)


@receiver(post_save, sender=Enrollment)
def assign_enrollment_number_on_create(sender, instance, created, **kwargs):
    if created:
        renumber_enrollment()

@receiver(post_delete, sender=Enrollment)
def handle_enrollment_deletion(sender, instance, **kwargs):
    renumber_enrollment()

def renumber_enrollment(course=None):
    if course:
        enrollments = Enrollment.objects.filter(courses_opted=course).order_by('id')
    else:
        enrollments = Enrollment.objects.all().order_by('id')
    for index, enrollment in enumerate(enrollments, start=1):
        enrollment.enrollment_number = index
        enrollment.save(update_fields=["enrollment_number"])