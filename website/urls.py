from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path(''                 , views.HomePageView.as_view()    , name='home'),
    path('privacy'          , views.PrivacyView.as_view()     , name='privacy'),
    path('terms'            , views.TermsView.as_view()       , name='terms'),
    path('commands'         , views.TermsView.as_view()       , name='commands'),
    path('google-auth'      , views.GoogleAuthView.as_view()  , name='google-auth'),
    path('contact/'         , views.ContactFormView.as_view() , name='contact'),
    path('contact/success/' , TemplateView.as_view(template_name="contact/contact_success.html"), name='contact_success'),
]
