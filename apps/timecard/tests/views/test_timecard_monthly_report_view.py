from datetime import datetime
from http import HTTPStatus

from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.utils import timezone

from apps.timecard.forms import TimeCardFormSet
from apps.timecard.models import TimeCard

from ..base import BaseTestCase


class TestTimeCardMonthlyReportView(BaseTestCase):
    url = reverse("timecard:timecard_monthly_report")
    template = "material-dashboard-master/pages/new_list.html"

    def test_get_not_login(self):
        super().base_test_get_not_login()

    def test_get_login_no_param(self, **params):
        today = timezone.datetime.today().astimezone(timezone.get_default_timezone()).date()
        response = self.client.get(self.url, params)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual(today.strftime("%Y-%m"), response.context_data["search_form"].initial["month"])
        self.assertEqual(today + relativedelta(day=1), response.context_data["BOM"])
        self.assertEqual(today + relativedelta(months=1, day=1) - relativedelta(days=1), response.context_data["EOM"])
        self.assertIsNone(response.context_data["promote_err_msg"])

    def test_get_login_has_error_param(self):
        self.test_get_login_no_param(a="a")

    def test_get_login_has_normally_param(self):
        response = self.client.get(self.url, {"month": "202301"})
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual("2023-01", response.context_data["search_form"].initial["month"])
        self.assertEqual(datetime.strptime("2023/01/01", "%Y/%m/%d").date(), response.context_data["BOM"])
        self.assertEqual(datetime.strptime("2023/01/31", "%Y/%m/%d").date(), response.context_data["EOM"])
        self.assertIsNone(response.context_data["promote_err_msg"])

        monthly_report = response.context_data["monthly_report"]

        self.assertEqual("", monthly_report[0]["start_work"])
        self.assertEqual("", monthly_report[0]["end_work"])
        self.assertEqual("", monthly_report[0]["enter_break"])
        self.assertEqual("", monthly_report[0]["end_break"])
        self.assertEqual("0:00", monthly_report[0]["work_hours"])
        self.assertEqual("0:00", monthly_report[0]["break_hours"])

        self.assertEqual(self.str2datetime("2023/01/02 09:00:00"), monthly_report[1]["start_work"])
        self.assertEqual(self.str2datetime("2023/01/02 19:00:00"), monthly_report[1]["end_work"])
        self.assertEqual(self.str2datetime("2023/01/02 12:00:00"), monthly_report[1]["enter_break"])
        self.assertEqual(self.str2datetime("2023/01/02 13:00:00"), monthly_report[1]["end_break"])
        self.assertEqual("9:00", monthly_report[1]["work_hours"])
        self.assertEqual("1:00", monthly_report[1]["break_hours"])

        self.assertEqual("", monthly_report[2]["start_work"])
        self.assertEqual("", monthly_report[2]["end_work"])
        self.assertEqual("", monthly_report[2]["enter_break"])
        self.assertEqual("", monthly_report[2]["end_break"])
        self.assertEqual("0:00", monthly_report[2]["work_hours"])
        self.assertEqual("0:00", monthly_report[2]["break_hours"])

    def test_secondary_access(self):
        self.client.get(self.url, {"month": "202301"})
        self.client.get(reverse("timecard:dashboard"))

        response = self.client.get(self.url)
        self.assertEqual("2023-01", response.context_data["search_form"].initial["month"])
        self.assertEqual(datetime.strptime("2023/01/01", "%Y/%m/%d").date(), response.context_data["BOM"])
        self.assertEqual(datetime.strptime("2023/01/31", "%Y/%m/%d").date(), response.context_data["EOM"])

    def test_promote_success(self):
        response = self.client.get(self.url, {"month": "202301", "mode": "promote"}, follow=True)
        self.assertEqual("ステータスを申請中に更新しました", response.context_data["success"])
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(reverse("timecard:timecard_monthly_report") + "?month=202301", response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

        self.assertEqual(TimeCard.State.PROCESSING, TimeCard.objects.get(kind=TimeCard.Kind.IN).state)
        self.assertEqual(TimeCard.State.PROCESSING, TimeCard.objects.get(kind=TimeCard.Kind.OUT).state)
        self.assertEqual(TimeCard.State.PROCESSING, TimeCard.objects.get(kind=TimeCard.Kind.ENTER_BREAK).state)
        self.assertEqual(TimeCard.State.PROCESSING, TimeCard.objects.get(kind=TimeCard.Kind.END_BREAK).state)

    def test_promote_failure_is_promoted(self):
        self.stamp_in.state = TimeCard.State.PROCESSING
        self.stamp_in.save()

        response = self.client.get(self.url, {"month": "202301", "mode": "promote"}, follow=True)
        self.assertEqual("すでに申請済みです", response.context_data["error"])
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(reverse("timecard:timecard_monthly_report") + "?month=202301", response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

        self.assertEqual(TimeCard.State.PROCESSING, self.stamp_in.state)
        self.assertEqual(TimeCard.State.NEW, self.stamp_out.state)
        self.assertEqual(TimeCard.State.NEW, self.stamp_out.state)
        self.assertEqual(TimeCard.State.NEW, self.stamp_out.state)

    def test_promote_failure_not_exist_stamp(self):
        response = self.client.get(self.url, {"month": "202302", "mode": "promote"}, follow=True)
        self.assertEqual("未打刻のため申請できません", response.context_data["warning"])
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(reverse("timecard:timecard_monthly_report") + "?month=202302", response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

    def test_promote_failure_invalid_stamp(self):
        self.stamp_in.stamped_time = self.str2datetime("2023/01/02 22:00:00")
        self.stamp_in.save()

        response = self.client.get(self.url, {"month": "202301", "mode": "promote"}, follow=True)
        self.assertEqual("入力時刻にエラーがあるため申請できません", response.context_data["warning"])
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(reverse("timecard:timecard_monthly_report") + "?month=202301", response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

        self.assertEqual(TimeCard.State.NEW, self.stamp_in.state)
        self.assertEqual(TimeCard.State.NEW, self.stamp_out.state)

        expected_err_msg = "2日：" + TimeCardFormSet.ERR_MSG_WORK_TIME
        self.assertEqual(expected_err_msg, response.context_data.get("promote_err_msg")[0])

        self.client.get(reverse("timecard:dashboard"))

        response = self.client.get(self.url + "?month=202301")
        self.assertEqual(expected_err_msg, response.context_data["promote_err_msg"][0])
