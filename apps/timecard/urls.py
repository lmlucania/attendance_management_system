from django.urls import path
from apps.timecard.views import (DashboardView, TimeCardListView, TimeCardCreateView, TimeCardUpdateView,
                                 TimeCardDeleteView)

app_name = 'apps.timecard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('monthly_report', TimeCardListView.as_view(), name='timecard_monthly_report'),
    path('create', TimeCardCreateView.as_view(), name='timecard_create'),
    path('<pk>/update', TimeCardUpdateView.as_view(), name='timecard_update'),
    path('<pk>/delete', TimeCardDeleteView.as_view(), name='timecard_delete')
]
