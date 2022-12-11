from django.urls import path
from apps.timecard.views import (DashboardView, TimeCardListView, TimeCardEditView)

app_name = 'apps.timecard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('monthly_report', TimeCardListView.as_view(), name='timecard_monthly_report'),
    path('edit', TimeCardEditView.as_view(), name='timecard_edit'),
]
