from django.urls import path
from .views import HomeView, UserCreateView, VerifyOtpView, RegenerateOtpView, ForgotPasswordView


urlpatterns = [
    path("", HomeView.as_view(), name="Home"),
    path("signup/", UserCreateView.as_view(), name="Signup"),
    path("verify-otp/", VerifyOtpView.as_view(), name="VerifyOtp"),
    path("resend-otp/", RegenerateOtpView.as_view(), name="RegenerateOtp"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="ForgotPasswordView")
]