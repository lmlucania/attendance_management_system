from datetime import timedelta

from django.shortcuts import redirect
from django.utils import timezone
from django.urls import reverse
from dateutil.relativedelta import relativedelta

from .base import TemplateView, get_work_days_by_qs, get_daily_stamps_info, calculation_hours_daily, timedelta2str
from apps.timecard.models import TimeCard, TimeCardSummary


class DashboardView(TemplateView):
    # template_name = 'dashboard.html'
    template_name = 'material-dashboard-master/pages/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        self.today = timezone.datetime.today().astimezone(timezone.get_default_timezone()).replace(
            hour=0, minute=0, second=0, microsecond=0)
        self.is_promoted = TimeCard.objects.filter(stamped_time__gte=self.today + relativedelta(day=1),
                                                   stamped_time__lt=self.today + relativedelta(
                                                       months=1, day=1) - relativedelta(days=1),
                                                   user=request.user).exclude(state=TimeCard.State.NEW).exists()

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        if 'mode' not in request.GET:
            return super().get(request, *args, **kwargs)

        if self.is_promoted:
            request.session['error'] = '締め処理後のため打刻できません'
            return redirect(reverse('timecard:dashboard'))

        stamping_kind = self._convert_stamping_kind(request.GET['mode'])
        if not self._stamped_time_today(stamping_kind):
            TimeCard.objects.create(user=request.user, kind=stamping_kind)

        return redirect(reverse('timecard:dashboard'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_promoted'] = self.is_promoted
        context['stamped_time'] = self._get_stamped_time()
        context['bar_chart_data'] = self._get_bar_chart_data()
        context['line_graph_data'] = self._get_line_graph_data()

        return context

    def _convert_stamping_kind(self, mode):
        try:
            return TimeCard.Kind[mode.upper()]

        except:
            return

    def _stamped_time_today(self, stamping_kind):
        today_qs = TimeCard.objects.filter(user=self.request.user, kind=stamping_kind, stamped_time__gte=self.today,
                                           stamped_time__lt=self.today + relativedelta(days=1))
        if not today_qs.exists():
            return

        return today_qs.first().stamped_time

    def _get_stamped_time(self):
        stamped_kind_dict = {TimeCard.Kind.IN: None, TimeCard.Kind.OUT: None, TimeCard.Kind.ENTER_BREAK: None,
                             TimeCard.Kind.END_BREAK: None}

        for stamped_kind in stamped_kind_dict.keys():
            if self.is_promoted or self._stamped_time_today(stamped_kind):
                stamped_kind_dict[stamped_kind] = self._stamped_time_today(stamped_kind)

        return stamped_kind_dict

    def _get_bar_chart_data(self):
        work_hour_data = [0] * 7

        DOW_int = self.today.isoweekday()
        this_monday = self.today - relativedelta(days=DOW_int - 1)
        this_sunday = this_monday + relativedelta(days=6)
        this_week_stamps_qs = TimeCard.objects.filter(user=self.request.user, stamped_time__gte=this_monday,
                                                      stamped_time__lte=this_sunday)
        work_days = get_work_days_by_qs(this_week_stamps_qs)
        bar_chart_latest_updated_at = \
            this_week_stamps_qs.order_by('-updated_at').first().updated_at if work_days != [] else None

        for day in work_days:
            work_date = self.today + relativedelta(day=day)
            DOW_index = work_date.isoweekday() - 1

            start_work, end_work, enter_break, end_break = get_daily_stamps_info(this_week_stamps_qs, work_date)
            work_hours, break_hours = calculation_hours_daily(start_work, end_work, enter_break, end_break)
            work_hour_data[DOW_index] = float('{:.2f}'.format(work_hours.seconds / (60 * 60)))

        return {'work_hour': work_hour_data, 'this_monday': this_monday, 'this_sunday': this_sunday,
                'latest_updated_at': bar_chart_latest_updated_at}

    def _past_6months_YM(self):
        today = timezone.datetime.today()
        months_list = []
        for index in range(6):
            display_month_YM = (today - relativedelta(months=index)).strftime('%Y/%m')
            months_list.append(display_month_YM)

        return months_list

    def _get_line_graph_data(self):
        self.line_graph_latest_updated_at = None
        months_YM_list = self._past_6months_YM()
        graph_data = {}
        for month_YM in months_YM_list:
            graph_data[month_YM] = self._get_total_work_hours(month_YM)

        total_work_hour_list = [hours for hours in graph_data.values()]

        return {'months': ', '.join(map(str, sorted([month for month in graph_data.keys()]))),
                'total_work_hours': total_work_hour_list[::-1], 'latest_updated_at': self.line_graph_latest_updated_at}

    def _get_total_work_hours(self, month):
        obj = TimeCardSummary.objects.filter(user=self.request.user, month=month).first()
        if obj:
            if not self.line_graph_latest_updated_at or self.line_graph_latest_updated_at < obj.updated_at:
                self.line_graph_latest_updated_at = obj.updated_at

            return float(obj.total_work_hours)

        month_first_date = \
            timezone.datetime.strptime(month + '/01', "%Y/%m/%d").astimezone(timezone.get_default_timezone())
        monthly_stamps_qs = self._get_monthly_stamps_qs(month_first_date)
        if monthly_stamps_qs.exists():
            if not self.line_graph_latest_updated_at or \
                    self.line_graph_latest_updated_at < monthly_stamps_qs.order_by('-updated_at').first().updated_at:
                self.line_graph_latest_updated_at = monthly_stamps_qs.order_by('-updated_at').first().updated_at

            total_work_hours_str = self._get_total_work_hours_by_qs(monthly_stamps_qs, month_first_date)
            return float(total_work_hours_str)

        return 0

    def _get_monthly_stamps_qs(self, month_first_date):
        return TimeCard.objects.filter(
            user=self.request.user, stamped_time__gte=month_first_date,
            stamped_time__lt=month_first_date + relativedelta(months=1, day=1) - relativedelta(days=1)
        )

    def _get_total_work_hours_by_qs(self, monthly_stamps_qs, month_first_date) -> str:
        work_days = get_work_days_by_qs(monthly_stamps_qs)

        total_work_hours = timedelta()
        for day in work_days:
            work_date = month_first_date + relativedelta(day=day)

            start_work, end_work, enter_break, end_break = get_daily_stamps_info(monthly_stamps_qs, work_date)
            work_hours, break_hours = calculation_hours_daily(start_work, end_work, enter_break, end_break)
            total_work_hours += work_hours

        return timedelta2str(total_work_hours)
