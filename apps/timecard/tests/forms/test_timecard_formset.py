from apps.timecard.forms import TimeCardFormSet
from apps.timecard.models import TimeCard

from ..base import BaseTestCase


class TestTimeCardFormset(BaseTestCase):
    def test_required_false(self):
        """
        エラーなし
        全項目未入力
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
        }
        formset = TimeCardFormSet(post_data)
        self.assertEqual(0, len(formset.errors[0]))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

    def test_required_stamped_time(self):
        """
        必須チェックエラー
        打刻時刻 未入力
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-kind": TimeCard.Kind.IN,
        }
        formset = TimeCardFormSet(post_data)
        errors = formset.errors[0].get("stamped_time").get_json_data()
        self.assertEqual("required", errors[0].get("code"))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

    def test_required_kind(self):
        """
        必須チェックエラー
        打刻種別 未入力
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
        }
        formset = TimeCardFormSet(post_data)
        errors = formset.errors[0].get("kind").get_json_data()
        self.assertEqual("required", errors[0].get("code"))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

    def test_invalid_date_stamped_time(self):
        """
        チェックエラー
        打刻時刻 日付が不正
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "a",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
        }
        formset = TimeCardFormSet(post_data)
        errors = formset.errors[0].get("stamped_time").get_json_data()
        self.assertEqual("invalid", errors[0].get("code"))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

    def test_invalid_time_stamped_time(self):
        """
        チェックエラー
        打刻時刻 時刻が不正
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "a",
            "form-0-kind": TimeCard.Kind.IN,
        }
        formset = TimeCardFormSet(post_data)
        errors = formset.errors[0].get("stamped_time").get_json_data()
        self.assertEqual("invalid", errors[0].get("code"))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

    def test_invalid_choice_kind(self):
        """
        チェックエラー
        打刻種別 不正な値
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": "a",
        }
        formset = TimeCardFormSet(post_data)
        errors = formset.errors[0].get("kind").get_json_data()
        self.assertEqual("invalid_choice", errors[0].get("code"))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

    def test_err_only_start_work(self):
        """
        相関チェックエラー
        出勤が入力されている
        退勤が未入力
        :return:
        """
        self._stamp_which_one_start_work_or_end_work()

    def test_err_only_end_work(self):
        """
        相関チェックエラー
        出勤が未入力
        退勤が入力されている
        :return:
        """
        self._stamp_which_one_start_work_or_end_work(False)

    def test_err_take_break_without_start_work(self):
        """
        相関チェックエラー
        出勤が未入力
        退勤、休憩開始、休憩終了が入力されている
        :return:
        """
        self._take_break_without_start_work_or_end_work()

    def test_err_take_break_without_end_work(self):
        """
        相関チェックエラー
        退勤が未入力
        出勤、休憩開始、休憩終了が入力されている
        :return:
        """
        self._take_break_without_start_work_or_end_work(False)

    def test_err_end_work_before_start_work(self):
        """
        相関チェックエラー
        退勤＜出勤
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "19:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "09:00",
            "form-1-kind": TimeCard.Kind.OUT,
        }
        formset = TimeCardFormSet(post_data)
        self.assertEqual(0, len(formset.errors[0]))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

        self.assertEqual(TimeCardFormSet.ERR_MSG_WORK_TIME, formset.non_form_errors()[0])

    def test_err_end_break_before_enter_break(self):
        """
        相関チェックエラー
        退勤＜休憩終了
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-stamped_time_0": "2023-06-01",
            "form-2-stamped_time_1": "15:00",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-stamped_time_0": "2023-06-01",
            "form-3-stamped_time_1": "13:00",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }

        formset = TimeCardFormSet(post_data)
        self.assertEqual(0, len(formset.errors[0]))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

        self.assertEqual(TimeCardFormSet.ERR_MSG_BREAK_TIME, formset.non_form_errors()[0])

    def test_err_enter_break_out_of_range(self):
        """
        相関チェックエラー
        休憩開始＜出勤
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-stamped_time_0": "2023-06-01",
            "form-2-stamped_time_1": "06:00",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-stamped_time_0": "2023-06-01",
            "form-3-stamped_time_1": "13:00",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }

        formset = TimeCardFormSet(post_data)
        self.assertEqual(0, len(formset.errors[0]))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

        self.assertEqual(TimeCardFormSet.ERR_MSG_BREAK_TIME_OUT_OF_RANGE, formset.non_form_errors()[0])

    def test_err_end_break_out_of_range(self):
        """
        相関チェックエラー
        退勤＜休憩終了
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-stamped_time_0": "2023-06-01",
            "form-2-stamped_time_1": "12:00",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-stamped_time_0": "2023-06-01",
            "form-3-stamped_time_1": "20:00",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }

        formset = TimeCardFormSet(post_data)
        self.assertEqual(0, len(formset.errors[0]))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

        self.assertEqual(TimeCardFormSet.ERR_MSG_BREAK_TIME_OUT_OF_RANGE, formset.non_form_errors()[0])

    def test_err_duplicate_kind(self):
        """
        相関チェックエラー
        打刻種別が重複する
        :return:
        """
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.IN,
            "form-2-stamped_time_0": "2023-06-01",
            "form-2-stamped_time_1": "15:00",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-stamped_time_0": "2023-06-01",
            "form-3-stamped_time_1": "13:00",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }

        formset = TimeCardFormSet(post_data)
        self.assertEqual(0, len(formset.errors[0]))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

        self.assertEqual(TimeCardFormSet.ERR_MSG_DUPLICATE_KIND, formset.non_form_errors()[0])

    def test_create(self):
        """
        登録処理（入力チェックOK）
        登録されていることを確認
        :return:
        """
        TimeCard.objects.all().delete()
        self.assertEqual(0, TimeCard.objects.all().count())

        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-stamped_time_0": "2023-06-01",
            "form-2-stamped_time_1": "12:00",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-stamped_time_0": "2023-06-01",
            "form-3-stamped_time_1": "13:00",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }
        formset = TimeCardFormSet(post_data)
        for form in formset:
            form.instance.user = self.user
        self.assertTrue(formset.is_valid())

        stamps = formset.save()
        self.assertIsNotNone(stamps)

        self.assertEqual(4, TimeCard.objects.all().count())

        self.assertEqual(TimeCard.Kind.IN, stamps[0].kind)
        self.assertEqual(self.str2datetime("2023-06-01 07:00", "%Y-%m-%d %H:%M"), stamps[0].stamped_time)
        self.assertEqual(TimeCard.Kind.OUT, stamps[1].kind)
        self.assertEqual(self.str2datetime("2023-06-01 19:00", "%Y-%m-%d %H:%M"), stamps[1].stamped_time)
        self.assertEqual(TimeCard.Kind.ENTER_BREAK, stamps[2].kind)
        self.assertEqual(self.str2datetime("2023-06-01 12:00", "%Y-%m-%d %H:%M"), stamps[2].stamped_time)
        self.assertEqual(TimeCard.Kind.END_BREAK, stamps[3].kind)
        self.assertEqual(self.str2datetime("2023-06-01 13:00", "%Y-%m-%d %H:%M"), stamps[3].stamped_time)

    def test_update(self):
        """
        更新処理（入力チェックOK）
        更新されていることを確認
        :return:
        """
        self.assertEqual(4, TimeCard.objects.all().count())

        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-id": 1,
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-1-id": 2,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-id": 3,
            "form-2-stamped_time_0": "2023-06-01",
            "form-2-stamped_time_1": "12:00",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-id": 4,
            "form-3-stamped_time_0": "2023-06-01",
            "form-3-stamped_time_1": "13:00",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }
        formset = TimeCardFormSet(post_data)
        for form in formset:
            form.instance.user = self.user
        self.assertTrue(formset.is_valid())

        stamps = formset.save()
        self.assertIsNotNone(stamps)

        self.assertEqual(4, TimeCard.objects.all().count())

        self.assertEqual(TimeCard.Kind.IN, stamps[0].kind)
        self.assertEqual(self.str2datetime("2023-06-01 07:00", "%Y-%m-%d %H:%M"), stamps[0].stamped_time)
        self.assertEqual(TimeCard.Kind.OUT, stamps[1].kind)
        self.assertEqual(self.str2datetime("2023-06-01 19:00", "%Y-%m-%d %H:%M"), stamps[1].stamped_time)
        self.assertEqual(TimeCard.Kind.ENTER_BREAK, stamps[2].kind)
        self.assertEqual(self.str2datetime("2023-06-01 12:00", "%Y-%m-%d %H:%M"), stamps[2].stamped_time)
        self.assertEqual(TimeCard.Kind.END_BREAK, stamps[3].kind)
        self.assertEqual(self.str2datetime("2023-06-01 13:00", "%Y-%m-%d %H:%M"), stamps[3].stamped_time)

    def test_delete(self):
        """
        削除処理
        削除されていることを確認
        :return:
        """
        self.assertEqual(4, TimeCard.objects.all().count())

        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-id": 1,
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": TimeCard.Kind.IN,
            "form-0-DELETE": "on",
            "form-1-id": 2,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "19:00",
            "form-1-kind": TimeCard.Kind.OUT,
            "form-2-id": 3,
            "form-2-stamped_time_0": "2023-06-01",
            "form-2-stamped_time_1": "12:00",
            "form-2-kind": TimeCard.Kind.ENTER_BREAK,
            "form-3-id": 4,
            "form-3-stamped_time_0": "2023-06-01",
            "form-3-stamped_time_1": "13:00",
            "form-3-kind": TimeCard.Kind.END_BREAK,
        }
        formset = TimeCardFormSet(post_data)
        for form in formset:
            form.instance.user = self.user
        self.assertTrue(formset.is_valid())

        stamps = formset.save()
        self.assertIsNotNone(stamps)

        self.assertEqual(3, TimeCard.objects.all().count())

        self.assertEqual(TimeCard.Kind.OUT, stamps[0].kind)
        self.assertEqual(self.str2datetime("2023-06-01 19:00", "%Y-%m-%d %H:%M"), stamps[0].stamped_time)
        self.assertEqual(TimeCard.Kind.ENTER_BREAK, stamps[1].kind)
        self.assertEqual(self.str2datetime("2023-06-01 12:00", "%Y-%m-%d %H:%M"), stamps[1].stamped_time)
        self.assertEqual(TimeCard.Kind.END_BREAK, stamps[2].kind)
        self.assertEqual(self.str2datetime("2023-06-01 13:00", "%Y-%m-%d %H:%M"), stamps[2].stamped_time)

    def _stamp_which_one_start_work_or_end_work(self, start_work=True):
        """
        相関チェック
        出勤と退勤のどちらか一方だけ入力されている
        :param start_work:True 出勤が入力されている, False 退勤が入力されている
        :return:
        """
        kind = TimeCard.Kind.IN if start_work else TimeCard.Kind.OUT
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": kind,
        }
        formset = TimeCardFormSet(post_data)
        self.assertEqual(0, len(formset.errors[0]))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

        self.assertEqual(TimeCardFormSet.ERR_MSG_NEED_WORK_TIME, formset.non_form_errors()[0])

    def _take_break_without_start_work_or_end_work(self, start_work=True):
        """
        相関チェック
        休憩開始と休憩終了は両方入力されている
        出勤と退勤はどちらか一方だけ入力されている
        :param start_work:True 出勤が入力されている, False 退勤が入力されている
        :return:
        """
        kind = TimeCard.Kind.IN if start_work else TimeCard.Kind.OUT
        post_data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "4",
            "form-0-stamped_time_0": "2023-06-01",
            "form-0-stamped_time_1": "07:00",
            "form-0-kind": kind,
            "form-1-stamped_time_0": "2023-06-01",
            "form-1-stamped_time_1": "12:00",
            "form-1-kind": TimeCard.Kind.ENTER_BREAK,
            "form-2-stamped_time_0": "2023-06-01",
            "form-2-stamped_time_1": "13:00",
            "form-2-kind": TimeCard.Kind.END_BREAK,
        }
        formset = TimeCardFormSet(post_data)
        self.assertEqual(0, len(formset.errors[0]))
        self.assertEqual(0, len(formset.errors[1]))
        self.assertEqual(0, len(formset.errors[2]))
        self.assertEqual(0, len(formset.errors[3]))

        self.assertEqual(TimeCardFormSet.ERR_MSG_NEED_WORK_TIME, formset.non_form_errors()[0])
