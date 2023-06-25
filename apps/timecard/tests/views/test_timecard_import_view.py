from http import HTTPStatus
from django.urls import reverse
from ..base import BaseTestCase
from apps.timecard.forms import UploadFileForm


class TestTimeCardImportView(BaseTestCase):
    url = reverse('timecard:timecard_upload')
    template = 'timecard/upload.html'

    def test_get_not_login(self):
        super().base_test_get_not_login()

    def test_post_invalid(self):
        response = self.client.post(self.url, data={}, files={})
        self.assertEqual(HTTPStatus.OK.value, response.status_code)
        self.assertEqual(self.template, response.templates[0].name)
        upload_form = response.context['upload_form']
        self.assertIsInstance(upload_form, UploadFileForm)
        self.assertFalse(upload_form.is_valid())
