from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.http import JsonResponse
from .models import Lead,Course,Trainer,Enrollment
from .forms import LeadForm,CourseForm,TrainerForm,EnrollmentForm
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta,datetime 
from django.contrib import messages
from django.db.models import Count
from django.db.models import Q
from tablib import Dataset
import csv
import json
import xlrd
import pandas as pd
import tempfile
import os
from openpyxl import load_workbook
import openpyxl
from io import StringIO
from datetime import date
from django.db.models import Count
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import UserActivity
from django.utils.timezone import now
import calendar
from django.http import JsonResponse
from django.utils.timezone import make_aware,now
from django.utils.timezone import localtime
from .models import Lead,Course
from django import forms
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from website.models import UserActivity
import mimetypes
from django.core.files.storage import FileSystemStorage


def delete_activity(request, activity_id):
    activity = get_object_or_404(UserActivity, id=activity_id)
    activity.delete()
    messages.success(request, "Activity deleted successfully.")
    return redirect('user_activity_log')

def delete_by_date(request):
    if request.method == 'POST':
        delete_range = request.POST.get('delete_range')
        now = datetime.now()

        if delete_range == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif delete_range == 'week':
            start_date = now - timedelta(days=7)
        elif delete_range == 'month':
            start_date = now - timedelta(days=30)
        elif delete_range == 'quarter':
            # Determine the start of the current quarter
            month = now.month
            if month in [1, 2, 3]:
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            elif month in [4, 5, 6]:
                start_date = now.replace(month=4, day=1, hour=0, minute=0, second=0, microsecond=0)
            elif month in [7, 8, 9]:
                start_date = now.replace(month=7, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now.replace(month=10, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            messages.error(request, "Invalid date range selected.")
            return redirect('user_activity_log')

        # Delete activities from the start_date onwards
        deleted_count = UserActivity.objects.filter(timestamp__gte=start_date).delete()[0]
        messages.success(request, f"Deleted {deleted_count} activities.")
        return redirect('user_activity_log')



def upload_file(request):
    required_columns = ["name", "email", "phone", "location"]
    
    if request.method == "POST":
        # Step 1: File Upload
        if "leads_file" in request.FILES:
            leads_file = request.FILES["leads_file"]

            # Check file extension
            file_extension = leads_file.name.split('.')[-1].lower()
            if file_extension not in ["csv", "xls", "xlsx"]:
                messages.error(request, "Invalid file format. Please upload a CSV or Excel file.")
                return redirect("import_leads")

            # Additional MIME type validation
            mime_type, _ = mimetypes.guess_type(leads_file.name)
            valid_mime_types = ["text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]

            if mime_type not in valid_mime_types:
                messages.error(request, "Invalid file format. Please upload a valid CSV or Excel file.")
                return redirect("import_leads")

            # Save the file temporarily
            temp_file_path = tempfile.NamedTemporaryFile(delete=False).name
            with open(temp_file_path, "wb") as temp_file:
                for chunk in leads_file.chunks():
                    temp_file.write(chunk)

            request.session["leads_file_path"] = temp_file_path

            try:
                # Load the dataframe based on file extension
                if file_extension == "csv":
                    df = pd.read_csv(temp_file_path)
                elif file_extension in ["xls", "xlsx"]:
                    df = pd.read_excel(temp_file_path, engine="openpyxl")
                else:
                    raise ValueError("Invalid file format. Please upload a CSV or Excel file.")

                # Check if dataframe is empty
                if df is None or df.empty is True:
                    messages.error(request, "The uploaded file is empty.")
                    return redirect("import_leads")


                # Save file columns to session for mapping
                file_columns = list(df.columns)
                request.session["file_columns"] = file_columns

                messages.info(request, "File uploaded successfully. Please map the fields.")
                return render(request, "website/import_mapping.html", {
                    "file_columns": file_columns,
                    "required_columns": required_columns,
                })

            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
                return redirect("import_leads")
            finally:
                os.remove(temp_file_path)  # Cleanup temp file






import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Lead, Course

def import_leads(request):
    if request.method == "POST" and request.FILES.get("leads_file"):
        file = request.FILES["leads_file"]

        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            elif file.name.endswith((".xls", ".xlsx")):
                df = pd.read_excel(file)
            else:
                messages.error(request, "Invalid file format. Upload CSV, XLS, or XLSX.")
                return redirect("import_leads")

            # Store file columns in session for mapping
            request.session["file_columns"] = list(df.columns)
            request.session["uploaded_data"] = df.to_dict(orient="records")

            return render(request, "website/import_mapping.html", {"file_columns": df.columns})

        except Exception as e:
            messages.error(request, f"Error reading file: {str(e)}")
            return redirect("import_leads")

    return render(request, "website/import_leads.html")


def process_mapping(request):
    if request.method == "POST":
        column_mapping = {
            "lead_name": request.POST.get("column_mapping_lead_name"),
            "email": request.POST.get("column_mapping_email"),
            "phone": request.POST.get("column_mapping_phone"),
            "location": request.POST.get("column_mapping_location"),
            "source": request.POST.get("column_mapping_source"),
            "course": request.POST.get("column_mapping_course"),
        }

        uploaded_data = request.session.get("uploaded_data", [])

        if not uploaded_data:
            messages.error(request, "No data found. Please upload the file again.")
            return redirect("import_leads")

        if not column_mapping["lead_name"] or not column_mapping["email"] or not column_mapping["phone"] or not column_mapping["location"]:
            messages.error(request, "Lead Name, Email, Phone, and Location are mandatory.")
            return redirect("import_mapping")

        # Handling Course
        for row in uploaded_data:
            lead_name = str(row.get(column_mapping["lead_name"], "")).strip()
            email = str(row.get(column_mapping["email"], "")).strip()
            phone = str(row.get(column_mapping["phone"], "")).strip()
            location = str(row.get(column_mapping["location"], "")).strip()
            source = str(row.get(column_mapping["source"], "")).strip()
            course_name = str(row.get(column_mapping["course"], "")).strip() or None  # Allow None if course is not mapped

            if not lead_name or not email or not phone or not location:
                continue  # Skip invalid rows

            # Handle duplicates
            existing_lead = Lead.objects.filter(email=email).first()
            if existing_lead:
                action = request.POST.get("handle_duplicates")
                if action == "ignore":
                    continue
                elif action == "update":
                    existing_lead.lead_name = lead_name
                    existing_lead.phone = phone
                    existing_lead.location = location
                    existing_lead.source = source
                    if course_name:
                        existing_lead.course, _ = Course.objects.get_or_create(course_name=course_name)
                    existing_lead.save()
                    continue

            # Create new lead
            course_obj = None
            if course_name:
                course_obj, _ = Course.objects.get_or_create(course_name=course_name)

            Lead.objects.create(
                lead_name=lead_name,
                email=email,
                phone=phone,
                location=location,
                source=source,
                course=course_obj,
            )

        messages.success(request, "Leads imported successfully!")
        return redirect("import_leads")


def export_leads(request):
    leads = Lead.objects.all()
    dataset = Dataset()
    
    # Define headers
    dataset.headers = ['Lead Name', 'Email', 'Phone', 'Location', 'Status', 'Source', 'Course']
    
    # Add lead data to the dataset
    for lead in leads:
       
        dataset.append([lead.lead_name, lead.email, lead.phone, lead.location, lead.status, lead.source, lead.course])
    
    # Export data as XLSX
    response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="leads.xlsx"'
    return response

def login_view(request):
    if request.method == "POST":
        # Check if it's an AJAX request (assuming you're using fetch)
        if request.headers.get('Content-Type') == 'application/json':
            import json
            data = json.loads(request.body)

            username = data.get('username')
            password = data.get('password')
            
            # Authenticate the user
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)  # Log the user in
                return JsonResponse({'success': True, 'redirect': '/home/'})  # Redirect to home
            else:
                return JsonResponse({'success': False, 'error_message': 'Invalid credentials'})
        else:
            # Handle regular form submission
            form = AuthenticationForm(data=request.POST)
            if form.is_valid():
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('home')
                else:
                    return render(request, 'website/login.html', {'form': form, 'error_message': 'Invalid credentials'})
            else:
                return render(request, 'website/login.html', {'form': form, 'error_message': 'Invalid credentials'})
    else:
        form = AuthenticationForm()
    return render(request, 'website/login.html', {'form': form})


def user_activity_log(request):
    activities = UserActivity.objects.all().order_by('-timestamp')
    for activity in activities:
        activity.timestamp = localtime(activity.timestamp)
       
    return render(request,'website/user_activity_log.html',{'activities': activities})
 
@login_required
def home(request):
    # Get total leads
    leads=Lead.objects.all()
    total_leads = leads.count()
    
    # Get total enrollments
    
    total_enrollments = leads.filter(status='Joined').count()
    
    # Calculate conversion rate if needed
    conversion_rate = (total_enrollments / total_leads * 100) if total_leads > 0 else 0
    
    return render(request, 'website/home.html', {
        'total_leads': total_leads,
        'total_enrollments': total_enrollments,
        'conversion_rate': conversion_rate
    })

def logout_view(request):
    logout(request)
    return redirect('login')
def course_status(request):
    courses = Course.objects.all()

    course_status_data = []
    for course in courses:
        leads = Lead.objects.filter(course=course).exclude(course__isnull=True)  # Exclude NULL courses
        
        lead_details = [
            {
                "lead_name": lead.lead_name,
                "email": lead.email,
                "phone": lead.phone,
                "location": lead.location,
                "status": lead.status,
                "source": lead.source,
                "date_joined": lead.date_joined.strftime("%d-%m-%Y"),
                "id": lead.id,
                "temp_status": request.session.get(f"status_{lead.id}", lead.status),
            }
            for lead in leads
        ]

        course_status_data.append({
            "course_name": course.course_name,
            "leads": lead_details,  # Only keeping the processed lead details
        })

    context = {"course_status_data": course_status_data}

    if request.method == "POST":
        lead_id = request.POST.get('lead_id')
        new_status = request.POST.get('status')
        if lead_id and new_status:
            request.session[f"status_{lead_id}"] = new_status
            messages.success(request, f"Lead status updated to {new_status}!")
            return redirect('course_status')

    return render(request, "website/course_status.html", context)





def update_lead_status(request, lead_id):
    if request.method == "POST":
        lead = get_object_or_404(Lead, id=lead_id)
        new_status = request.POST.get("status")
        
        # Temporarily store the new status in session, without saving to the database
        if 'course_status_updates' not in request.session:
            request.session['course_status_updates'] = {}

        # Store the updated status in session
        request.session['course_status_updates'][lead.id] = new_status
        request.session.modified = True  # Ensure the session is updated
        
        messages.success(request, f"Status for {lead.lead_name} updated to {new_status} (temporary change).")
        return redirect('course_status')  # Redirect to the course status page

    else:
        messages.error(request, "Invalid request method.")
        return redirect('course_status')

def dashboard_data(request):
    
    # Determine the filter (e.g., this_week, last_week, this_month, custom)
    filter = request.GET.get('filter', 'this_week')
    today = datetime.today()

    # Date range logic
    if filter == 'this_week':
        start_date = today - timedelta(days=today.weekday())  # Start of this week
        end_date = start_date + timedelta(days=6)  # End of this week
    elif filter == 'last_week':
        start_date = today - timedelta(days=today.weekday() + 7)  # Start of last week
        end_date = start_date + timedelta(days=6)  # End of last week
    elif filter == 'this_month':
        start_date = today.replace(day=1)  # Start of this month
        end_date = today  # Current day of the month
    elif filter == 'custom':
        start_date = request.GET.get('from_date')
        end_date = request.GET.get('to_date')
        if start_date and end_date:
            start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
            end_date = make_aware(datetime.strptime(end_date, "%Y-%m-%d"))
        else:
            start_date = today
            end_date = today
    else:
        start_date = today
        end_date = today

    start_date = make_aware(start_date)
    end_date = make_aware(end_date)

    # Fetch dynamic data
    total_leads = Lead.objects.filter(created_at__range=(start_date, end_date)).count()
    total_enrollments = Enrollment.objects.filter(enrollment_date__range=(start_date, end_date)).count()
    leads_by_source = Lead.objects.filter(created_at__range=(start_date, end_date)) \
        .values('source').annotate(total=Count('id'))
    leads_by_course = Lead.objects.filter(created_at__range=(start_date, end_date)) \
        .values('course').annotate(total=Count('id'))

    # Convert queryset to dictionaries
    leads_by_source_data = {item['source']: item['total'] for item in leads_by_source}
    leads_by_course_data = {item['course']: item['total'] for item in leads_by_course}

    # Pass data to the template
    context = {
        'total_leads': total_leads,
        'total_enrollments': total_enrollments,
        'leads_by_source': leads_by_source_data,
        'leads_by_course': leads_by_course_data,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'dashboard.html', context)











def get_sources_data(start_date, end_date):
    # Fetching lead sources with counts in the date range
    sources = Lead.objects.filter(created_at__range=[start_date, end_date])\
                           .values('source')\
                           .annotate(count=Count('source'))  # Count occurrences of each source
    
    return sources

def get_courses_data(start_date, end_date):
    # Fetching lead courses with counts in the date range
    courses = Lead.objects.filter(created_at__range=[start_date, end_date])\
                           .values('course')\
                           .annotate(count=Count('course'))  # Count occurrences of each course
    
    return courses








def get_chart_data(request):
    try:
        # Get date range parameter
        date_range = request.GET.get('dateRange', 'this_week')
        today = timezone.now()
        
        # Default date range (for fallback purposes)
        start_date = today - timedelta(days=7)
        end_date = today
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Determine start and end dates based on the selected range
        if date_range == 'this_week':
            start_date = today - timedelta(days=today.weekday())  # Start of the week (Monday)
            end_date = today  # Today's date

        elif date_range == 'last_week':
            start_date = today - timedelta(days=today.weekday() + 7)  # 7 days before the start of this week
            end_date = start_date + timedelta(days=6)  # Last week's end date
        elif date_range == 'this_month':
            start_date = today.replace(day=1)  # First day of the current month
            end_date = today  # Today's date
        elif date_range == 'last_month':
            first_day_last_month = today.replace(day=1) - timedelta(days=1)  # First day of last month
            start_date = first_day_last_month.replace(day=1)
            end_date = first_day_last_month
        elif date_range == "this_quarter":
            current_month = today.month
            if current_month >= 4 and current_month <= 6:
                quarter = "Q1"
                start_month = 4
            elif current_month >= 7 and current_month <= 9:
                quarter = "Q2"
                start_month = 7
            elif current_month >= 10 and current_month <= 12:
                quarter = "Q3"
                start_month = 10
            else:
                quarter = "Q4"
                start_month = 1

            start_date = today.replace(month=start_month, day=1)
            end_date = today
        elif date_range == "previous_quarter":
            current_month = today.month
            if current_month >= 4 and current_month <= 6:
                previous_quarter = "Q4"
                start_month = 1
                year = today.year - 1
            elif current_month >= 7 and current_month <= 9:
                previous_quarter = "Q1"
                start_month = 4
                year = today.year
            elif current_month >= 10 and current_month <= 12:
                previous_quarter = "Q2"
                start_month = 7
                year = today.year
            else:
                previous_quarter = "Q3"
                start_month = 10
                year = today.year

            start_date = today.replace(year=year, month=start_month, day=1)
            end_month = start_month + 2
            end_date = today.replace(year=year, month=end_month, day=1) - timedelta(days=1)
        
        elif date_range == 'custom':
            from_date = request.GET.get("from_date")
            to_date = request.GET.get("to_date")
            if not from_date or not to_date:
                return JsonResponse({
                    "error": "Invalid date range. Please select both 'From' and 'To' dates."
                }, status=400)

            try:
                # Convert string dates to datetime objects
                start_date = timezone.make_aware(datetime.strptime(from_date, "%Y-%m-%d"))
                end_date = timezone.make_aware(datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
            except ValueError:
                return JsonResponse({
                    "error": "Invalid date format. Dates must be in 'YYYY-MM-DD' format."
                }, status=400)

        # Log start and end dates for debugging
        print(f"Start Date: {start_date}, End Date: {end_date}")

        # Fetch leads within the date range
        leads = Lead.objects.filter(created_at__gte=start_date, created_at__lte=end_date)

        # Log the query for debugging
       
        # Check if there are no leads
        if not leads.exists():
            return JsonResponse({
                "conversion": {"labels": [], "data": []},
                "sources": {"labels": [], "data": []},
                "courses": {"labels": [], "data": []},
                "message": f"No leads joined during the selected period {(date_range)} ."
            }, status=200)

        # Conversion Data
        conversion_data = {
            "labels": ["Leads", "Enrollments"],
            "data": [leads.count(), leads.filter(status="Joined").count()],
        }

        # Source Data
        source_data = leads.values("source").annotate(count=Count("id"))
        sources = {
            "labels": [entry["source"] for entry in source_data],
            "data": [entry["count"] for entry in source_data],
        }

        # Course Data
        course_data = leads.values("course__course_name").annotate(count=Count("id"))
        courses = {
            "labels": [entry["course__course_name"] for entry in course_data],
            "data": [entry["count"] for entry in course_data],
        }

        # Return chart data
        return JsonResponse({
            "conversion": conversion_data,
            "sources": sources,
            "courses": courses,
        })
    except Exception as e:
        return JsonResponse({
            "error": f"Failed to load chart data. Please try again. Error: {str(e)}"
        }, status=500)


def lead_list(request):
    period = request.GET.get('period')  # Get the period from the query parameter
    print(f"Period received: {period}")  # Debugging line

    today = timezone.now()  # Current date and time
    leads = Lead.objects.all().order_by('lead_number')  # Initially get all leads
    print(f"Total leads: {leads.count()}") 
    
    # Filtering logic based on the selected period
    
    if period == 'this_week':
        # Start of the current week (Monday) at midnight (00:00:00)
        start_date = today - timedelta(days=today.weekday())  # Monday this week
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)  # Ensure start time is midnight
        end_date = today  # End date is the current time
        print(f"Filtering leads from this week: {start_date} to {end_date}")  # Debugging line
        leads = leads.filter(created_at__gte=start_date, created_at__lte=end_date)
        print(f"Leads from this week: {leads.count()}")

    elif period == 'last_week':
        # Start and end of last week (from the previous Monday to Sunday)
        start_date = today - timedelta(days=today.weekday() + 7)  # Start of the last week
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)  # Ensure start time is midnight
        end_date = start_date + timedelta(days=6)  # End of the last week (Sunday)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)  # End time is 23:59:59
        print(f"Filtering leads from last week: {start_date} to {end_date}")  # Debugging line
        leads = leads.filter(created_at__gte=start_date, created_at__lte=end_date)

    elif period == 'last_month':
        # Start of last month
        last_month_start = today.replace(day=1) - timedelta(days=1)  # Move back one day to get the last day of previous month
        last_month_start = last_month_start.replace(day=1)  # First day of last month
        # End of last month
        last_month_end = today.replace(day=1) - timedelta(days=1)  # Last day of last month
        last_month_end = last_month_end.replace(hour=23, minute=59, second=59, microsecond=999999)  # End time is 23:59:59
        print(f"Filtering leads from last month: {last_month_start} to {last_month_end}")  # Debugging line
        leads = leads.filter(created_at__gte=last_month_start, created_at__lte=last_month_end)

    # Print all leads (for debugging purposes)
    for lead in leads:
        print(f"Lead ID: {lead.id}, Created At: {lead.created_at}")  # Debugging line

    if leads:
        print(f"Leads found: {leads.count()}")
    else:
        print("No leads found.")

    # Return the filtered leads to the template
    return render(request, 'website/lead_list.html', {'leads': leads})

def add_lead(request):

    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            
            lead_name = form.cleaned_data['lead_name']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            source = form.cleaned_data['source']
            course = form.cleaned_data['course']
            

            # Check if the lead_name is already enrolled in the specified course
            if Lead.objects.filter(lead_name=lead_name, course=course).exists():
                messages.error(request, f"{lead_name} is already enrolled in the course '{course}'.")
                return render(request, 'website/add_lead.html', {'form': form, 'courses': Course.objects.all()})


            # Save the new Lead instance
            lead = form.save(commit=False)
            lead.save()
            UserActivity.objects.create(
                user=request.user if request.user.is_authenticated else None,
                path=request.path,
                action=f"Added lead: {lead.lead_name}",  # Safely access lead_name here
                timestamp=now()
            )
            messages.success(request, f"Lead '{lead.lead_name}' added successfully!")
            return redirect('lead_list')
        else:
            messages.error(request, "There was an error in the form submission.")
    else:
        form = LeadForm()

       
    return render(request, 'website/add_lead.html', {'form': form, 'courses': Course.objects.all()})


def renumber_leads():
    # Get all leads ordered by id
    leads = Lead.objects.all().order_by('id')
    
    with transaction.atomic():
        for index, lead in enumerate(leads, start=1):
            lead.lead_number = index  # Update lead_number to be sequential
            lead.save()



def edit_lead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    lead_name= lead.lead_name
    
    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        
        if form.is_valid():
            lead_name = form.cleaned_data['lead_name']
            course = form.cleaned_data['course']
            
            # Check if the lead_name is already enrolled in the specified course,
            # but exclude the current lead from the check (so it doesn't flag itself as a duplicate)
            if Lead.objects.filter(lead_name=lead_name, course=course).exclude(id=lead.id).exists():
                messages.error(request, f"{lead_name} is already enrolled in the course '{course}'.")
                return render(request, 'website/edit_lead.html', {'form': form})
            
            # Save the form and update the lead
            form.save()
            messages.success(request, "Lead edited successfully!")
            return redirect('lead_list')  # Redirect to the lead list after saving
    else:
        form = LeadForm(instance=lead)

        UserActivity.objects.create(
        user=request.user if request.user.is_authenticated else None,  # Same as above, store user or None
        path=request.path,  # The current URL (edit page URL)
        action=f"Lead '{lead_name}' edited.",  # Action type is 'EDIT' for modifying
        timestamp=timezone.now()  # Timestamp of the action
    )
    
    return render(request, 'website/edit_lead.html', {'form': form})


def delete_lead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    lead_name= lead.lead_name
    if request.method == 'POST':
        lead.delete()
        renumber_leads()  # Renumber leads after deletion
        messages.success(request, 'Lead deleted successfully!')
        return redirect('lead_list')  # Redirect to the lead list after deletion

        UserActivity.objects.create(
        user=request.user if request.user.is_authenticated else None,  # Store the user or None
        path=request.path,  # The current URL (delete page URL)
        action=f"Lead '{lead_name}' deleted.",  # Action type is 'DELETE' for deleting
        timestamp=timezone.now()  
        )
    return render(request, 'website/confirm_delete.html', {'lead': lead})





def update_lead_status(request, lead_id):
    lead = Lead.objects.get(id=lead_id)
    new_status = request.POST.get('status')

    print(f"Updating lead {lead_id}: New Status: {new_status}")  # Debugging line

    if new_status == "Joined" and not lead.date_joined:
        lead.date_joined = timezone.now()
        print(f"Setting date_joined for lead {lead_id} to {lead.date_joined}")  # Debugging line
    
    lead.status = new_status
    lead.save()
    return redirect('lead_list')


def lead_report(request):
    # Get the current time in UTC (timezone-aware)
    today = make_aware(datetime.now())

    # Start of this week (Monday) at midnight (00:00) in UTC time
    this_week_start = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=today.weekday())

    # Start and end of last week
    last_week_start = this_week_start - timedelta(weeks=1)
    last_week_end = this_week_start - timedelta(days=1)

    # Start and end of last month
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month_end = today.replace(day=1) - timedelta(days=1)

    # Convert to local time (Asia/Kolkata)
    today_local = localtime(today)
    this_week_start_local = localtime(this_week_start)
    last_week_start_local = localtime(last_week_start)
    last_week_end_local = localtime(last_week_end)
    last_month_start_local = localtime(last_month_start)
    last_month_end_local = localtime(last_month_end)

    # Debugging prints to check local time ranges
    print(f"Today (local): {today_local}")
    print(f"This week (start to now): {this_week_start_local} to {today_local}")
    print(f"Last week: {last_week_start_local} to {last_week_end_local}")
    print(f"Last month: {last_month_start_local} to {last_month_end_local}")

    # Filter leads based on created_at and count them
    leads_this_week = Lead.objects.filter(created_at__gte=this_week_start).count()
    leads_last_week = Lead.objects.filter(
        created_at__gte=last_week_start,
        created_at__lte=last_week_end
    ).count()
    leads_last_month = Lead.objects.filter(
        created_at__gte=last_month_start,
        created_at__lte=last_month_end
    ).count()

    # Debugging prints to check the count of leads
    print(f"Leads this week: {leads_this_week}")
    print(f"Leads last week: {leads_last_week}")
    print(f"Leads last month: {leads_last_month}")

    # Prepare context for the template
    context = {
        'leads_this_week': leads_this_week,
        'leads_last_week': leads_last_week,
        'leads_last_month': leads_last_month,
    }

    return render(request, 'website/lead_report.html', context)

def lead_sources(request):
    leads = Lead.objects.all()
    return render(request,'website/lead_sources.html',{'leads':leads})


def course_list(request):
    courses = Course.objects.all()  # Fetch all courses
    return render(request, 'website/course_list.html', {'courses': courses})



def edit_course(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request,"course updated successfully")
            return redirect('course_list')  # Redirect to the course list page after saving
    else:
        form = CourseForm(instance=course)
        UserActivity.objects.create(
        user=request.user if request.user.is_authenticated else None,  # Same as above, store user or None
        path=request.path,  # The current URL (edit page URL)
        action=f"course '{course.course_name}' edited.",  # Action type is 'EDIT' for modifying
        timestamp=timezone.now()  # Timestamp of the action
        )
    return render(request, 'website/edit_course.html', {'form': form})





def add_course(request):
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        
        if course_name:
            # Check if the course already exists
            if Course.objects.filter(course_name=course_name).exists():
                # Show an error message if the course name already exists
                messages.error(request, "Course with this name already exists.")
            else:
                # Create a new course and save it to the database
                course = Course.objects.create(course_name=course_name)
                messages.success(request, "Course added successfully!")

                # Log user activity
                UserActivity.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    path=request.path,
                    action=f"Added course: {course.course_name}",  # Use the saved course object
                    timestamp=now()
                )
            return redirect('course_list')
    
    return render(request, 'website/add_course.html')








def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course_name = course.course_name  # Store the course name before deletion
    course.delete()  # Delete the course

    # Show a success message
    messages.success(request, 'Course deleted successfully.')

    # Log user activity
    UserActivity.objects.create(
        user=request.user if request.user.is_authenticated else None,  # Store the user or None
        path=request.path,  # The current URL (delete page URL)
        action=f"Course '{course_name}' deleted.",  # Use the stored course_name
        timestamp=now()  # Timestamp of the action
    )

    return redirect('course_list')  # Redirect to the course list page





def add_trainer(request):
    if request.method == 'POST':
        form = TrainerForm(request.POST, request.FILES)
        if form.is_valid():
            trainer = form.save()  # Save the trainer object
            messages.success(request, 'Trainer added successfully!')

            # Log user activity
            UserActivity.objects.create(
                user=request.user if request.user.is_authenticated else None,
                path=request.path,
                action=f"Added Trainer: {trainer.name}",  # Use 'name' field from the Trainer model
                timestamp=now()
            )

            return redirect('trainer_list')
        else:
            # If form is invalid, show form error messages
            messages.error(request, 'There was an error with your form submission.')
    else:
        form = TrainerForm()

    return render(request, 'website/add_trainer.html', {'form': form})





def renumber_trainers():
    # Get all trainers ordered by id (or any other field you want to order by)
    trainers = Trainer.objects.all().order_by('id')
    
    with transaction.atomic():  # Ensures that the operation is atomic
        for index, trainer in enumerate(trainers, start=1):
            trainer.trainer_number = index  # Update trainer_number to be sequential
            trainer.save()



def edit_trainer(request, id):
    trainer = get_object_or_404(Trainer, pk=id)
    
    if request.method == 'POST':
        form = TrainerForm(request.POST, request.FILES, instance=trainer)
        
        if form.is_valid():
            # Check for duplicate trainer name
            if Trainer.objects.filter(name=form.cleaned_data['name']).exclude(pk=trainer.pk).exists():
                form.add_error('name', 'Trainer name is already taken.')
            else:
                # Save trainer and log activity
                trainer = form.save()
                messages.success(request, 'Trainer details updated successfully!')

                UserActivity.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    path=request.path,
                    action=f"Trainer '{trainer.name}' edited.",
                    timestamp=now()
                )

                return redirect('trainer_list')  # Redirect after successful edit
        else:
            messages.error(request, 'There were errors in the form submission.')
    else:
        form = TrainerForm(instance=trainer)

    return render(request, 'website/edit_trainer.html', {'form': form, 'trainer': trainer})


def delete_trainer(request, id):
    trainer = get_object_or_404(Trainer, id=id)  # Fetch the trainer object
    trainer_name = trainer.name  # Use 'name' field from the Trainer model

    if request.method == 'POST':
        trainer.delete()  # Delete the trainer
        renumber_trainers()  # Optional: Renumber trainers if needed
        messages.success(request, 'Trainer deleted successfully!')

        # Log user activity
        UserActivity.objects.create(
            user=request.user if request.user.is_authenticated else None,  # Store the user or None
            path=request.path,  # The current URL (delete page URL)
            action=f"Trainer '{trainer_name}' deleted.",  # Log the trainer's name
            timestamp=now()  # Timestamp of the action
        )

        return redirect('trainer_list')  # Redirect to the trainer list page after deletion

    return render(request, 'website/delete_trainer.html', {'trainer': trainer})  # Pass 'trainer' to the template

    




def trainer_list(request):
    trainers = Trainer.objects.all()
    return render(request, 'website/trainer_list.html', {'trainers': trainers})






def add_enrollment(request):
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        
        # Check if form is valid
        if form.is_valid():
            # Get the selected lead and courses
            lead = form.cleaned_data.get('lead')
            courses = form.cleaned_data.get('courses_opted')
            
            # Check for existing enrollments for the same lead and courses
            if lead:
                existing_enrollment = Enrollment.objects.filter(lead=lead, courses_opted__in=courses)
                if existing_enrollment.exists():
                    messages.warning(request, "This lead is already enrolled in one or more of the selected courses.")
                    return render(request, 'website/add_enrollment.html', {'form': form})

            # If no existing enrollment, save the new enrollment
            enrollment = form.save(commit=False)
            enrollment.save()  # Now it has an ID

            # Handle many-to-many relationship
            enrollment.courses_opted.set(courses)  # Assign courses
            enrollment.save()  # Save again to ensure courses are saved

            # Log user activity after successful save
            UserActivity.objects.create(
                user=request.user if request.user.is_authenticated else None,
                path=request.path,
                action=f"Added enrollment for lead: {enrollment.name}",  # Assuming 'name' is a field of 'lead'
                timestamp=now()
            )

            messages.success(request, "Enrollment added successfully!")
            return redirect('enrollment_list')  # Redirect after successful save
        else:
            messages.error(request, "Form is not valid. Please check the fields.")
            print(form.errors)
            return render(request, 'website/add_enrollment.html', {'form': form})
    else:
        form = EnrollmentForm()

    return render(request, 'website/add_enrollment.html', {'form': form})




def renumber_enrollment(course):
    # Fetch all enrollments associated with the course and order by id
    enrollments = Enrollment.objects.filter(courses_opted=course).order_by('id')

    # Prepare the list for bulk update
    updated_enrollments = []
    
    # Renumber enrollments
    for index, enrollment in enumerate(enrollments, start=1):
        enrollment.enrollment_number = index  # Set the new enrollment number
        updated_enrollments.append(enrollment)  # Append for bulk update
    
    # Perform bulk update for all enrollments
    if updated_enrollments:
        Enrollment.objects.bulk_update(updated_enrollments, ['enrollment_number'])
    
    # Optional: Print out the updated enrollments for debugging
    for enrollment in updated_enrollments:
        print(f"Renumbered enrollment {enrollment.id} to {enrollment.enrollment_number}")





 
def add_joined_leads_to_enrollment(request):
    joined_leads = Lead.objects.filter(status='joined')

    for lead in joined_leads:
        if not Enrollment.objects.filter(name=lead.lead_name).exists():
            enrollment = Enrollment(
                name=lead.lead_name,
                email=lead.email,
                phone=lead.phone,
                address=lead.location,
                mode_of_training='online',
                tentative_date_of_joining_course=timezone.now()
            )
            enrollment.save()

            # Check if lead.course is not None before assigning
            if lead.course:
                enrollment.courses_opted.set([lead.course])
            enrollment.save()  # Save the enrollment after adding courses
            
    return render(request, 'website/enrollment_list.html')




def edit_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        
        if form.is_valid():
            enrollment = form.save()  # Save updated enrollment
            messages.success(request, "Enrollment details updated successfully.")
            
            # Log the user activity
            UserActivity.objects.create(
                user=request.user if request.user.is_authenticated else None,
                path=request.path,
                action=f"Enrollment for '{enrollment.name}' edited.",  # Replace 'student_name' as per your model
                timestamp=now()
            )
            
            return redirect('enrollment_list')  # Redirect after saving
        else:
            messages.error(request, "There were errors in the form submission.")
    else:
        form = EnrollmentForm(instance=enrollment)
    
    return render(request, 'website/edit_enrollment.html', {'form': form})





def delete_enrollment(request, enrollment_id):
    try:
        # Fetch the enrollment
        enrollment = Enrollment.objects.get(id=enrollment_id)
        
        # Get related courses (ManyToManyField)
        courses = enrollment.courses_opted.all()

        # Log user activity for deletion
        UserActivity.objects.create(
            user=request.user if request.user.is_authenticated else None,
            path=request.path,
            action=f"Enrollment for {enrollment.name} deleted.",
            timestamp=now()
        )

        # Delete the enrollment
        enrollment.delete()

        # Renumber enrollments for related courses
        for course in courses:
            Enrollment.renumber_enrollment(course)

        messages.success(request, f"Enrollment for {enrollment.name} has been deleted.")
    except Enrollment.DoesNotExist:
        messages.error(request, "Enrollment not found.")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
    return redirect('enrollment_list')


def archive_enrollment(request, enrollment_id):
    # Fetch the enrollment by ID
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    # Set the 'archived' field to True
    enrollment.archived = True
    enrollment.save()
    
    # Display a success message
    messages.success(request, f'Enrollment "{enrollment.name}" archived successfully.')

    # Redirect back to the enrollment list
    return redirect('enrollment_list')


# views.py
def archived_enrollments(request):
    # Get all enrollments that are archived
    archived = Enrollment.objects.filter(archived=True)
    
    # Render the template with the archived enrollments
    return render(request, 'website/archived_enrollments.html', {'archived': archived})






def enrollment_list(request):
    # Fetch all enrollments ordered by enrollment_number
    enrollments = Enrollment.objects.all().prefetch_related('courses_opted').order_by('enrollment_number')
    
    # Add a sequential enrollment number dynamically
    for index, enrollment in enumerate(enrollments, start=1):
        enrollment.sequential_number = index  # Add a temporary attribute
    
    return render(request, 'website/enrollment_list.html', {'enrollments': enrollments})







def dashboard(request):
    
    leads = Lead.objects.all()
    total_leads = leads.count()
    total_enrollments = leads.filter(status='Joined').count()

    # Data for pie charts
    course_data = Course.objects.annotate(
        lead_count=Count('lead')
    ).order_by('-lead_count')

    # Fetch source data dynamically
    source_data = (
        Lead.objects.values('source')
        .annotate(count=Count('source'))
        .order_by('-source')
    )

    context = {
        'total_leads': total_leads,
        'total_enrollments': total_enrollments,
        'conversion_rate': (total_enrollments / total_leads) * 100 if total_leads > 0 else 0,
        'course_data': course_data,
        'source_data': source_data,
    }
    return render(request, 'website/dashboard.html', context)


