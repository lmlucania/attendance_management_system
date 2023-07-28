from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.timecard.models import TimeCard


class BaseTestCase(TestCase):
    url = None
    template = None

    @classmethod
    def setUpTestData(cls):
        for i in range(1, 4):
            user = {
                "id": i,
                "email": "petit.chat.0509+{}@gmail.com".format(i),
                "name": "テスト{}".format(i),
                "active": True,
                "manager": i % 2,
                "password": "password{}".format(i),
            }
            User.objects.create(**user)

    def setUp(self, login_super_user=False):
        self.super_user = User.objects.get(id=1)
        self.user = User.objects.get(id=2)

        self.stamp_in = TimeCard.objects.create(
            id=1, user=self.user, kind=TimeCard.Kind.IN, stamped_time=self.str2datetime("2023/01/02 09:00:00")
        )
        self.stamp_out = TimeCard.objects.create(
            id=2, user=self.user, kind=TimeCard.Kind.OUT, stamped_time=self.str2datetime("2023/01/02 19:00:00")
        )
        self.stamp_enter_break = TimeCard.objects.create(
            id=3, user=self.user, kind=TimeCard.Kind.ENTER_BREAK, stamped_time=self.str2datetime("2023/01/02 12:00:00")
        )
        self.stamp_end_break = TimeCard.objects.create(
            id=4, user=self.user, kind=TimeCard.Kind.END_BREAK, stamped_time=self.str2datetime("2023/01/02 13:00:00")
        )

        self.client = Client()

        if login_super_user:
            self.client.force_login(user=self.super_user)
        else:
            self.client.force_login(user=self.user)

        self.client_session = self.client.session

    def base_test_get_not_login(self):
        self.client.logout()
        response = self.client.get(self.url, follow=True)
        self.assertIn(reverse("accounts:login"), response.redirect_chain[0][0])
        self.assertEqual(HTTPStatus.FOUND.value, response.redirect_chain[0][1])

    def str2datetime(self, datetime_str, format="%Y/%m/%d %H:%M:%S"):
        return timezone.datetime.strptime(datetime_str, format).astimezone(timezone.get_default_timezone())


class BaseTestCaseNeedSuperUser(BaseTestCase):
    def setUp(self):
        super().setUp(True)
