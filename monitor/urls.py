# urls.py
from django.urls import re_path, path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from . import views

from rest_framework.routers import DefaultRouter
schema_view = get_schema_view(
   openapi.Info(
      title="Djanguard",
      default_version='v1',
      description="API documentation",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register(r'sensors'     , views.SensorViewSet    , basename='sensor')
router.register(r'actions'     , views.ActionViewSet    , basename='action')
router.register(r'test-results', views.TestResultViewSet, basename='test-result')


urlpatterns = [
    # API
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('api/', include(router.urls)),
    path('api/action/<int:action_id>/screenshot/', views.ActionScreenshotAPIView.as_view() , name='api_screenshot'),
    path('api/action/<int:action_id>/run/'       , views.ActionRunNowAPI.as_view()         , name='run_action_now'),

    # Pages
    path('profile/'        , views.ProfileView.as_view()     , name='profile'),
    path('board/'          , views.BoardView.as_view()       , name='web_board'),
    path('config/'         , views.ConfigView.as_view()      , name='web_config'),
    path('sensor/add'      , views.SensorAddView.as_view()   , name='web_sensor_add'),
    path('sensor/<int:pk>/', views.SensorDetailView.as_view(), name='web_sensor_detail'),
]
