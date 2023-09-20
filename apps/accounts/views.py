from django.contrib.auth import views
from django.urls import reverse_lazy

from apps.accounts.form import LoginForm
from apps.accounts.models import User


class LoginView(views.LoginView):
    form_class = LoginForm
    redirect_authenticated_user = True
    template_name = "material-dashboard-master/pages/sign-in.html"

    def get_redirect_url(self):
        url = super().get_redirect_url()

        if url == "":
            url = reverse_lazy("timecard:dashboard")

        return url

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        # TODO デモ用 ログイン情報
        context["users"] = User.objects.all().order_by("-manager", "email")
        return context


class LogoutView(views.LogoutView):
    next_page = "accounts:login"

