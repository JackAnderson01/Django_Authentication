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
                # non_verified_user.delete()

                # serializer = self.serializer_class(data=request.data)

                # if serializer.is_valid():
                # otp creation:
                # otp = random.randint(100000, 999999)
                # otp_expiry = datetime.now() + timedelta(minutes=10)
                # email = data.get('email')
                # password = data.get('password')
                # name = data.get('name')
                try:
                    user = non_verified_user.update(email=email, name=name,password=make_password(password), otp=otp, otp_expiry=otp_expiry)
                    
                    try:
                        sendOtp(otp, email, name)
                        return Response(data={"message": f"OTP Sent to {email}"}, status=status.HTTP_200_OK)
                    except Exception as e:
                        print("Upper", e)
                        return Response(data={"error":f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    print("Lower", e)
                    return Response(data={"error":f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    

                # return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            if (verified_user.exists()):
                return Response(data={"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)



            
            try:
                user = User.objects.create_user(email=email, password=password, name=name, otp=otp, otp_expiry=otp_expiry)
                try:
                    sendOtp(otp, email, name)
                    return Response(data={"message": f"OTP Sent to {email}"}, status=status.HTTP_201_CREATED)
                except Exception as e:
                    print("Upper", e)
                    return Response(data={"error":f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                print("Lower", e)
                return Response(data={"error":f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
class VerifyOtpView(generics.CreateAPIView):
    serializer_class = serializers.VerifyOtpSerializer

    def post(self, request):
        data = request.data

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            email_exists = User.objects.filter(email=serializer.validated_data.get('email'))
            print(email_exists.exists())
            if(email_exists.exists()):

                # Finding out non verified user
                non_verified_user = User.objects.filter(otp=serializer.validated_data.get('otp'), is_verified=False or None)
                # Finding verified user
                verified_user = User.objects.filter(otp=serializer.validated_data.get('otp'), is_verified=True)

                if(not verified_user.exists() and not non_verified_user.exists()):
                    return Response(data={"message": "Invalid Otp"}, status=status.HTTP_400_BAD_REQUEST)

                # Functionality if user is already verified.
                if(verified_user.exists()):
                    return Response(data={"message": f"User Already Verified. Please Login Instead."}, status=status.HTTP_400_BAD_REQUEST)
                

                # Functionality if the user is not verified.
                if(non_verified_user.exists()):
                    # Taking the first object of the queryset
                    user = non_verified_user.first()

                    # If otp has expired sending an error:
                    if(timezone.now() > user.otp_expiry):
                        return Response(data={"message": f"Otp expired get a new one."}, status=status.HTTP_401_UNAUTHORIZED)

                    # Checking if all the conditions for otp verification has met.
                    if(user.otp == serializer.validated_data.get('otp') and user.otp_expiry and timezone.now() < user.otp_expiry
                    ):
                        non_verified_user.update(is_verified=True, otp_expiry=None, max_otp_try=settings.MAX_OTP_TRY, otp_max_out=None)
                        return Response(data={"message": f"User Successfully Verified."}, status=status.HTTP_200_OK)
                
            
            return Response(data={"message": f"Invalid Email."}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Functionality if user has provided data in incorrect format.
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class RegenrateOtpView(generics.CreateAPIView):
    serializer_class=serializers.RegeenrateOtpSerializer

    def post(self, request):
        data=request.data

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            non_verified_user = User.objects.filter(email=serializer.validated_data.get('email'))
            
            if(non_verified_user.exists()):
                user = non_verified_user.first()
                

                if int(user.max_otp_try) == 0 and timezone.now() < user.otp_max_out:
                    return Response(
                    "You've reached otp try limit. Please try again after an hour",
                    status=status.HTTP_400_BAD_REQUEST
                    )
        
                # otp regenration:
                otp = random.randint(100000, 999999)
                otp_expiry = datetime.now() + timedelta(minutes=10)
                max_otp_try = int(user.max_otp_try ) - 1


                non_verified_user.update(otp = otp)
                non_verified_user.update(otp_expiry = otp_expiry)
                non_verified_user.update(max_otp_try = max_otp_try)

                if max_otp_try == 0:
                    non_verified_user.update(otp_max_out = timezone.now() + timedelta(minutes=1))

                elif max_otp_try == -1:
                    non_verified_user.update(max_otp_try = settings.MAX_OTP_TRY)

                else:
                    non_verified_user.update(otp_max_out = None)
                    non_verified_user.update(max_otp_try = max_otp_try)
                
                return Response("Otp Successfully regenerated", status=status.HTTP_200_OK)
            
            else:
                return Response("No user associated with this email", status=status.HTTP_400_BAD_REQUEST)
                
