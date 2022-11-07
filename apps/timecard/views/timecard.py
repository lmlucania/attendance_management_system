from django.urls import reverse_lazy

from .base import ListView, CreateView, UpdateView, DeleteView
from apps.timecard.models import TimeCard
from apps.timecard.forms import TimeCardForm


class TimeCardListView(ListView):
    model = TimeCard


class TimeCardCreateView(CreateView):
    model = TimeCard
    form_class = TimeCardForm
    success_url = reverse_lazy('timecard:dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TimeCardUpdateView(UpdateView):
    model = TimeCard
    form_class = TimeCardForm
    success_url = reverse_lazy('timecard:dashboard')


class TimeCardDeleteView(DeleteView):
    model = TimeCard
    form_class = TimeCardForm
    success_url = reverse_lazy('timecard:dashboard')
