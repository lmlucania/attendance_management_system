from django.shortcuts import redirect
from django.utils import timezone
from django.urls import reverse
from dateutil.relativedelta import relativedelta

from .base import TemplateView
from apps.timecard.models import TimeCard


class DashboardView(TemplateView):
    template_name = 'dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        self.today = timezone.datetime.today().astimezone(timezone.get_default_timezone()).replace(
            hour=0, minute=0, second=0, microsecond=0)
        self.is_promoted = TimeCard.objects.filter(stamped_time__gte=self.today + relativedelta(day=1),
                                                   stamped_time__lt=self.today + relativedelta(
                                                       months=1, day=1) - relativedelta(days=1),
                                                   user=self.request.user).exclude(state=TimeCard.State.NEW).exists()

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        if 'mode' not in self.request.POST:
            return super().get(request, *args, **kwargs)

        if self.is_promoted:
            self.request.session['error'] = '締め処理後のため、打刻できません'
            return super().get(request, *args, **kwargs)

        stamping_kind = self._convert_stamping_kind(self.request.POST['mode'])
        if not self._is_stamped_today(stamping_kind):
            TimeCard.objects.create(user=self.request.user, kind=stamping_kind)

        return redirect(reverse('timecard:dashboard'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_promoted'] = self.is_promoted
        context['btn_in_attr'] = self._get_btn_attr(TimeCard.Kind.IN)
        context['btn_out_attr'] = self._get_btn_attr(TimeCard.Kind.OUT)
        context['btn_enter_break_attr'] = self._get_btn_attr(TimeCard.Kind.ENTER_BREAK)
        context['btn_end_break_attr'] = self._get_btn_attr(TimeCard.Kind.END_BREAK)

        return context

    def _convert_stamping_kind(self, mode):
        try:
            return TimeCard.Kind[mode.upper()]

        except:
            return

    def _is_stamped_today(self, stamping_kind):
        today_qs = TimeCard.objects.filter(user=self.request.user, stamped_time__gte=self.today,
                                           stamped_time__lt=self.today + relativedelta(days=1))

        return today_qs.filter(kind=stamping_kind).exists()

    def _get_btn_attr(self, stamped_kind):
        if self.is_promoted or self._is_stamped_today(stamped_kind):
            return 'disabled'
