from datetime import timedelta

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.timecard.models import TimeCard, TimeCardSummary
from faker import Faker
from django.utils import timezone
import random
from dateutil.relativedelta import relativedelta

from apps.timecard.views.base import timedelta2str
from apps.timecard.views.timecard import TimeCardProcessMonthlyReportView

class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        self.new_users = []
        self.today = (
            timezone.datetime.today()
            .astimezone(timezone.get_default_timezone())
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        super().__init__(*args, **kwargs)


    def handle(self, *args, **options):
        self.new_users = []

        if options['reset']:
           User.objects.all().delete()

        self._create_users(4)
        self._create_super_users(3)
        
        for user in self.new_users:
            self._create_data(user)

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true')

    def _create_user(self, is_manager):
        fake = Faker('jp-JP')
        last_name, last_name_ruby, last_name_alphabet = fake.last_name_pair()
        first_name, first_name_ruby, first_name_alphabet = fake.first_name_pair()
        user = {
            'name': '{} {}'.format(last_name, first_name),
            'email': '{}-{}@example.com'.format(last_name_alphabet, first_name_alphabet),
            'manager': is_manager
        }
        obj = User(**user)
        obj.set_password('pass')
        obj.save()
        self.new_users.append(obj)

    def _create_users(self, num, is_manager=False):
        for i in range(num):
            self._create_user(is_manager)

    def _create_super_users(self, num):
        self._create_users(num, True)

    def _create_timecard(self, user, month, state):
        work_days_list = self._create_random_work_days_list(month)
        total_work_hours = total_break_hours = timedelta()

        for day in work_days_list:
            datetime = self.today.replace(month=month, day=day)
            if random.randint(0, 5) == 0:
                # 5分の1の確率で午前中のみ出勤にする
                start_work = datetime.replace(hour=random.randint(7, 9), minute=random.randint(0, 59))
                end_work = datetime.replace(hour=random.randint(11, 12), minute=random.randint(0, 59))
                total_work_hours += (end_work - start_work)

                TimeCard.objects.create(user=user, kind=TimeCard.Kind.IN, stamped_time=start_work, state=state)
                TimeCard.objects.create(user=user, kind=TimeCard.Kind.OUT, stamped_time=end_work, state=state)
            else:
                start_work = datetime.replace(hour=random.randint(7, 9), minute=random.randint(0, 59))
                end_work = datetime.replace(hour=random.randint(17, 20), minute=random.randint(0, 59))
                enter_break = datetime.replace(hour=12, minute=random.randint(0, 15))
                end_break = datetime.replace(hour=13, minute=random.randint(0, 15))
                break_hours = end_break - enter_break
                total_work_hours += (end_work - start_work - break_hours)
                total_break_hours += break_hours

                TimeCard.objects.create(user=user, kind=TimeCard.Kind.IN, stamped_time=start_work, state=state)
                TimeCard.objects.create(user=user, kind=TimeCard.Kind.OUT, stamped_time=end_work, state=state)
                TimeCard.objects.create(user=user, kind=TimeCard.Kind.ENTER_BREAK, stamped_time=enter_break, state=state)
                TimeCard.objects.create(user=user, kind=TimeCard.Kind.END_BREAK, stamped_time=end_break, state=state)

        return work_days_list, total_work_hours, total_break_hours

    def _create_data(self, user):
        self._create_new_timecard(user)

        last_month = self.today.month - 1
        for month in range(1, self.today.month):
            work_days_list, total_work_hours, total_break_hours = self._create_timecard(user, month, TimeCard.State.PROCESSING)

            if month != last_month:
                self._approve_timecard_and_create_summary(user, month, work_days_list, total_work_hours, total_break_hours)

    def _approve_timecard_and_create_summary(self, user, month, work_days_list, total_work_hours, total_break_hours):
        obj = TimeCardProcessMonthlyReportView()
        work_days_flag = obj.create_work_days_flag(work_days_list)
        TimeCard.objects.filter(user=user, state=TimeCard.State.PROCESSING).update(state=TimeCard.State.APPROVED)
        TimeCardSummary.objects.create(user=user, work_days_flag=work_days_flag, month=(self.today + relativedelta(month=month)).strftime("%Y%m"), total_work_hours=timedelta2str(total_work_hours),
                    total_break_hours=timedelta2str(total_break_hours),)


    def _create_new_timecard(self, user):
        self._create_timecard(user, self.today.month, TimeCard.State.NEW)
        TimeCard.objects.filter(user=user, stamped_time__gt=self.today).delete()


    def _get_day_count(self, month):
        next_month = month + 1
        EOM = self.today.date() + relativedelta(month=next_month, day=1) - relativedelta(days=1)
        return EOM.day

    def _create_random_work_days_list(self, month):
        day_count = self._get_day_count(month)
        work_days_count = random.randint(19,24)
        return random.sample(range(1, day_count+1), work_days_count)
