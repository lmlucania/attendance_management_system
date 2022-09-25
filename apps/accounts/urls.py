from django.urls import path
from apps.accounts.views import (LoginView, LogoutView, PasswordResetView, PasswordResetDoneView,
                                 PasswordResetConfirmView, PasswordResetCompleteView)

app_name = 'apps.accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(), name="logout"),
    path('pw_reset/', PasswordResetView.as_view(), name="pw_reset"),
    path('pw_reset/done', PasswordResetDoneView.as_view(), name="pw_reset_done"),
    path('pw_reset/<uidb64>/<token>', PasswordResetConfirmView.as_view(), name="pw_reset_confirm"),
    path('pw_reset/complete', PasswordResetCompleteView.as_view(), name="pw_reset_complete"),
]
