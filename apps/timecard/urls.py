from django.urls import path

from apps.timecard.views import (DashboardView, TimeCardApprovedMonthListView,
                                 TimeCardApprovedMonthlyReportView,
                                 TimeCardEditView, TimeCardExportView,
                                 TimeCardImportView, TimeCardMonthlyReportView,
                                 TimeCardProcessMonthListView,
                                 TimeCardProcessMonthlyReportView)

app_name = "apps.timecard"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("monthly_report", TimeCardMonthlyReportView.as_view(), name="timecard_monthly_report"),
    path("edit", TimeCardEditView.as_view(), name="timecard_edit"),
    path("export", TimeCardExportView.as_view(), name="timecard_export"),
    path("upload", TimeCardImportView.as_view(), name="timecard_upload"),
    path("process_month_list", TimeCardProcessMonthListView.as_view(), name="timecard_process_month_list"),
    path("process_monthly_report", TimeCardProcessMonthlyReportView.as_view(), name="timecard_process_monthly_report"),
    path("approved_month_list", TimeCardApprovedMonthListView.as_view(), name="timecard_approved_month_list"),
    path(
        "approved_monthly_report", TimeCardApprovedMonthlyReportView.as_view(), name="timecard_approved_monthly_report"
    ),
]
