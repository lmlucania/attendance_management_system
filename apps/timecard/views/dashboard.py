from django.shortcuts import redirect
from django.urls import reverse

from .base import TemplateView
from apps.timecard.models import TimeCard


class DashboardView(TemplateView):
    template_name = 'dashboard.html'

    def post(self, request, *args, **kwargs):

        if 'mode' not in self.request.POST:
            return super().get(request, *args, **kwargs)

        stamping_kind = self._validate_double_stamping(self._convert_stamping_kind(self.request.POST['mode']))
        if stamping_kind:
            TimeCard.objects.create(user=self.request.user, kind=stamping_kind)

        return redirect(reverse('timecard:dashboard'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_click_in'] = ''
        context['can_click_reset'] = 'disabled'

        if self._latest_record_stamping_kind() == TimeCard.Kind.IN:
            context['can_click_in'] = 'disabled'
            context['can_click_reset'] = ''

        return context

    def _latest_record_stamping_kind(self):
        if not TimeCard.objects.filter(user=self.request.user).exists():
            return

        return TimeCard.objects.filter(user=self.request.user).latest('created_at').kind

    def _convert_stamping_kind(self, mode):
        stamping_kind = TimeCard.Kind.LEAVE
        if mode == 'in':
            stamping_kind = TimeCard.Kind.IN

        elif mode == 'out':
            stamping_kind = TimeCard.Kind.OUT

        return stamping_kind

    def _validate_double_stamping(self, stamping_kind):
        if self._latest_record_stamping_kind() != stamping_kind:
            return stamping_kind

        if stamping_kind == TimeCard.Kind.LEAVE:
            return

        elif stamping_kind == TimeCard.Kind.IN:
            return TimeCard.Kind.LEAVE
