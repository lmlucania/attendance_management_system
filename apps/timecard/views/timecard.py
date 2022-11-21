import urllib
import re

import openpyxl
import jpholiday
from django.http import HttpResponse
from django.utils import timezone
from django.urls import reverse_lazy
from dateutil.relativedelta import relativedelta
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from .base import ListView, CreateView, UpdateView, DeleteView
from apps.timecard.models import TimeCard
from apps.timecard.forms import TimeCardForm, TimeCardSearchForm


class TimeCardListView(ListView):
    model = TimeCard
    search_form = TimeCardSearchForm

    def get(self, request, *args, **kwargs):
        self.target_date = self.get_target_date(request)

        if self.request.GET.get('mode') == 'export':
            wb = self._create_wb()
            filename = 'タイムカード_' + self.target_date.strftime('%Y{0}%m{1}').format(*'年月') + '.xlsx'
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename={}'.format(urllib.parse.quote(filename))
            wb.save(response)
            return response

        return super().get(request, *args, **kwargs)

    def get_queryset(self, day=None):
        queryset = TimeCard.objects.filter(stamped_time__gte=(self.target_date + relativedelta(day=1)),
                                           stamped_time__lt=(self.target_date + relativedelta(months=1, day=1)),
                                           user=self.request.user).order_by('stamped_time', 'kind')
        if day:
            queryset = queryset.filter(stamped_time__gte=(self.target_date + relativedelta(day=day)),
                                       stamped_time__lt=(
                                               self.target_date + relativedelta(day=day) + relativedelta(days=1)))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['search_form'] = self.search_form(month=self.target_date)
        context['next_month'] = (self.target_date + relativedelta(months=1)).strftime('%Y-%m')
        context['last_month'] = (self.target_date - relativedelta(months=1)).strftime('%Y-%m')
        context['first_day'] = self.target_date + relativedelta(day=1)
        context['last_day'] = self.target_date
        return context

    def get_target_date(self, request):
        target_date = timezone.datetime.today().astimezone(timezone.get_default_timezone()).date()
        param = request.GET.get('month')
        if param:
            try:
                target_date = timezone.datetime.strptime(param + '-01', "%Y-%m-%d").date()
            except:
                pass

        last_day_target_date = target_date + relativedelta(months=1, day=1) - relativedelta(days=1)
        return last_day_target_date

    def _create_wb(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.title = '勤務一覧'

        self._write_ws(ws)
        self._edit_appearance_ws(ws)
        self._adjust_width_ws(ws)

        return wb

    def _write_ws(self, ws):
        self._write_header(ws)

        last_day = self.target_date.day
        for day in range(1, last_day + 1):
            dow = self._get_dow(day)
            start_time, end_time, work_hour = self._get_stamped_info(day)
            holiday_name = jpholiday.is_holiday_name(self.target_date + relativedelta(day=day))

            ws.append([day, dow, start_time, end_time, work_hour, holiday_name])

    def _get_dow(self, day):
        week = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}
        dow_int = (self.target_date + relativedelta(day=day)).isoweekday()
        return week[dow_int]

    def _get_stamped_info(self, day):
        day_queryset = self.get_queryset(day)
        start_query = day_queryset.filter(kind=TimeCard.Kind.IN)
        end_query = day_queryset.filter(kind=TimeCard.Kind.OUT)

        start_time = self._get_localtime(start_query).strftime('%H:%M') if start_query else ''
        end_time = self._get_localtime(end_query).strftime('%H:%M') if end_query else ''
        work_hour = self._get_localtime(end_query) - self._get_localtime(start_query) \
            if start_query and end_query else ''

        return start_time, end_time, self._format(work_hour)

    def _format(self, timedelta):
        if type(timedelta) == str:
            return timedelta

        pattern = r'((0?|1)[0-9]|2[0-3]):[0-5][0-9]'
        return re.compile(pattern).match(str(timedelta)).group()

    def _get_localtime(self, query):
        utc_time = query.values_list('stamped_time', flat=True)[0]
        return timezone.localtime(utc_time)

    def _write_header(self, ws):
        ws['A2'] = '勤務報告書' + '　' + self.target_date.strftime('%Y{0}%m{1}').format(*'年月')
        ws['A4'] = '氏名' + '　' + self.request.user.name

        ws.append(['日付', '曜日', '出勤時刻', '退勤時刻', '勤務時間', '備考'])

    def _edit_appearance_ws(self, ws):
        side = Side(style='thin', color='000000')
        fill_grey = PatternFill(patternType='solid', fgColor='d0d0d0')
        for row in ws:
            for cell in row:
                ws[cell.coordinate].font = Font(name='游ゴシック', size=9)

                if type(cell.value) == str and '勤務報告書' in cell.value:
                    ws[cell.coordinate].font = Font(name='游ゴシック', size=12)
                    ws.row_dimensions[cell.row].height = 20

                if cell.row <= 4:
                    continue

                ws[cell.coordinate].border = Border(top=side, bottom=side, left=side, right=side)
                ws[cell.coordinate].alignment = Alignment(horizontal='center', vertical='center', wrapText=True)

                if cell.value == '土' or cell.value == '日' or self._is_holiday(cell):
                    ws[ws.cell(row=cell.row, column=1).coordinate].fill = fill_grey
                    ws[ws.cell(row=cell.row, column=2).coordinate].fill = fill_grey

    def _is_holiday(self, cell):
        if type(cell.value) == int:
            return jpholiday.is_holiday_name(self.target_date + relativedelta(day=cell.value))

    def _adjust_width_ws(self, ws):
        for column in ws.columns:
            column_letter = column[0].column_letter
            max_char_length = max([len(str(cell.value)) for cell in column[4:] if cell.value])

            ws.column_dimensions[column_letter].width = max_char_length * 1.5 + 2


class TimeCardCreateView(CreateView):
    model = TimeCard
    form_class = TimeCardForm
    success_url = reverse_lazy('timecard:timecard_monthly_report')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TimeCardUpdateView(UpdateView):
    model = TimeCard
    form_class = TimeCardForm
    success_url = reverse_lazy('timecard:timecard_monthly_report')


class TimeCardDeleteView(DeleteView):
    model = TimeCard
    form_class = TimeCardForm
    success_url = reverse_lazy('timecard:timecard_monthly_report')
