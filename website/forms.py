from django import forms
from .models import Lead, Course,Trainer,Enrollment
from django.utils import timezone

class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['lead_name', 'email', 'phone', 'location','status', 'source', 'course']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').replace(" ", "").replace("-", "")  # Remove spaces and dashes

    # If phone number starts with +91, handle it correctly
        if phone.startswith('+91'):
            phone = phone[3:]  # Strip +91 for validation

    # Check if the phone number contains only digits
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

    # Ensure the phone number has exactly 10 digits
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

    # Re-add +91 to the phone number
        phone = "+91" + phone

        return phone


        def clean(self):
            cleaned_data = super().clean()
            lead_name = cleaned_data.get('lead_name')
            course = cleaned_data.get('course')

        # Check if the same lead is already associated with the selected course
        if Lead.objects.filter(lead_name=lead_name, course=course).exists():
            raise forms.ValidationError(f"{lead_name} is already enrolled in the course '{course}'.")

        return cleaned_data 



class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_name']

class TrainerForm(forms.ModelForm):
    class Meta:
        model= Trainer
        fields = ['name', 'email', 'phone', 'bio', 'expertise','location','resume','type','courses_opted']


    def clean_phone(self):
        phone=self.cleaned_data.get('phone')
        if not phone or len(phone) != 10:
            raise forms.ValidationError('Please enter a 10 digit number.')
        return phone

    def clean_resume(self):
        resume=self.cleaned_data.get('resume')
        if not resume:
            raise forms.ValidationError('Resume is required')
        return resume

    def clean_name(self):
        name = self.cleaned_data['name']
        if Trainer.objects.filter(name=name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError('Trainer name is already taken.')
        return name



class EnrollmentForm(forms.ModelForm):
    
    class Meta:
        model = Enrollment
        fields = [
            'name', 'email', 'phone', 'address', 'courses_opted', 
            'mode_of_training', 'tentative_date_of_joining_course'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter email'}),
            'phone': forms.TextInput(attrs={'placeholder': '+91XXXXXXXXXX'}),
            'address': forms.Textarea(attrs={'cols': 60, 'rows': 6}),
            'courses_opted': forms.CheckboxSelectMultiple(),
            'tentative_date_of_joining_course': forms.DateInput(attrs={'type': 'date'}),
            
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')

        # Remove spaces and dashes
        phone = phone.replace(" ", "").replace("-", "")

        # Validate and format phone number
        if phone.isdigit() and len(phone) == 10:
            phone = "+91" + phone
        elif not phone.startswith("+91") or len(phone) != 13:
            raise forms.ValidationError("Phone number must start with +91 and have 10 digits.")
        
        return phone

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        courses_opted = cleaned_data.get('courses_opted')
        enrollment = self.instance  # Get the current enrollment instance

        if name and courses_opted:
        # Only check for duplicates if courses are selected
            enrolled_courses = Enrollment.objects.filter(name=name, courses_opted__in=courses_opted).exclude(pk=enrollment.pk)
            for course in courses_opted:
                if enrolled_courses.filter(courses_opted=course).exists():
                    raise forms.ValidationError({
                        'courses_opted': f"{name} is already enrolled in the {course.course_name} course."
                })
        return cleaned_data



   
