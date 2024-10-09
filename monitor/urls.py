from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sensors', views.SensorViewSet)
router.register(r'actions', views.ActionViewSet)
router.register(r'tests', views.TestResultViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('test-results/', views.test_results_view, name='test_results'),
    path('add-sensor/', views.add_sensor, name='add_sensor'),
    # other urls
]