from datetime import datetime
from http import HTTPStatus

from django.urls import reverse

from apps.timecard.models import TimeCard

from ..base import BaseTestCaseNeedSuperUser


class TestTimeCardProcessMonthlyReportView(BaseTestCaseNeedSuperUser):
    url = reverse("timecard:timecard_process_monthly_report")
    redirect_url = reverse("timecard:timecard_process_month_list")
    template = "material-dashboard-master/pages/processing_list.html"
    redirect_template = "material-dashboard-master/pages/tables_process.html"

    def test_get_not_login(self):
        """
        ログイン前に画面にアクセスする
        ログイン画面にリダイレクトされることを確認
        :return:
        """
        super().base_test_get_not_login()

    def test_get_not_superuser(self):
        """
        一般ユーザーで画面にアクセスする
        403エラーになることを確認
        :return:
        """
        self.client.logout()
        self.client.force_login(user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(HTTPStatus.FORBIDDEN.value, response.status_code)

    def test_get_login_no_param(self, **params):
        """
        クエリパラメーターなしでアクセスする
        承認待ち一覧画面にリダイレクトされることを確認
        エラーメッセージを確認
        :return:
        """
        response = self.client.get(self.url, params, follow=True)
        self.assertEqual("不正な操作を検知しました", response.context_data["error"])
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.redirect_template, response.templates[0].name)
        self.assertEqual(self.redirect_url, response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

    def test_get_login_has_error_param(self):
        """
        不正なクエリパラメーターでアクセスする
        承認待ち一覧画面にリダイレクトされることを確認
        エラーメッセージを確認
        :return:
        """
        self.test_get_login_no_param(a="a")

    def test_normally_param_not_record(self):
        """
        `申請中`のデータが0件
        承認待ち一覧画面にリダイレクトされることを確認
        エラーメッセージを確認
        :return:
        """
        TimeCard.objects.all().delete()

        response = self.client.get(self.url, {"user": self.user.id, "month": "202301"}, follow=True)
        self.assertEqual("勤怠情報が存在しません", response.context_data["error"])
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.redirect_template, response.templates[0].name)
        self.assertEqual(self.redirect_url, response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

    def test_normally_param_exist_record(self):
        """
        `申請中`のデータが表示されることを確認
        :return:
        """
        TimeCard.objects.all().update(state=TimeCard.State.PROCESSING)

        response = self.client.get(self.url, {"user": self.user.id, "month": "202301"}, follow=True)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual("テスト2", response.context_data["user_name"])
        self.assertEqual("9.0", response.context_data["total_work_hours"])
        self.assertEqual(datetime.strptime("2023/01/01", "%Y/%m/%d").date(), response.context_data["BOM"])
        self.assertEqual(datetime.strptime("2023/01/31", "%Y/%m/%d").date(), response.context_data["EOM"])

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

    def test_promote_success(self):
        """
        承認処理
        承認待ち一覧画面にリダイレクトされることを確認
        打刻情報のステータスが`承認済み`に変更されていることを確認
        :return:
        """
        TimeCard.objects.all().update(state=TimeCard.State.PROCESSING)

        response = self.client.get(self.url, {"user": self.user.id, "month": "202301", "mode": "promote"}, follow=True)
        self.assertEqual("承認しました", response.context_data["success"])
        self.assertEqual(0, len(response.context_data["month_list"]))
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.redirect_url, response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

        self.assertEqual(TimeCard.State.APPROVED, TimeCard.objects.get(kind=TimeCard.Kind.IN).state)
        self.assertEqual(TimeCard.State.APPROVED, TimeCard.objects.get(kind=TimeCard.Kind.OUT).state)
        self.assertEqual(TimeCard.State.APPROVED, TimeCard.objects.get(kind=TimeCard.Kind.ENTER_BREAK).state)
        self.assertEqual(TimeCard.State.APPROVED, TimeCard.objects.get(kind=TimeCard.Kind.END_BREAK).state)

    def test_promote_failure_own_record(self):
        """
        ログインユーザーの打刻情報を承認処理する
        承認待ち一覧画面にリダイレクトされることを確認
        エラーメッセージを確認
        :return:
        """
        response = self.client.get(self.url, {"user": self.super_user, "month": "202301", "mode": "promote"}, follow=True)
        self.assertEqual("不正な操作を検知しました", response.context_data["error"])
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.redirect_template, response.templates[0].name)
        self.assertEqual(self.redirect_url, response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

    def test_demote_success(self):
        """
        差戻処理
        承認待ち一覧画面にリダイレクトされることを確認
        打刻情報のステータスが`新規`に変更されていることを確認
        :return:
        """
        TimeCard.objects.all().update(state=TimeCard.State.PROCESSING)

        response = self.client.get(self.url, {"user": self.user.id, "month": "202301", "mode": "demote"}, follow=True)
        self.assertEqual("差し戻しました", response.context_data["success"])
        self.assertEqual(0, len(response.context_data["month_list"]))
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.redirect_url, response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

        self.assertEqual(TimeCard.State.NEW, TimeCard.objects.get(kind=TimeCard.Kind.IN).state)
        self.assertEqual(TimeCard.State.NEW, TimeCard.objects.get(kind=TimeCard.Kind.OUT).state)
        self.assertEqual(TimeCard.State.NEW, TimeCard.objects.get(kind=TimeCard.Kind.ENTER_BREAK).state)
        self.assertEqual(TimeCard.State.NEW, TimeCard.objects.get(kind=TimeCard.Kind.END_BREAK).state)
