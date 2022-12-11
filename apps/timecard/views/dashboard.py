from django.shortcuts import redirect
from django.utils import timezone
from django.urls import reverse
from dateutil.relativedelta import relativedelta

from .base import TemplateView
from apps.timecard.models import TimeCard


class DashboardView(TemplateView):
    template_name = 'dashboard.html'

    def post(self, request, *args, **kwargs):

        if 'mode' not in self.request.POST:
            return super().get(request, *args, **kwargs)

        stamping_kind = self._validate_stamping(self._convert_stamping_kind(self.request.POST['mode']))
        if stamping_kind:
            TimeCard.objects.create(user=self.request.user, kind=stamping_kind)

        return redirect(reverse('timecard:dashboard'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['can_click_in'] = ''
        # context['can_click_reset'] = 'disabled'
        #
        # if self._latest_record_stamping_kind() == TimeCard.Kind.IN:
        #     context['can_click_in'] = 'disabled'
        #     context['can_click_reset'] = ''

        return context

    def _convert_stamping_kind(self, mode):
        if type(mode) != str:
            return

        try:
            return TimeCard.Kind[mode.upper()]

        except KeyError:
            return

    def _validate_stamping(self, stamping_kind):
        today = timezone.datetime.today().astimezone(timezone.get_default_timezone()).date()
        today_query = TimeCard.objects.filter(user=self.request.user, stamped_time__gte=today,
                                              stamped_time__lt=today + relativedelta(days=1))
        if today_query.filter(kind=stamping_kind).exists():
            return

        if stamping_kind == TimeCard.Kind.OUT:
            return today_query.filter(kind=TimeCard.Kind.IN).exists()

        return stamping_kind
