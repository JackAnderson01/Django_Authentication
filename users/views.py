from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from . import serializers
from .models import User
import random
from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password
from .utils import sendOtp
from django.utils import timezone
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.conf import settings
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


# Create your views here.
class HomeView(generics.GenericAPIView):
    def get(self, request):
        return Response(data={"message": "You're welcome"}, status=status.HTTP_200_OK)

class UserCreateView(generics.CreateAPIView):
    serializer_class = serializers.UserCreateSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            verified_user = User.objects.filter(email=serializer.validated_data.get('email'), is_verified=True)
            non_verified_user = User.objects.filter(email=serializer.validated_data.get('email'), is_verified=False or None)
            # otp creation:
            otp = random.randint(100000, 999999)
            otp_expiry = datetime.now() + timedelta(minutes=10)
            email = serializer.validated_data.get('email')
            password = serializer.validated_data.get('password')
            name = serializer.validated_data.get('name')

            if(non_verified_user.exists()):

                try:
                    user = non_verified_user.update(email=email, name=name,password=make_password(password), otp=otp, otp_expiry=otp_expiry)
                    
                    try:
                        sendOtp(otp, email, name)
                        return Response(data={"message": f"OTP Sent to {email}"}, status=status.HTTP_200_OK)
                    except Exception as e:
                        return Response(data={"error":f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    return Response(data={"error":f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    

            
            if (verified_user.exists()):
                return Response(data={"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                user = User.objects.create_user(email=email, password=password, name=name, otp=otp, otp_expiry=otp_expiry)
                try:
                    sendOtp(otp, email, name)
                    return Response(data={"message": f"OTP Sent to {email}"}, status=status.HTTP_201_CREATED)
                except Exception as e:
                    return Response(data={"error":f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response(data={"error":f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data={"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
class VerifyOtpView(generics.CreateAPIView):
    serializer_class = serializers.VerifyOtpSerializer

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            email_exists = User.objects.filter(email=serializer.validated_data.get('email'))
            if(email_exists.exists()):

                # Finding out non verified user
                non_verified_user = User.objects.filter(otp=serializer.validated_data.get('otp'), is_verified=False or None)
                # Finding verified user
                verified_user = User.objects.filter(otp=serializer.validated_data.get('otp'), is_verified=True)

                if(not verified_user.exists() and not non_verified_user.exists()):
                    return Response(data={"error": "Invalid Otp"}, status=status.HTTP_400_BAD_REQUEST)

                # Functionality if user is already verified.
                if(verified_user.exists()):
                    return Response(data={"error": f"User Already Verified. Please Login Instead."}, status=status.HTTP_400_BAD_REQUEST)
                

                # Functionality if the user is not verified.
                if(non_verified_user.exists()):
                    # Taking the first object of the queryset
                    user = non_verified_user.first()

                    # If otp has expired sending an error:
                    if(user.otp_expiry and timezone.now() > user.otp_expiry):
                        return Response(data={"error": f"Otp expired get a new one."}, status=status.HTTP_401_UNAUTHORIZED)

                    # Checking if all the conditions for otp verification has met.
                    if(user.otp == serializer.validated_data.get('otp') and user.otp_expiry and timezone.now() < user.otp_expiry
                    ):
                        non_verified_user.update(is_active=True, is_verified=True, otp="xxx" ,otp_expiry=None, max_otp_try=settings.MAX_OTP_TRY, otp_max_out=None)
                        return Response(data={"message": f"User Successfully Verified."}, status=status.HTTP_200_OK)
                
            
            return Response(data={"error": f"Invalid Email."}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Functionality if user has provided data in incorrect format.
        return Response(data={"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
class RegenerateOtpView(generics.CreateAPIView):
    serializer_class=serializers.RegenerateOtpSerializer

    def post(self, request):
        data=request.data

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            non_verified_user = User.objects.filter(email=serializer.validated_data.get('email'))
            
            if(non_verified_user.exists()):
                user = non_verified_user.first()
                

                if int(user.max_otp_try) == 0 and timezone.now() < user.otp_max_out:
                    return Response(data={"error": f"You've reached otp try limit. Please try again after {user.otp_max_out.strftime('%H:%M:%S')}"},status=status.HTTP_400_BAD_REQUEST
                    )
        
                # otp regenration:
                otp = random.randint(100000, 999999)
                otp_expiry = datetime.now() + timedelta(minutes=10)
                max_otp_try = int(user.max_otp_try ) - 1


                non_verified_user.update(otp = otp)
                non_verified_user.update(otp_expiry = otp_expiry)
                non_verified_user.update(max_otp_try = max_otp_try)

                if max_otp_try == 0:
                    non_verified_user.update(otp_max_out = timezone.now() + timedelta(minutes=15))

                elif max_otp_try == -1:
                    non_verified_user.update(max_otp_try = settings.MAX_OTP_TRY)

                else:
                    non_verified_user.update(otp_max_out = None)
                    non_verified_user.update(max_otp_try = max_otp_try)
                
                sendOtp(otp, user.email, user.name)
                return Response(data={"message":"Otp Successfully regenerated"}, status=status.HTTP_200_OK)
            
            else:
                return Response(data={"error": "No user associated with this email"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(data={"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
class ForgotPasswordView(generics.CreateAPIView):
    serializer_class = serializers.ForgotPasswordSerializer

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            forgot_user = User.objects.filter(email=serializer.validated_data.get("email"))
            if(forgot_user.exists()):
                user = forgot_user.first()
                otp = random.randint(100000, 999999)
                otp_expiry = datetime.now() + timedelta(minutes=10)
                forgot_user.update(otp=otp, otp_expiry=otp_expiry)
                sendOtp(otp, user.email, user.name)
                return Response(data={"message": f"Otp sent to {user.email}"}, status=status.HTTP_200_OK)
            
            return Response(data={"error": "Email not yet registered."}, status=status.HTTP_400_BAD_REQUEST)
            # need to work on change pass email being sent upon hitting the forgot pass api rightnow.
        
        return Response(data={"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
      
class VerifyForgotOtpView(generics.CreateAPIView):
    serializer_class = serializers.VerifyForgotOtpSerializer

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            email_exists = User.objects.filter(email=serializer.validated_data.get('email'))
            if(email_exists.exists()):

                # Finding out the user that have the same otp
                non_verified_user = User.objects.filter(otp=serializer.validated_data.get('otp'))
                

                if(not non_verified_user.exists()):
                    return Response(data={"error": "Invalid Otp"}, status=status.HTTP_400_BAD_REQUEST)

               

                # Functionality if the user is not verified.
                if(non_verified_user.exists()):
                    # Taking the first object of the queryset
                    user = non_verified_user.first()

                    # If otp has expired sending an error:
                    if(user.otp_expiry and timezone.now() > user.otp_expiry):
                        return Response(data={"error": f"Otp expired get a new one."}, status=status.HTTP_401_UNAUTHORIZED)

                    # Checking if all the conditions for otp verification has met.
                    if(user.otp == serializer.validated_data.get('otp') and user.otp_expiry and timezone.now() < user.otp_expiry
                    ):
                        non_verified_user.update(is_active=True, is_verified=True, otp=serializer.validated_data.get('otp'), otp_expiry=None, max_otp_try=settings.MAX_OTP_TRY, otp_max_out=None)
                        return Response(data={"message": f"User Successfully Verified."}, status=status.HTTP_200_OK)
                
            
            return Response(data={"error": f"Invalid Email."}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Functionality if user has provided data in incorrect format.
        return Response(data={"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(generics.CreateAPIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            if(token):
                token.blacklist()
                return Response(data={"message": "Logged out successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
                return Response(data={"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

class ValidateTokenView(generics.CreateAPIView):
    serializer_class = serializers.ValidateTokenSerializer

    def post(self, request):
        data = request.data
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            token = serializer.validated_data.get('token')
            try:
                # Verify the token using the settings SECRET_KEY
                AccessToken(token)
                return Response(data={"message": "Token is Valid"}, status=status.HTTP_200_OK)
            except (InvalidToken, TokenError):
                # Token is invalid
                return Response(data={"error": "Token is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(data={"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(generics.CreateAPIView):
    serializer_class = serializers.ChangePasswordSerializer

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            email_exists = User.objects.filter(email=serializer.validated_data.get('email'))
            if(email_exists.exists()):

                # Finding out the user that have the same otp
                change_pass_user = User.objects.filter(otp=serializer.validated_data.get('otp'))
                

                if(not change_pass_user.exists()):
                    return Response(data={"error": "Invalid Otp Provided."}, status=status.HTTP_400_BAD_REQUEST)

               

                # Functionality if the user is not verified.
                if(change_pass_user.exists()):
                    # Taking the first object of the queryset
                    user = change_pass_user.first()

                    # Checking if all the conditions for otp verification has met.
                    if(user.otp == serializer.validated_data.get('otp')):
                        change_pass_user.update(is_active=True, is_verified=True,otp="xxx", password=make_password(serializer.validated_data.get('password')))
                        return Response(data={"message": f"Password updated successfully"}, status=status.HTTP_200_OK)
                
            
            return Response(data={"error": f"Invalid Email."}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Functionality if user has provided data in incorrect format.
        return Response(data={"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
