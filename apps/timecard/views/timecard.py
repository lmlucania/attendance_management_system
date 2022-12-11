import urllib
import re

import openpyxl
import jpholiday
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from dateutil.relativedelta import relativedelta
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from .base import ListView, TemplateView
from apps.timecard.models import TimeCard
from apps.timecard.forms import TimeCardSearchForm, TimeCardFormSet


class TimeCardListView(ListView):
    model = TimeCard
    search_form = TimeCardSearchForm

    def get(self, request, *args, **kwargs):
        self.target_date = self._get_target_date(request)

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
            return queryset.filter(stamped_time__gte=(self.target_date + relativedelta(day=day)),
                                   stamped_time__lt=(self.target_date + relativedelta(day=day) + relativedelta(days=1)))

        return queryset

    def get_context_data(self, **kwargs):
        context = dict()
        context['monthly_report'] = self._summary_monthly_report()
        context['search_form'] = self.search_form(month=self.target_date)
        context['next_month'] = (self.target_date + relativedelta(months=1)).strftime('%Y%m')
        context['last_month'] = (self.target_date - relativedelta(months=1)).strftime('%Y%m')
        context['first_day'] = self.target_date + relativedelta(day=1)
        context['last_day'] = self.target_date
        return context

    def _get_target_date(self, request):
        target_date = timezone.datetime.today().astimezone(timezone.get_default_timezone()).date()
        param = request.GET.get('month')
        if param:
            try:
                target_date = timezone.datetime.strptime(param + '01', "%Y%m%d").date()
            except:
                pass

        last_day_target_date = target_date + relativedelta(months=1, day=1) - relativedelta(days=1)
        return last_day_target_date

    def _summary_monthly_report(self):
        last_day = self.target_date.day
        monthly_report = []
        for day in range(1, last_day+1):
            start_time, end_time, work_hour = self._get_stamped_info(day)
            monthly_report.append({'day': day, 'start_time': start_time, 'end_time': end_time, 'work_hour': work_hour})

        return monthly_report

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
        start_obj = day_queryset.filter(kind=TimeCard.Kind.IN).first()
        end_obj = day_queryset.filter(kind=TimeCard.Kind.OUT).first()

        start_time = timezone.localtime(start_obj.stamped_time).strftime('%H:%M') if start_obj else ''
        end_time = timezone.localtime(end_obj.stamped_time).strftime('%H:%M') if end_obj else ''
        work_hour = timezone.localtime(end_obj.stamped_time) - timezone.localtime(start_obj.stamped_time) \
            if start_obj and end_obj else ''

        return start_time, end_time, self._format(work_hour)

    def _format(self, timedelta):
        if type(timedelta) == str:
            return timedelta

        pattern = r'((0?|1)[0-9]|2[0-3]):[0-5][0-9]'
        return re.compile(pattern).match(str(timedelta)).group()

    def _write_header(self, ws):
        ws['A2'] = '勤務報告書' + '　' + self.target_date.strftime('%Y{0}%m{1}').format(*'年月')
        ws['A4'] = '氏名' + '　' + self.request.user.name

        ws.append(['日付', '曜日', '出勤時刻', '退勤時刻', '', '', '勤務時間', '備考'])

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


class TimeCardEditView(TemplateView):
    template_name = 'timecard/form.html'
    url = reverse_lazy('timecard:timecard_monthly_report')

    def dispatch(self, request, *args, **kwargs):
        if not self._get_target_date(request):
            return redirect(reverse('timecard:timecard_monthly_report'))

        self.target_date = self._get_target_date(request)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        formset = TimeCardFormSet(request.POST)
        if formset.is_valid():
            # TODO 保存時に日付を修正日付にするように指定する
            for form in formset:
                if form.changed_data != {}:
                    form.instance.user = request.user
            formset.save()
            return redirect(reverse('timecard:timecard_monthly_report'))

        context = dict()
        context['formset'] = formset
        context['sorted_formset'] = self._sort_formset(formset)
        return render(request, self.template_name, context)

    def _get_target_date(self, request):
        target_date = ''
        today = timezone.datetime.today().astimezone(timezone.get_default_timezone()).date()
        param = request.GET.get('date')
        if param:
            try:
                if timezone.datetime.strptime(param, "%Y%m%d").date() <= today:
                    target_date = timezone.datetime.strptime(param, "%Y%m%d").date()
            except:
                pass

        return target_date

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO 時間のみ入力できる様に修正
        # TODO formsetのままテンプレートに渡して、リストから取得するようにしたい
        formset = TimeCardFormSet(date=self.target_date, user=self.request.user)
        context['formset'] = formset
        context['sorted_formset'] = self._sort_formset(formset)
        return context

    def _get_formset_display_list(self, formset):
        display_list = []
        extra_form_index = len(formset.forms) - len(formset.extra_forms)
        formset_kind_list = [form.initial['kind'] if form.instance.id else '' for form in formset]
        order_kind_list = [TimeCard.Kind.IN, TimeCard.Kind.OUT, TimeCard.Kind.ENTER_BREAK, TimeCard.Kind.END_BREAK]
        for order_kind in order_kind_list:
            try:
                index = formset_kind_list.index(order_kind)
            except ValueError:
                index = extra_form_index
                extra_form_index += 1
            display_list.append(formset[index])

        return display_list

    def _sort_formset(self, formset):
        formset_dict = {form.initial['kind']: form for form in formset if form.instance.id}
        order_kind_list = [TimeCard.Kind.IN, TimeCard.Kind.OUT, TimeCard.Kind.ENTER_BREAK, TimeCard.Kind.END_BREAK]

        extra_form_index = 0
        for index, order_kind in enumerate(order_kind_list):
            if formset_dict.get(order_kind):
                order_kind_list[index] = formset_dict[order_kind]
            else:
                formset.extra_forms[extra_form_index].initial['kind'] = order_kind
                order_kind_list[index] = formset.extra_forms[extra_form_index]
                extra_form_index += 1

        return order_kind_list
