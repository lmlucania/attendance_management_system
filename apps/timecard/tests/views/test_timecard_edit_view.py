from datetime import datetime
from http import HTTPStatus

from dateutil.relativedelta import relativedelta
from django.urls import reverse

from apps.timecard.models import TimeCard

from ..base import BaseTestCase


class TestTimeCardEditView(BaseTestCase):
    url = reverse("timecard:timecard_edit")
    monthly_report_url = reverse("timecard:timecard_monthly_report")
    template = "timecard/form.html"
    monthly_report_template = "material-dashboard-master/pages/new_list.html"

    def test_get_not_login(self):
        super().base_test_get_not_login()

    def test_get_failure_not_param(self):
        response = self.client.get(self.url)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        self.assertEqual("不正な操作を検知しました", self.client_session.get("error"))

    def test_get_failure_next_month(self):
        next_month_YM = (datetime.today() + relativedelta(day=1, months=1)).strftime("%Y%m%d")
        response = self.client.get(self.url, {"date": next_month_YM})
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        self.assertEqual("来月以降の情報は編集できません", self.client_session.get("error"))

    def test_get_failure_exist_promoted_stamp(self):
        TimeCard.objects.all().update(state=TimeCard.State.PROCESSING)

        response = self.client.get(self.url, {"date": "20230102"})
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        self.assertEqual("申請中および承認済みの情報は更新できません", self.client_session.get("error"))

    def test_not_initial_data(self):
        target_date_YMD = "20230101"
        target_date = self.str2datetime(target_date_YMD + "00:00:00", "%Y%m%d%H:%M:%S")
        response = self.client.get(self.url, {"date": target_date_YMD})
        qs = TimeCard.objects.filter(
            stamped_time__gte=target_date, stamped_time__lt=target_date + relativedelta(days=1)
        )
        self.assertFalse(qs.exists())
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual(target_date.date(), response.context_data["edit_date"])
        self.assertEqual("日", response.context_data["DOW"])

        formset = response.context_data["formset"]
        self.assertEqual(4, len(formset))

        for form in formset:
            self.assertIsNone(form.initial.get("stamped_time"))
            self.assertIsNone(form.initial.get("kind"))
            self.assertIsNone(form.initial.get("DELETE"))

    def test_initial_data(self):
        target_date_YMD = "20230102"
        target_date = self.str2datetime(target_date_YMD + "00:00:00", "%Y%m%d%H:%M:%S")
        response = self.client.get(self.url, {"date": target_date_YMD})
        qs = TimeCard.objects.filter(
            stamped_time__gte=target_date, stamped_time__lt=target_date + relativedelta(days=1)
        )
        self.assertTrue(qs.exists())
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual(target_date.date(), response.context_data["edit_date"])
        self.assertEqual("月", response.context_data["DOW"])
        formset = response.context_data["formset"]
        self.assertEqual(4, len(formset))

        self.assertEqual(self.str2datetime("2023/01/02 09:00:00"), formset[0].initial.get("stamped_time"))
        self.assertEqual(TimeCard.Kind.IN, formset[0].initial.get("kind"))
        self.assertIsNone(formset[0].initial.get("DELETE"))

        self.assertEqual(self.str2datetime("2023/01/02 19:00:00"), formset[1].initial.get("stamped_time"))
        self.assertEqual(TimeCard.Kind.OUT, formset[1].initial.get("kind"))
        self.assertIsNone(formset[1].initial.get("DELETE"))

        self.assertEqual(self.str2datetime("2023/01/02 12:00:00"), formset[2].initial.get("stamped_time"))
        self.assertEqual(TimeCard.Kind.ENTER_BREAK, formset[2].initial.get("kind"))
        self.assertIsNone(formset[2].initial.get("DELETE"))

        self.assertEqual(self.str2datetime("2023/01/02 13:00:00"), formset[3].initial.get("stamped_time"))
        self.assertEqual(TimeCard.Kind.END_BREAK, formset[3].initial.get("kind"))
        self.assertIsNone(formset[3].initial.get("DELETE"))

    def test_create_success(self):
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-01-03",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-01-03",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.OUT,
        }

        TimeCard.objects.all().delete()
        self.assertEqual(0, TimeCard.objects.all().count())

        response = self.client.post(self.url, data=post_data)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual(2, TimeCard.objects.all().count())

        stamp_in = TimeCard.objects.filter(kind=TimeCard.Kind.IN).first()
        stamp_out = TimeCard.objects.filter(kind=TimeCard.Kind.OUT).first()

        self.assertEqual(self.str2datetime("2023/01/03 07:00", "%Y/%m/%d %H:%M"), stamp_in.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/03 19:00", "%Y/%m/%d %H:%M"), stamp_out.stamped_time)

        self.assertEqual("更新しました", self.client.session["success"])

    def test_create_failure_by_validation(self):
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "2",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-01-03",
            "form-0-stamped_time_1": "17:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-01-03",
            "form-1-stamped_time_1": "07:00",
            "form-1-kind": TimeCard.Kind.OUT,
        }

        TimeCard.objects.all().delete()
        response = self.client.post(self.url, data=post_data, follow=True)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)

        self.assertEqual(self.monthly_report_template, response.templates[0].name)
        self.assertEqual(self.monthly_report_url, response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

        self.assertEqual(0, TimeCard.objects.all().count())

    def test_create_failure_by_validation_normally_param(self):
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "2",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-01-03",
            "form-0-stamped_time_1": "17:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-01-03",
            "form-1-stamped_time_1": "07:00",
            "form-1-kind": TimeCard.Kind.OUT,
        }

        TimeCard.objects.all().delete()
        response = self.client.post(self.url + "?date=20230103", data=post_data)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        self.assertEqual(0, TimeCard.objects.all().count())

    def test_delete(self):
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-id": 1,
            "form-0-stamped_time_0": "2023-01-02",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-0-DELETE": "on",
            "form-1-id": 2,
            "form-1-stamped_time_0": "2023-01-02",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-1-DELETE": "on",
            "form-2-id": 3,
            "form-2-stamped_time_0": "2023-01-02",
            "form-2-stamped_time_1": "07:00",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-2-DELETE": "on",
            "form-3-id": 4,
            "form-3-stamped_time_0": "2023-01-02",
            "form-3-stamped_time_1": "07:00",
            "form-3-kind": TimeCard.Kind.END_BREAK,
            "form-3-DELETE": "on",
        }

        self.assertEqual(4, TimeCard.objects.all().count())

        response = self.client.post(self.url, data=post_data)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual(0, TimeCard.objects.all().count())

        self.assertEqual("更新しました", self.client.session["success"])

    def test_update_success(self):
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-id": 1,
            "form-0-stamped_time_0": "2023-01-04",
            "form-0-stamped_time_1": "07:30",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-id": 2,
            "form-1-stamped_time_0": "2023-01-04",
            "form-1-stamped_time_1": "19:30",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-id": 3,
            "form-2-stamped_time_0": "2023-01-04",
            "form-2-stamped_time_1": "12:30",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-id": 4,
            "form-3-stamped_time_0": "2023-01-04",
            "form-3-stamped_time_1": "13:30",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }

        response = self.client.post(self.url, data=post_data)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual(4, TimeCard.objects.all().count())

        stamp_in = TimeCard.objects.get(id=1)
        stamp_out = TimeCard.objects.get(id=2)
        stamp_break_enter = TimeCard.objects.get(id=3)
        stamp_break_out = TimeCard.objects.get(id=4)

        self.assertEqual(self.str2datetime("2023/01/04 07:30", "%Y/%m/%d %H:%M"), stamp_in.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/04 19:30", "%Y/%m/%d %H:%M"), stamp_out.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/04 12:30", "%Y/%m/%d %H:%M"), stamp_break_enter.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/04 13:30", "%Y/%m/%d %H:%M"), stamp_break_out.stamped_time)

        self.assertEqual("更新しました", self.client.session["success"])

    def test_update_failure_by_validation(self):
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-id": 1,
            "form-0-stamped_time_0": "2023-01-04",
            "form-0-stamped_time_1": "20:30",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-id": 2,
            "form-1-stamped_time_0": "2023-01-04",
            "form-1-stamped_time_1": "19:30",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-id": 3,
            "form-2-stamped_time_0": "2023-01-04",
            "form-2-stamped_time_1": "12:30",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-id": 4,
            "form-3-stamped_time_0": "2023-01-04",
            "form-3-stamped_time_1": "13:30",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }

        response = self.client.post(self.url, data=post_data, follow=True)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)

        self.assertEqual(self.monthly_report_template, response.templates[0].name)
        self.assertEqual(self.monthly_report_url, response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

        self.assertEqual(4, TimeCard.objects.all().count())

        stamp_in = TimeCard.objects.get(id=1)
        stamp_out = TimeCard.objects.get(id=2)
        stamp_break_enter = TimeCard.objects.get(id=3)
        stamp_break_out = TimeCard.objects.get(id=4)

        self.assertEqual(self.str2datetime("2023/01/02 09:00", "%Y/%m/%d %H:%M"), stamp_in.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/02 19:00", "%Y/%m/%d %H:%M"), stamp_out.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/02 12:00", "%Y/%m/%d %H:%M"), stamp_break_enter.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/02 13:00", "%Y/%m/%d %H:%M"), stamp_break_out.stamped_time)

    def test_update_failure_exist_promoted_stamp(self):
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-id": 1,
            "form-0-stamped_time_0": "2023-01-04",
            "form-0-stamped_time_1": "07:30",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-id": 2,
            "form-1-stamped_time_0": "2023-01-04",
            "form-1-stamped_time_1": "19:30",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-id": 3,
            "form-2-stamped_time_0": "2023-01-04",
            "form-2-stamped_time_1": "12:30",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-id": 4,
            "form-3-stamped_time_0": "2023-01-04",
            "form-3-stamped_time_1": "13:30",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }
        TimeCard.objects.all().update(state=TimeCard.State.APPROVED)

        response = self.client.post(self.url, data=post_data)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual(4, TimeCard.objects.all().count())

        stamp_in = TimeCard.objects.get(id=1)
        stamp_out = TimeCard.objects.get(id=2)
        stamp_break_enter = TimeCard.objects.get(id=3)
        stamp_break_out = TimeCard.objects.get(id=4)

        self.assertEqual(self.str2datetime("2023/01/02 09:00", "%Y/%m/%d %H:%M"), stamp_in.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/02 19:00", "%Y/%m/%d %H:%M"), stamp_out.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/02 12:00", "%Y/%m/%d %H:%M"), stamp_break_enter.stamped_time)
        self.assertEqual(self.str2datetime("2023/01/02 13:00", "%Y/%m/%d %H:%M"), stamp_break_out.stamped_time)

        self.assertEqual("申請中のため編集できません", self.client.session.get("error"))
