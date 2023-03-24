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
class TimeCardExportView(TimeCardBaseMonthlyReportView, HandleExcelView):

    def get(self, request, *args, **kwargs):
        if self.request.GET.get('mode') == 'export':
            wb = self._create_wb()
            filename = 'タイムカード_' + self.EOM_by_url.strftime('%Y{0}%m{1}').format(*'年月') + '.xlsx'
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename={}'.format(urllib.parse.quote(filename))
            wb.save(response)

            return response

        return redirect(reverse('timecard:timecard_monthly_report'))

    def _create_wb(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.title = self.SHEET_TITLE

        self._write_ws(ws)
        self._edit_appearance_ws(ws)
        self._adjust_col_width_ws(ws)

        return wb

    def _write_ws(self, ws):
        self._write_header(ws)

        day_count = self.EOM_by_url.day
        monthly_stamps_qs = self.get_queryset()
        for day_index in range(day_count):
            day = day_index + 1
            target_date = self.EOM_by_url + relativedelta(day=day)

            dow = self._get_dow(day)
            day_kind = self._get_day_kind(dow, day)
            start_time, end_time, enter_break, end_break = self._get_daily_stamps_info(monthly_stamps_qs, day)
            holiday_name = jpholiday.is_holiday_name(target_date)

            ws.append([day, dow, day_kind, self._local_time(start_time), self._local_time(end_time),
                       self._local_time(enter_break), self._local_time(end_break), holiday_name])

    def _format(self, timedelta):
        if type(timedelta) == str:
            return timedelta

        pattern = r'((0?|1)[0-9]|2[0-3]):[0-5][0-9]'
        return re.compile(pattern).match(str(timedelta)).group()

    def _local_time(self, stamped_time):
        if stamped_time:
            return timezone.localtime(stamped_time).strftime('%H:%M')

        return ''

    def _write_header(self, ws):
        ws[self.TITLE_CELL] = self.SHEET_HEADLINE.format(self.EOM_by_url.strftime('%Y{0}%m{1}').format(*'年月'))
        ws[self.USER_NAME_CELL] = self.SHEET_USER_NAME.format(self.request.user.name)

        ws.append(self.SHEET_HEADER)


class TimeCardImportView(HandleExcelView):
    template_name = 'timecard/upload.html'
    logger = logging.getLogger(__name__)

    ERR_MSG_HEADER = 'エラー内容'
    ERR_MSG_CELL_FORMAT = 'フォーマットはHH:MMで入力してください。'


    def get(self, *args, **kwargs):
        return TemplateResponse(self.request, self.template_name, {'upload_form': self._get_upload_form()})

    def post(self, request, *args, **kwargs):
        self.toast_err_msg = None
        self.end_of_import_month = None

        upload_form = self._get_upload_form()
        if not (upload_form.is_valid()):
            return render(self.request, self.template_name, {'upload_form': upload_form})

        wb = openpyxl.load_workbook(self.request.FILES['file'])
        if self._is_valid_wb(wb):
            self._import_data_by_wb(wb)
            self.request.session['success'] = '{}の取込が成功しました'.format(
                self.end_of_import_month.strftime('%Y{0}%m{1}').format(*'年月'))

            return redirect(
                reverse('timecard:timecard_monthly_report') + '?month=' + self.end_of_import_month.strftime('%Y%m'))

        if self.toast_err_msg:
            self.request.session['error'] = self.toast_err_msg
            return redirect(reverse('timecard:timecard_monthly_report'))

        err_response = self._create_err_response(wb)
        return err_response

    def _get_upload_form(self):
        kwargs = {}
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
            kwargs['files'] = self.request.FILES

        return UploadFileForm(**kwargs)

    def _is_valid_wb(self, wb):
        self.toast_err_msg = None
        self.end_of_import_month = None
        self.err_msg_ws = {}

        try:
            ws = wb[self.SHEET_TITLE]
            if not self.is_valid_ws_format(ws):
                return

            if self.exist_promoted_db_stamps():
                self.toast_err_msg = '{}および{}の情報は更新できません'.format(TimeCard.State.PROCESSING.label,
                                                                     TimeCard.State.APPROVED.label)
                return

            self._reset_color_cells(ws)
            self._set_err_msg_col(ws)

            return self.is_valid_ws_stamps(ws)

        except Exception as e:
            self.toast_err_msg = '取込失敗しました'
            self.logger.error(f'{e}', exc_info=True)
            return

    def _validate_ws_stamps(self, ws, day_count):
        empty_row_count = 0
        valid_row_count = 0
        # 1日の行から末日の行までループする
        for row_num in range(self.HEADER_ROW_NUM + 1, ws.max_row + 1):
            row = ws[row_num]
            max_col_index = ws.max_column - 1
            err_msg_write_cell = row[max_col_index]

            start_work_cell = row[self.START_WORK_COL_NUM - 1]
            end_work_cell = row[self.END_WORK_COL_NUM - 1]
            enter_break_cell = row[self.ENTER_BREAK_COL_NUM - 1]
            end_break_cell = row[self.END_BREAK_COL_NUM - 1]

            start_work = self._validate_format(start_work_cell.value)
            end_work = self._validate_format(end_work_cell.value)
            enter_break = self._validate_format(enter_break_cell.value)
            end_break = self._validate_format(end_break_cell.value)

            if start_work is end_work is enter_break is end_break is None:
                empty_row_count += 1
                continue

            if False in [start_work, end_work, enter_break ,end_break]:
                err_msg = self.ERR_MSG_CELL_FORMAT
                err_cells = [cell for cell in [start_work_cell, end_work_cell, enter_break_cell, end_break_cell]
                             if self._validate_format(cell.value) == False]
                self._write_err_msg_cell(err_msg, err_msg_write_cell, *err_cells)
                continue

            if start_work or end_work:
                if not (start_work and end_work):
                    err_msg = TimeCardFormSet.ERR_MSG_NEED_WORK_TIME
                    self._write_err_msg_cell(err_msg, err_msg_write_cell, start_work_cell, end_work_cell)
                    continue

                elif end_work < start_work:
                    err_msg = TimeCardFormSet.ERR_MSG_WORK_TIME
                    self._write_err_msg_cell(err_msg, err_msg_write_cell, start_work_cell, end_work_cell)
                    continue

            if enter_break or end_break:
                if not (start_work and end_work):
                    err_msg = TimeCardFormSet.ERR_MSG_NEED_WORK_TIME_BY_BREAK_TIME
                    self._write_err_msg_cell(err_msg, err_msg_write_cell, start_work_cell, end_work_cell)
                    continue

                if not (enter_break and end_break):
                    err_msg = TimeCardFormSet.ERR_MSG_NEED_BREAK_TIME
                    self._write_err_msg_cell(err_msg, err_msg_write_cell, enter_break_cell, end_break_cell)
                    continue

                elif end_break < enter_break:
                    err_msg = TimeCardFormSet.ERR_MSG_BREAK_TIME
                    self._write_err_msg_cell(err_msg, err_msg_write_cell, enter_break_cell, end_break_cell)
                    continue

                if enter_break < start_work or end_work < end_break:
                    err_msg = TimeCardFormSet.ERR_MSG_BREAK_TIME_OUT_OF_RANGE
                    self._write_err_msg_cell(err_msg, err_msg_write_cell, enter_break_cell, end_break_cell)
                    continue

            valid_row_count += 1

        is_empty_ws = (day_count == empty_row_count)
        is_valid_ws = (day_count == valid_row_count)

        return is_empty_ws, is_valid_ws

    def _reset_color_cells(self, ws):
        for col in ws.columns:
            if col[0].column <= self.DAY_KIND_COL_NUM:
                # '日付'、'曜日'、'区分'の列の色は変更しない
                continue

            for cell in col:
                cell.fill = PatternFill(fgColor=self.WHITE)

    def _set_err_msg_col(self, ws):
        ws.delete_cols(self.ERR_MSG_COL_NUM)
        ws.cell(row=self.HEADER_ROW_NUM, column=self.ERR_MSG_COL_NUM).value = self.ERR_MSG_HEADER
        ws.cell(row=self.HEADER_ROW_NUM, column=self.ERR_MSG_COL_NUM).font = Font(name=self.FONT_NAME, size=9)

    def _write_err_msg_cell(self, err_msg, err_msg_cell, *err_cells):
        err_msg_cell.value = err_msg
        err_msg_cell.font = Font(name=self.FONT_NAME, size=9)
        for err_cell in err_cells:
            err_cell.fill = PatternFill(patternType='solid', fgColor=self.YELLOW)

    def _write_borders_ws(self, ws):
        side = Side(style='thin', color=self.BLACK)
        for row in ws:
            row_num = row[0].row

            if row_num < self.HEADER_ROW_NUM:
                continue

            # ヘッダーから末日の行までループする
            for cell in row:
                ws[cell.coordinate].border = Border(top=side, bottom=side, left=side, right=side)
                ws[cell.coordinate].alignment = Alignment(horizontal='center', vertical='center', wrapText=True)

    def _validate_format(self, cell_value):
        if not cell_value:
            return

        try:
            if type(cell_value) == time:
                return cell_value
            return datetime.strptime(cell_value, "%H:%M").time()

        except:
            return False

    def _get_import_month_by_ws(self, ws):
        value = ws[self.TITLE_CELL].value[6:]
        month_str = value.replace('年', '').replace('月', '') + '01'
        return datetime.strptime(month_str, '%Y%m%d').astimezone(timezone.get_default_timezone())

    @transaction.non_atomic_requests
    def _import_data_by_wb(self, wb):
        try:
            ws = wb[self.SHEET_TITLE]

class TimeCardEditView(TemplateView):
    template_name = 'timecard/form.html'
    url = reverse_lazy('timecard:timecard_monthly_report')
            self._get_queryset_by_db().delete()

            # 1日の行から末日の行までループする
            stamp_list = []
            for row_num in range(self.HEADER_ROW_NUM + 1, ws.max_row + 1):
                row = ws[row_num]
                day = row[0].value

                stamped_date = self.end_of_import_month+ relativedelta(day=day)
                col_num_kind = {self.START_WORK_COL_NUM: TimeCard.Kind.IN,
                                self.END_WORK_COL_NUM: TimeCard.Kind.OUT,
                                self.ENTER_BREAK_COL_NUM: TimeCard.Kind.ENTER_BREAK,
                                self.END_BREAK_COL_NUM: TimeCard.Kind.END_BREAK}

                for col_num in col_num_kind:
                    cell_value = row[col_num - 1].value

                    if cell_value:
                        stamp_kind = col_num_kind[col_num]
                        stamped_time = self._get_stamped_time_by_cell(stamped_date, cell_value)
                        stamp_list.append([stamp_kind, stamped_time])

            if stamp_list:
                for stamp in stamp_list:
                    TimeCard.objects.create(kind=stamp[0], stamped_time=stamp[1], user=self.request.user)

        except Exception as e:
            self.logger.error(f'{e}', exc_info=True)

    def _get_stamped_time_by_cell(self, stamped_day, cell_value):
        if type(cell_value) != time:
            cell_value = datetime.strptime(cell_value, "%H:%M").time()
        return stamped_day + relativedelta(hours=cell_value.hour, minutes=cell_value.minute)

    def _create_err_response(self, wb):
        ws = wb[self.SHEET_TITLE]
        self._edit_appearance_ws(ws)
        self._adjust_col_width_ws(ws)

        filename = 'エラーレポート_' + timezone.datetime.now().strftime('%Y%m%d%H%M') + '.xlsx'
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename={}'.format(urllib.parse.quote(filename))
        wb.save(response)

        return response

    def is_valid_ws_format(self, ws):
        next_month = timezone.datetime.today().astimezone(timezone.get_default_timezone()).replace(
            hour=0, minute=0, second=0, microsecond=0) + relativedelta(day=1, months=1)
        import_month_by_ws = self._get_import_month_by_ws(ws)
        user_name = ws[self.USER_NAME_CELL].value[3:]

        if import_month_by_ws >= next_month:
            self.toast_err_msg = '来月以降の情報は、取込できません'
            return

        if user_name != self.request.user.name:
            self.toast_err_msg = '不正なシートのため、取込できません'
            return

        self.end_of_import_month = import_month_by_ws + relativedelta(months=1, day=1) - relativedelta(days=1)
        day_count_by_ws = ws.cell(row=ws.max_row, column=1).value

        # シートの月末日が正しいかチェックする
        if self.end_of_import_month.day != day_count_by_ws:
            self.toast_err_msg = '不正なシートのため、取込できません'
            return

        return self.toast_err_msg == None

    def exist_promoted_db_stamps(self):
        db_monthly_stamps = self._get_queryset_by_db()
        return db_monthly_stamps.exclude(state=TimeCard.State.NEW).exists()

    def _get_queryset_by_db(self):
        monthly_stamps_qs = TimeCard.objects.filter(stamped_time__gte=(self.end_of_import_month + relativedelta(day=1)),
                                                    stamped_time__lt=(self.end_of_import_month + relativedelta(months=1, day=1)),
                                                    user=self.request.user)
        return monthly_stamps_qs

    def is_valid_ws_stamps(self, ws):
        day_count = self.end_of_import_month.day

        is_empty_ws, is_valid_ws = self._validate_ws_stamps(ws, day_count)

        if is_empty_ws:
            # 未入力の場合、取込した月の情報が全て削除されるためエラーにする
            self.toast_err_msg = '未入力のため、取込できません'
            return

        return is_valid_ws

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
