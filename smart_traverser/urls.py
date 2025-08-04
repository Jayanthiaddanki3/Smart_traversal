from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('trip/', views.trip_input_view, name='trip_input'),
    path('budget_options/', views.budget_options_view, name='budget_options'),  # ✅ New
    path('budget_detail/', views.budget_detail_view, name='budget_detail'),
    path('book_ticket/', views.book_ticket_view, name='book_ticket'),
    path('download_ticket/', views.download_ticket_view, name='download_ticket'),
    path('chat/', views.get_response, name='get_response')

]
