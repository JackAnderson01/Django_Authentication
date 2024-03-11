from django.core.mail import send_mail





def sendOtp(otp, email, name):
    subject = "HRMS | Verification code"
    message = f"Dear {name}, \nPlease use the verification code below to sign in. \n{otp} \nIf you didn’t request this, you can ignore this email. \nThanks,\nThe HRMS team"
    from_email = 'professorcoding123@gmail.com'
    recipient_list = [email]


    send_mail(subject, message, from_email, recipient_list)

    
