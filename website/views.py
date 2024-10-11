from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from .forms import ContactForm
from django.urls import reverse_lazy

class ContactFormView(FormView):
    template_name = 'contact/contact_form.html'  # Your contact form template
    form_class = ContactForm
    success_url = reverse_lazy('contact_success')  # URL to redirect to after successful form submission

    def form_valid(self, form):
        # Save the form data to the database
        ip_address = self.request.META.get('X-REAL-IP')
        form.save(ip_address=ip_address)
        # Continue with the usual form validation process
        return super().form_valid(form)

class HomePageView(TemplateView):
    template_name = 'home.html'

class PrivacyView(TemplateView):
    template_name = 'privacy.html'

