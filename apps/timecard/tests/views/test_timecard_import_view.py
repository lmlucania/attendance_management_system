from http import HTTPStatus

from django.urls import reverse

from apps.timecard.forms import UploadFileForm

from ..base import BaseTestCase


class TestTimeCardImportView(BaseTestCase):
    url = reverse("timecard:timecard_upload")
    template = "material-dashboard-master/pages/upload.html"

    def test_get_not_login(self):
        """
        ログイン前に画面にアクセスする
        ログイン画面にリダイレクトされることを確認
        :return:
        """
        super().base_test_get_not_login()

    def test_post_invalid(self):
        """
        入力チェックでNGになることを確認
        :return:
        """
        response = self.client.post(self.url, data={}, files={})
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        upload_form = response.context["upload_form"]
        self.assertIsInstance(upload_form, UploadFileForm)
        self.assertFalse(upload_form.is_valid())
