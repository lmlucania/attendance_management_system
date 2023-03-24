import logging
import urllib
import re
from datetime import datetime, time

from django.db import transaction
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView
from dateutil.relativedelta import relativedelta
import jpholiday
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from .base import TemplateView, SuperuserPermissionView, TimeCardBaseMonthlyReportView, HandleExcelView
from apps.timecard.models import TimeCard
from apps.accounts.models import User
from apps.timecard.forms import TimeCardSearchForm, TimeCardFormSet, UploadFileForm


class TimeCardMonthlyReportView(TimeCardBaseMonthlyReportView):
    template_name = 'timecard/monthly_report.html'
    err_url = reverse_lazy('timecard:timecard_monthly_report')

    def get_context_data(self):
        context = super().get_context_data()
        context['search_form'] = self._get_search_form()

        return context

    def _get_search_form(self):
        kwargs = {}
        kwargs['initial'] = {'month': self.EOM_by_url.strftime('%Y-%m')}
        return TimeCardSearchForm(**kwargs)

    def _promote_process(self):
        url = reverse('timecard:timecard_monthly_report') + '?month=' + self.EOM_by_url.strftime('%Y%m')
        monthly_stamps_qs = self.get_queryset()

        if not monthly_stamps_qs.exists():
            self.request.session['warning'] = '未打刻のため申請できません'
            return redirect(self.err_url)
        elif monthly_stamps_qs.exclude(state=TimeCard.State.NEW):
            self.request.session['error'] = 'すでに申請済みです'
            return redirect(self.err_url)

        if self._validate_err_db_stamps(monthly_stamps_qs):
            monthly_stamps_qs.update(state=TimeCard.State.PROCESSING)
            self.request.session['success'] = 'ステータスを{}に更新しました'.format(TimeCard.State.PROCESSING.label)
            return redirect(url)

        # TODO 締め処理失敗時にレンダリング処理を実装する
        self.request.session['error'] = 'ステータス更新に失敗しました'
        return redirect(url)

    def _validate_err_db_stamps(self, monthly_stamps_qs):
        self.err_dict = {}

        work_days_list = self._get_work_days_by_qs(monthly_stamps_qs)

        for work_day in work_days_list:
            start_work, end_work, enter_break, end_break = self._get_daily_stamps_info(monthly_stamps_qs, work_day)

            if start_work or end_work:
                if not (start_work and end_work):
                    self.err_dict[work_day] = TimeCardFormSet.ERR_MSG_NEED_WORK_TIME
                    continue

                elif end_work < start_work:
                    self.err_dict[work_day] = TimeCardFormSet.ERR_MSG_WORK_TIME
                    continue

            if enter_break or end_break:
                if not (start_work and end_work):
                    self.err_dict[work_day] = TimeCardFormSet.ERR_MSG_NEED_WORK_TIME_BY_BREAK_TIME
                    continue

                if not (enter_break and end_break):
                    self.err_dict[work_day] = TimeCardFormSet.ERR_MSG_NEED_BREAK_TIME
                    continue

                elif end_break < enter_break:
                    self.err_dict[work_day] = TimeCardFormSet.ERR_MSG_BREAK_TIME
                    continue

                if enter_break < start_work or end_work < end_break:
                    self.err_dict[work_day] = TimeCardFormSet.ERR_MSG_BREAK_TIME_OUT_OF_RANGE
                    continue

        return self.err_dict == {}


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

class TimeCardEditView(TemplateView):
    template_name = 'timecard/form.html'
    FORMSET_ORDER_KIND_DISPLAY = [TimeCard.Kind.IN, TimeCard.Kind.OUT, TimeCard.Kind.ENTER_BREAK, TimeCard.Kind.END_BREAK]
    FORMSET_COUNT = len(FORMSET_ORDER_KIND_DISPLAY)


    def dispatch(self, request, *args, **kwargs):
        self.date_by_url = self._get_date_by_url(request)
        if not self.date_by_url:
            self.request.session['error'] = self.toast_err_msg
            return redirect(reverse('timecard:timecard_monthly_report'))

        daily_stamps_qs = TimeCard.objects.filter(stamped_time__gte=(self.date_by_url + relativedelta(day=1)),
                                                  stamped_time__lt=(self.date_by_url + relativedelta(months=1, day=1)),
                                                  user=self.request.user)
        if daily_stamps_qs.exclude(state=TimeCard.State.NEW).exists():
            self.request.session['error'] = '{}および{}の情報は更新できません'.format(TimeCard.State.PROCESSING.label,
                                                                            TimeCard.State.APPROVED.label)
            return redirect(reverse('timecard:timecard_monthly_report') + '?month=' + self.date_by_url.strftime('%Y%m'))

        return super().dispatch(request, *args, **kwargs)


    def post(self, request, *args, **kwargs):
        # データを変更するためコピーする
        cp_querydict = request.POST.copy()
        # DBのデータ型に合わせるために打刻時刻に日付を追加する
        self._stamped_time_time2datetime(cp_querydict)

        formset = TimeCardFormSet(cp_querydict)
        if not formset.is_valid():
            context = {}
            # 画面表示のフォーマットに合わせるために打刻時刻を時間のみに変更する
            self._stamped_time_datetime2time(formset)
            context['formset'] = formset

            return render(request, self.template_name, context)

        for form in formset:
            form.instance.user = request.user

        edit_date_str = self.date_by_url.strftime('%Y{0}%m{1}%d{2}').format(*'年月日')
        if formset.save() != False:
            self.request.session['success'] = '{}を更新しました'.format(edit_date_str)
        else:
            self.request.session['error'] = '{}の更新に失敗しました'.format(edit_date_str)

        return redirect(reverse('timecard:timecard_monthly_report') + '?month=' + self.date_by_url.strftime('%Y%m'))


    def _get_date_by_url(self, request):
        date_by_url = ''
        next_month = timezone.datetime.today().astimezone(timezone.get_default_timezone()).replace(
            hour=0, minute=0, second=0, microsecond=0) + relativedelta(day=1, months=1)
        param = request.GET.get('date')
        if param:
            try:
                date_by_url = timezone.datetime.strptime(param, "%Y%m%d").astimezone(timezone.get_default_timezone())
            except:
                self.toast_err_msg = '不正な操作を検知しました'
                return

        if date_by_url >= next_month:
            self.toast_err_msg = '来月以降の情報は編集できません'
            return

        return date_by_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formset'] = TimeCardFormSet(date=self.date_by_url, user=self.request.user)
        return context

    def _stamped_time_time2datetime(self, querydict):
        for formset_index in range(self.FORMSET_COUNT):
            # DBのデータ型に合わせるために打刻時刻に日付を追加する
            add_date_target = 'form-{}-stamped_time'.format(formset_index)
            form_stamped_time = querydict.get(add_date_target)
            querydict[add_date_target] = self.date_by_url.strftime('%Y-%m-%d') + ' ' + form_stamped_time\
                if form_stamped_time else form_stamped_time

    def _stamped_time_datetime2time(self, formset):
        for formset_index in range(self.FORMSET_COUNT):
            edit_target = 'form-{}-stamped_time'.format(formset_index)
            if formset.data.get(edit_target):
                # 画面表示のフォーマットに合わせるために打刻時刻を時間のみに変更する
                formset.data[edit_target] = self._extract_date(formset.data[edit_target])

    def _extract_date(self, datetime_str):
        pattern = r'((0?|1)[0-9]|2[0-3]):[0-5][0-9]'
        if re.search(pattern, datetime_str):
            return re.search(pattern, datetime_str).group()
        return datetime_str


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


class TimeCardProcessMonthList(SuperuserPermissionView, ListView):
    model = TimeCard
    template_name = 'timecard/process_month_list.html'

    def get_queryset(self):
        state_process_month_qs = TimeCard.objects.filter(state=TimeCard.State.PROCESSING).values('user', 'stamped_time').annotate(
            month=TruncMonth('stamped_time')).values('user', 'month').distinct().order_by('user', '-month')

        return state_process_month_qs

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()

        for process_month in context['process_month_list']:
            user = User.objects.get(pk=process_month['user'])
            process_month['user_name'] = user.name
            process_month['date_str'] = process_month['month'].strftime('%Y{0}%m{1}').format(*'年月')
            process_month['param'] = '?month={}&user={}'.format(process_month['month'].strftime('%Y%m'), user.id)

        return context

    def get_context_object_name(self, object_list):
        return 'process_month_list'


class TimeCardProcessMonthlyReportView(SuperuserPermissionView, TimeCardBaseMonthlyReportView):
    template_name = 'timecard/process_monthly_report.html'
    url = reverse_lazy('timecard:timecard_process_month_list')

    def dispatch(self, request, *args, **kwargs):
        self.user = self._get_user_by_url(request)
        response = super().dispatch(request, *args, **kwargs)

        if not (self.user and self.EOM_by_url):
            self.request.session['error'] = '不正な操作を検知しました'
            return redirect(self.url)
        return response

    def get(self, request, *args, **kwargs):

        if not self.get_queryset().exists():
            self.request.session['error'] = '不正な操作を検知しました'
            return redirect(self.url)

        return super().get(request, *args, **kwargs)

    def _get_user_by_url(self, request):
        param = request.GET.get('user')
        if param:
            try:
                return User.objects.get(pk=param)
            except:
                pass

        return

    def get_EOM_by_url(self, request):
        if not request.GET.get('month'):
            return

        return super().get_EOM_by_url(request)

    def get_context_data(self):
        context = super().get_context_data()
        context['user_name'] = self.user.name

        return context

    @transaction.non_atomic_requests
    def approval_process(self):
        try:
            # TODO サマリを作成する
            pass

        except:
            return

    def _create_work_days_flag(self, work_days_list) -> int:
        work_days_flag_int = 0
        for work_day in work_days_list:
            left_shift_count = work_day - 1
            work_days_flag_int = work_days_flag_int | 1 << left_shift_count

        return work_days_flag_int

    def _promote_process(self):
        monthly_stamps_qs = self.get_queryset()

        if monthly_stamps_qs.exclude(state=TimeCard.State.APPROVED):
            self.request.session['error'] = 'すでに承認済みです'
            return redirect(self.url)

        if self.approval_process():
            self.request.session['success'] = 'ステータスを{}に更新しました'.format(TimeCard.State.APPROVED.label)
            return redirect(self.url)

        self.request.session['error'] = '承認処理に失敗しました'
        return redirect(self.url)
