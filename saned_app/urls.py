from django.urls import path
from . import views

urlpatterns = [
    # AUTH / GENERAL
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('create_user/', views.create_user, name='create_user'),
    path('login_user/', views.login_user, name='login_user'),

    # BENEFICIARY
    path('beneficiary/dashboard/', views.beneficiary_dashboard, name='beneficiary_dashboard'),
    path('beneficiary/my-requests/', views.my_requests, name='my_requests'),
    path('beneficiary/aid-request/', views.aid_request_form, name='aid_request_form'),
    path('beneficiary/submit-request/', views.submit_aid_request, name='submit_aid_request'),
    path('beneficiary/delete-request/<int:request_id>/', views.delete_aid_request, name='delete_aid_request'),

    # NGO
    path('ngo/pending-approval/', views.pending_approval, name='pending_approval'),
    path('ngo/check-approval/', views.check_ngo_approval, name='check_ngo_approval'),
    path('ngo/dashboard/', views.ngo_dashboard, name='ngo_dashboard'),
    path('ngo/region-requests/', views.region_requests, name='region_requests'),
    path('ngo/create-campaign/', views.create_campaign_form, name='create_campaign_form'),
    path('ngo/create-campaign/submit/', views.create_campaign_submit, name='create_campaign_submit'),
    path('ngo/my-campaigns/', views.my_campaigns, name='my_campaigns'),
    path('ngo/approve-request/<int:request_id>/', views.approve_aid_request, name='approve_aid_request'),
    path('ngo/reject-request/<int:request_id>/', views.reject_aid_request, name='reject_aid_request'),
    path('ngo/adopted-requests/', views.adopted_requests, name='adopted_requests'),

    # DONOR
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('donor/donate_to_campaign/<int:campaign_id>/', views.donate_to_campaign, name='donate_to_campaign'),
    path('donor/donate_to_request/<int:request_id>/', views.donate_to_request, name='donate_to_request'),

    path('about/', views.about_us, name='about_us'),
    path('ngo/export-donations-excel/', views.export_donations_excel, name='export_donations_excel'),
    path('ngo/export-requests-excel/', views.export_requests_excel, name='export_requests_excel'),

]
