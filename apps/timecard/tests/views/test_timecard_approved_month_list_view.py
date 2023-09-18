from http import HTTPStatus

from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.timecard.models import TimeCardSummary

from ..base import BaseTestCaseNeedSuperUser


class TestTimeCardApprovedMonthListView(BaseTestCaseNeedSuperUser):
    url = reverse("timecard:timecard_approved_month_list")
    template = "material-dashboard-master/pages/tables_approved.html"

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

    def test_get_login_no_param(self):
        """
        クエリパラメーターなしでアクセスする
        検索フォームにシステム日付の１ヶ月前の年月が表示されることを確認する
        :return:
        """
        today = timezone.datetime.today().astimezone(timezone.get_default_timezone()).date()
        response = self.client.get(self.url)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual(
            (today - relativedelta(months=1)).strftime("%Y-%m"), response.context_data["search_form"].initial["month"]
        )

    def test_get_no_record(self):
        """
        承認済みのデータが0件
        :return:
        """
        response = self.client.get(self.url)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        self.assertEqual(0, response.context_data["timecardsummary_list"].count())

    def test_get_login_has_normally_param(self):
        """
        承認済みのデータが存在する
        :return:
        """
        for user in User.objects.all():
            TimeCardSummary.objects.create(
                total_work_hours="1", total_break_hours="2", work_days_flag=3, month="202301", user=user
            )
            TimeCardSummary.objects.create(
                total_work_hours="1", total_break_hours="2", work_days_flag=3, month="202302", user=user
            )

        response = self.client.get(self.url, {"month": "202301"})
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)

        self.assertEqual("2023-01", response.context_data["search_form"].initial["month"])

        summary_list = response.context_data["timecardsummary_list"]

        self.assertEqual(2, len(summary_list))
        self.assertEqual("1", summary_list[0].total_work_hours)
        self.assertEqual("2", summary_list[0].total_break_hours)
        self.assertEqual(3, summary_list[0].work_days_flag)
        self.assertEqual("202301", summary_list[0].month)
        self.assertEqual(2, summary_list[0].user.id)

        self.assertEqual("1", summary_list[1].total_work_hours)
        self.assertEqual("2", summary_list[1].total_break_hours)
        self.assertEqual(3, summary_list[1].work_days_flag)
        self.assertEqual("202301", summary_list[1].month)
        self.assertEqual(3, summary_list[1].user.id)

    def test_secondary_access(self):
        """
        他メニュー遷移後の再表示
        クエリパラメーターなしの時に遷移前と同じ年月の情報が表示されることを確認
        :return:
        """
        self.client.get(self.url, {"month": "202301"})
        self.client.get(reverse("timecard:dashboard"))

        response = self.client.get(self.url)
        self.assertEqual("2023-01", response.context_data["search_form"].initial["month"])
