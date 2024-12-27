from django.urls import path
from . import views

urlpatterns = [
    path('', views.show_login, name='show_login'),  
    path('logout/', views.logout, name='logout'), 
    path('login/', views.login, name='login'),
    path('auth/callback/', views.auth_callback, name='auth_callback'),
    path('emails/', views.get_emails, name='emails'),
    path('email/<str:email_id>/', views.view_email, name='email_detail'),
    path('compose/', views.compose_email, name='compose_email'),
    path('sent-emails/', views.get_sent_emails, name='sent_emails'),
    path('deleted-emails/', views.get_deleted_emails, name='deleted_emails'),
    path('toggle-read/<str:email_id>/<str:is_read>/', views.toggle_read_status, name='toggle_read_status'),
    path('delete_email/<str:email_id>/', views.delete_email, name='delete_email'),
    path('folders/', views.view_folders, name='view_folders'),
    path('folders/create/', views.create_folder, name='create_folder'),
    path('folders/rename/<str:folder_id>/', views.rename_folder, name='rename_folder'),
    path('folders/delete/<str:folder_id>/', views.delete_folder, name='delete_folder'),
    path('move_email/<str:email_id>/', views.move_email_to_folder, name='move_email_to_folder'),   
    path('folders/<str:folder_id>/emails/', views.view_folder_emails, name='view_folder_emails'),
]
