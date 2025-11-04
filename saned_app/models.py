from django.db import models
import re, bcrypt
from datetime import date

class UserManager(models.Manager):
    def user_validator(self, postdata):
        errors = {}
        EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

        first_name = postdata.get('registerFirstName', '').strip()
        last_name = postdata.get('registerLastName', '').strip()
        email = postdata.get('registerEmail', '').strip()
        password = postdata.get('registerPassword', '')
        repeat_password = postdata.get('registerRepeatPassword', '')
        region = postdata.get('registerRegion', '').strip()
        role = postdata.get('role', '').strip()

        if len(first_name) < 2 or not first_name.isalpha():
            errors['registerFirstName'] = "الاسم الأول يجب أن لا يقل عن حرفين ويحتوي فقط على أحرف"

        if len(last_name) < 2 or not last_name.isalpha():
            errors['registerLastName'] = "الاسم الأخير يجب أن لا يقل عن حرفين ويحتوي فقط على أحرف"

        if not EMAIL_REGEX.match(email):
            errors['registerEmail'] = "البريد الإلكتروني غير صالح"
        elif User.objects.filter(email=email).exists():
            errors['registerEmail'] = "البريد الإلكتروني مسجل مسبقًا"

        if len(password) < 8:
            errors['registerPassword'] = "كلمة المرور يجب أن لا تقل عن 8 أحرف"

        if repeat_password != password:
            errors['registerRepeatPassword'] = "كلمتا المرور غير متطابقتين"

        if role != 'donor' and not region:
            errors['registerRegion'] = "يرجى اختيار المدينة"

        return errors


    def login_validator(self, postdata):
        errors = {}
        email = postdata.get('loginEmail', '').strip()
        password = postdata.get('loginPassword', '')

        if not email or not password:
            errors['login'] = "البريد الإلكتروني وكلمة المرور مطلوبة"
            return errors

        user = User.objects.filter(email=email).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
            errors['login'] = "البريد الإلكتروني أو كلمة المرور غير صحيحة"
        return errors

class User(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    region = models.CharField(max_length=100, null=True, blank=True)
    role = models.CharField(max_length=45, choices=[
        ('beneficiary', 'Beneficiary'),
        ('donor', 'Donor'),
        ('ngo', 'NGO'),
        ('admin', 'Admin')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.role}"


class NGOProfile(models.Model):
    organization_name = models.CharField(max_length=100)
    license_document = models.FileField(upload_to='documents/')
    approved = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ngo_profiles")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AidRequest(models.Model):
    type = models.CharField(max_length=45)
    description = models.TextField()
    amount_requested = models.IntegerField()
    document = models.FileField(upload_to='documents/')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delivered', 'Delivered'),
    ], default='pending')
    beneficiary = models.ForeignKey(User, on_delete=models.CASCADE, related_name="aid_requests")
    ngo = models.ForeignKey(NGOProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Campaign(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    goal_amount = models.IntegerField()
    deadline = models.DateField()
    ngo = models.ForeignKey(NGOProfile, on_delete=models.CASCADE, related_name="campaigns")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Donation(models.Model):
    amount = models.IntegerField()
    anonymous = models.BooleanField(default=False)
    message = models.TextField(blank=True, null=True)
    donation_method = models.CharField(max_length=45)
    donor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="donations")
    request = models.ForeignKey(AidRequest, on_delete=models.CASCADE, related_name="donations", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CampaignDonation(models.Model):
    donor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="campaign_donations")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="campaign_donations")
    amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


