# urls.py
from . import views
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.authentication import SessionAuthentication

schema_view = get_schema_view(
   openapi.Info(
      title="Djanguard",
      default_version='v1',
      description="API documentation",
   ),
   public=True,
   permission_classes=(AllowAny,),
)

router = DefaultRouter()
router.register(r'sensors'     , views.SensorViewSet    , basename='sensor')
router.register(r'actions'     , views.ActionViewSet    , basename='action')
router.register(r'test-results', views.TestResultViewSet, basename='test-result')


urlpatterns = [
    # API
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0)         , name='schema-json'),
    path('swagger/'        , schema_view.with_ui('swagger', cache_timeout=0) , name='schema-swagger-ui'),
    path('redoc/'          , schema_view.with_ui('redoc', cache_timeout=0)   , name='schema-redoc'),
    path('oauth/'          , include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api/'            , include(router.urls)),

    # Pages
    path('profile/'        , views.ProfileView.as_view()     , name='profile'),
    path('board/'          , views.BoardView.as_view()       , name='web_board'),
    path('config/'         , views.ConfigView.as_view()      , name='web_config'),
    path('sensor/add'      , views.SensorAddView.as_view()   , name='web_sensor_add'),
    path('sensor/<int:pk>/', views.SensorDetailView.as_view(), name='web_sensor_detail'),
]
