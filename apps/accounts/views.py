from django.contrib.auth import views
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy

from apps.accounts.form import LoginForm, PasswordResetForm, SetPasswordForm
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
        #TODO デモ用 ログイン情報
        context['users'] = User.objects.all().order_by('-manager', 'email')
        return context


class LogoutView(views.LogoutView):
    next_page = "accounts:login"


class PasswordResetView(views.PasswordResetView):
    template_name = "pw_reset/form.html"
    email_template_name = "pw_reset/email.html"
    success_url = reverse_lazy("accounts:pw_reset_done")
    subject_template_name = "pw_reset/email_subject.txt"
    form_class = PasswordResetForm

    def post(self, request, *args, **kwargs):
        request.session["reset_email"] = request.POST["email"]
        super().post(self, request, *args, **kwargs)

        return HttpResponseRedirect(self.success_url)


class PasswordResetDoneView(views.PasswordResetDoneView):
    template_name = "pw_reset/done.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["reset_email"] = self.request.session.get("reset_email")

        return context_data


class PasswordResetConfirmView(views.PasswordResetConfirmView):
    template_name = "pw_reset/confirm.html"
    form_class = SetPasswordForm
    success_url = reverse_lazy("accounts:pw_reset_complete")


class PasswordResetCompleteView(views.PasswordResetCompleteView):
    template_name = "pw_reset/complete.html"
