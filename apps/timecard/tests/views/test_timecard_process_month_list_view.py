from http import HTTPStatus

from django.urls import reverse

from apps.timecard.models import TimeCard

from ..base import BaseTestCaseNeedSuperUser


class TestTimeCardProcessMonthListView(BaseTestCaseNeedSuperUser):
    url = reverse("timecard:timecard_process_month_list")
    template = "material-dashboard-master/pages/tables_process.html"

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

    def test_get_no_record(self):
        """
        承認申請が0件
        :return:
        """
        response = self.client.get(self.url)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        self.assertEqual(0, response.context_data["month_list"].count())

    def test_display_promoted_month(self):
        """
        承認申請が存在する
        申請者と申請月が表示されていることを確認
        :return:
        """
        TimeCard.objects.filter(user=self.user).update(state=TimeCard.State.PROCESSING)

        response = self.client.get(self.url)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        self.assertEqual(1, response.context_data["month_list"].count())
        self.assertEqual("テスト2", response.context_data["month_list"][0]["user_name"])
        self.assertEqual("2023年01月", response.context_data["month_list"][0]["date_str"])

    def test_not_display_own_promoted_month(self):
        """
        ログインユーザーの承認申請が表示されないことを確認
        :return:
        """
        TimeCard.objects.filter(user=self.user).update(state=TimeCard.State.PROCESSING, user=self.super_user)

        response = self.client.get(self.url)
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        self.assertEqual(0, response.context_data["month_list"].count())
