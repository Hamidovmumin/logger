from django.core.mail import EmailMessage
from django.http import  HttpRequest
from utils.generator import generate_string
from django.core.cache import cache
from django.template.loader import render_to_string
from django.shortcuts import render
from celery import shared_task

@shared_task
def send_otp_email(email,code):
    message = render_to_string(
        "email_sms.html",
        {
            "code": code,
        }
    )

    mail = EmailMessage(
        "Doğrulama kodunuz!",
        message,
        to=[email]
    )

    mail.content_subtype = "html"
    mail.send()


def send_email_sms(
        request:HttpRequest,
        email_type:str,
        **kwargs
):
    if email_type == 'forgot_password':

        code = generate_string(length=6,digits=True)
        user = kwargs['account']
        cache_key = f"otp:{user.email}"

        if cache.get(cache_key):
            return {
                "status": False,
                "message": "Doğrulama kodu artıq göndərilib. Zəhmət olmasa 2 dəqiqə gözləyin."
            }

        cache.set(
            cache_key,
            value=code,
            timeout=120)

        send_otp_email.delay(email=user.email, code=code)

        return {
            "status": True,
            "message": "Kod email ünvanınıza göndərildi."
        }

