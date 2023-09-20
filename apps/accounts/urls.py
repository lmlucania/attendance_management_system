from django.urls import path

from apps.accounts.views import LoginView, LogoutView

app_name = "apps.accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
