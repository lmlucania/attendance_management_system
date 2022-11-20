from django.http import Http404, HttpResponseRedirect
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy


class TemplateView(LoginRequiredMixin, generic.TemplateView):
    login_url = reverse_lazy('accounts:login')


class ListView(LoginRequiredMixin, generic.ListView):
    search_form = None

    def get_template_names(self):
        return ['%s/list.html' % (self.object_list.model._meta.app_label)]


class CreateView(LoginRequiredMixin, generic.CreateView):

    def get_template_names(self):
        return ['%s/form.html' % (self.model._meta.app_label)]


class UpdateView(LoginRequiredMixin, generic.UpdateView):

    def get_template_names(self):
        return ['%s/form.html' % (self.model._meta.app_label)]


class DeleteView(LoginRequiredMixin, generic.DeleteView):

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except Http404:
            pass

    def delete(self, request, *args, **kwargs):
        _object = self.get_object()
        if _object:
            _object.delete()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.success_url:
            return self.success_url
        else:
            super().get_success_url()
