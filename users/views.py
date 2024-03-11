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
            non_verified_user = User.objects.filter(email=serializer.validated_data.get('email'), otp=serializer.validated_data.get('otp'), is_verified=False or None)
            verified_user = User.objects.filter(email=serializer.validated_data.get('email'), otp=serializer.validated_data.get('otp'), is_verified=True)
            if(non_verified_user.exists()):
                non_verified_user.update(is_verified=True)
                return Response(data={"message": f"User Successfully Verified."})
            if(verified_user.exists()):
                return Response(data={"message": f"User Already Verified. Please Login Instead."})
            else:
                return Response(data={"message": f"Invalid Email or Otp provided."})
            
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        