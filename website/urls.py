from django.contrib import admin
from django.urls import path,include
from . import views 
from django.conf import settings
from django.conf.urls.static import static
from .views import add_joined_leads_to_enrollment
from django.contrib.auth.views import LogoutView
from .views import delete_activity
from .views import delete_by_date

urlpatterns = [
    path('',views.login_view,name='login'),
    path('home/', views.home, name='home'),  # Home page
    path('lead/add/', views.add_lead, name='add_lead'),
    path('lead/report/',views.lead_report, name='lead_report'),   # Use the correct function name
    path('lead/list/', views.lead_list, name='lead_list'), 
    path('dashboard-data/', views.dashboard_data, name='dashboard_data'),
    path('lead/edit/<int:lead_id>/',views.edit_lead, name='edit_lead'),
    path('lead/delete/<int:lead_id>/', views.delete_lead, name='delete_lead'),
    path('lead/update_status/<int:lead_id>/', views.update_lead_status, name='update_lead_status'),
    path('delete-by-date/', delete_by_date, name='delete_by_date'),
    path('get-chart-data/', views.get_chart_data, name='get_chart_data'),
    path('update-lead-status/<int:lead_id>/', views.update_lead_status, name='update_lead_status'),
    path('get-sources-data/', views.get_sources_data, name='get_sources_data'),  # For AJAX
    path('get-courses-data/', views.get_courses_data, name='get_courses_data'),  # For AJAX
    
    path('import-leads/', views.import_leads, name='import_leads'),
    path('process-mapping/', views.process_mapping, name='process_mapping'),
    
    path('export-leads/', views.export_leads, name='export_leads'),
    
    path('lead/sources/',views.lead_sources,name='lead_sources'),
    path('course/add/', views.add_course, name='add_course'),  # For adding a course
    path('course_status/', views.course_status, name='course_status'),
    path('delete_course/<int:course_id>/', views.delete_course, name='delete_course'),
    path('course/list/', views.course_list, name='course_list'),  # Assuming you have a course list view
    path('trainer/list/',views.trainer_list,name='trainer_list'),
    path('trainer/edit/<int:id>/',views.edit_trainer,name='edit_trainer'),
    path('trainer/delete/<int:id>/',views.delete_trainer,name='delete_trainer'),
    path('user-activity-log/',views.user_activity_log,name='user_activity_log'),
    path('enrollment/list/',views.enrollment_list,name='enrollment_list'),
    path('enrollment/add/',views.add_enrollment,name='add_enrollment'),
    path('add_joined_leads/', add_joined_leads_to_enrollment, name='add_joined_leads'),
    path('trainer/add/',views.add_trainer,name='add_trainer'),
    path('edit-enrollment/<int:enrollment_id>/',views.edit_enrollment, name='edit_enrollment'),
    path('delete-enrollment/<int:enrollment_id>/',views.delete_enrollment, name='delete_enrollment'),
    path('upload-file/', views.upload_file, name='upload_file'),
    
    path('archive_enrollment/<int:enrollment_id>/', views.archive_enrollment, name='archive_enrollment'),
    path('archived_enrollments/',views.archived_enrollments, name='archived_enrollments'),
    path('delete-activity/<int:activity_id>/', delete_activity, name='delete_activity'),


    path('dashboard/',views.dashboard, name= 'dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/',views.logout_view,name='logout'),
    
  
   
]


