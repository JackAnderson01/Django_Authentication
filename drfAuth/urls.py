
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView
)
from rest_framework.documentation import include_docs_urls
from rest_framework.schemas import get_schema_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('docs/', include_docs_urls(title="Api Documentation")),
    path('schema/', get_schema_view(
        title="HRMS Backend",
        description="An Api build on top of django and drf that serves as a backend for a erp platform.",
        version='1.0.0'
    ), name="api_schema"),
    path("auth/", include('users.urls')),
    path('auth/login', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
]
