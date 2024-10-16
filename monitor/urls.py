# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Sensor API
    path('api/sensor/'             , views.SensorListCreateAPI.as_view(), name='api_sensor_list_create'),
    path('api/sensor/<int:pk>/'    , views.SensorDetailAPI.as_view(), name='api_sensor_detail'),

    # Action API
    path('api/action/'                           , views.ActionListCreateAPI.as_view()     , name='api_action_list_create'),
    path('api/action/<int:pk>/'                  , views.ActionDetailAPI.as_view()         , name='api_action_detail'),
    path('api/action/<int:action_id>/run/'       , views.ActionRunNowAPI.as_view()         , name='run_action_now'),
    path('api/action/<int:action_id>/screenshot/', views.ActionScreenshotAPIView.as_view() , name='api_screenshot'),

    # TestResult API
    path('api/test-result/'         , views.TestResultListAPI.as_view(), name='api_testresult_list'),
    path('api/test-result/<int:pk>/', views.TestResultDetailAPI.as_view(), name='api_testresult_detail'),

    # Pages
    path('board/'          , views.BoardView.as_view(), name='web_board'),
    path('sensor/add'      , views.SensorAddView.as_view(), name='web_sensor_add'),
    path('sensor/<int:pk>/', views.SensorDetailView.as_view(), name='web_sensor_detail'),
]
