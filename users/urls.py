from django.urls import path
from .views import HomeView, UserCreateView, VerifyOtpView, RegenrateOtpView


urlpatterns = [
    path("", HomeView.as_view(), name="Home"),
    path("signup/", UserCreateView.as_view(), name="Signup"),
    path("verify-otp/", VerifyOtpView.as_view(), name="VerifyOtp"),
    path("resend-otp/", RegenrateOtpView.as_view(), name="RegenerateOtp"),

]