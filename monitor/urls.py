from django.urls import path
from . import views

urlpatterns = [
    # Sensor API
    path('api/sensor/', views.SensorListCreateAPIView.as_view(), name='api_sensor_list_create'),
    path('api/sensor/<int:pk>/', views.SensorDetailAPIView.as_view(), name='api_sensor_detail'),    

    # Action API
    path('api/action/'                , views.ActionListCreateAPIView.as_view(), name='api_action_list_create'),
    path('api/action/<int:pk>/'       , views.ActionDetailAPIView.as_view(), name='api_action_detail'),

    # TestResult API
    path('api/test-result/'           , views.TestResultListAPIView.as_view()   , name='api_testresult_list'),
    path('api/test-result/<int:pk>/'  , views.TestResultDetailAPIView.as_view() , name='api_testresult_detail'),

    # Pages
    path('sensor/'         , views.SensorList.as_view()  , name='web_sensor_list'),
    path('sensor/add'      , views.SensorAdd.as_view()   , name='web_sensor_add'),
    path('sensor/<int:pk>/', views.SensorDetail.as_view(), name='web_sensor_detail'),

]