from django.shortcuts import render, redirect
from .models import *
from django.http import JsonResponse, HttpResponseForbidden,HttpResponse
from django.contrib import messages
from django.utils import timezone
import bcrypt, json
from django.views.decorators.http import require_POST
from django.db.models import Sum, F,Q,Count
from django.utils.timezone import now
from django.utils.html import escape
from django.db.models.functions import TruncMonth
from django.db.models.functions import Concat
import pandas as pd

def index(request):
    return render(request, 'index.html')


def register(request):
    cities = [
        "القدس", "رام الله", "البيرة", "نابلس", "الخليل", "بيت لحم",
        "قلقيلية", "طولكرم", "جنين", "سلفيت", "أريحا", "طوباس"
    ]
    return render(request, 'auth/register.html', {'cities': cities})


def login(request):
    return render(request, 'auth/login.html')

def logout_user(request):
    request.session.flush()
    return redirect('login')


def create_user(request):
    if request.method == 'POST':
        if request.content_type.startswith('multipart'):
            data = request.POST
            files = request.FILES
        else:
            data = json.loads(request.body)
            files = {}

        errors = User.objects.user_validator(data)

        if errors:
            return JsonResponse({'success': False, 'errors': errors})

        hashed_pw = bcrypt.hashpw(data['registerPassword'].encode(), bcrypt.gensalt()).decode()
        role = data.get('role', 'beneficiary')
        region_value = data.get('registerRegion') if role != 'donor' else None

        user = User.objects.create(
            first_name=data['registerFirstName'],
            last_name=data['registerLastName'],
            email=data['registerEmail'],
            region=region_value,
            password=hashed_pw,
            role=role
        )

        if role == 'ngo' and files.get('licenseDocument'):
            NGOProfile.objects.create(
                organization_name=f"{user.first_name} {user.last_name}",
                license_document=files['licenseDocument'],
                user=user
            )

        request.session['user_id'] = user.id
        request.session['name'] = f"{user.first_name} {user.last_name}"

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'errors': {'general': 'طلب غير صالح'}})


def login_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'errors': {'general': 'بيانات غير صالحة'}})

        errors = User.objects.login_validator(data)

        if errors:
            return JsonResponse({'success': False, 'errors': errors})

        user = User.objects.filter(email=data['loginEmail']).first()

        request.session['user_id'] = user.id
        request.session['role'] = user.role
        request.session['name'] = f"{user.first_name} {user.last_name}"

        if user.role == 'beneficiary':
            redirect_url = '/beneficiary/dashboard'
        elif user.role == 'donor':
            redirect_url = '/donor/dashboard'
        elif user.role == 'ngo':
            ngo_profile = NGOProfile.objects.filter(user=user).first()
            if not ngo_profile or not ngo_profile.approved:
                redirect_url = '/ngo/pending-approval/'
            else:
                redirect_url = '/ngo/dashboard'
        else:
            redirect_url = '/'

        return JsonResponse({'success': True, 'redirect_url': redirect_url})

    return JsonResponse({'success': False, 'errors': {'general': 'طلب غير صالح'}})


def beneficiary_dashboard(request):
    if 'user_id' not in request.session or request.session.get('role') != 'beneficiary':
        return redirect('login')
    user_id = request.session.get('user_id')
    recent_requests = AidRequest.objects.filter(beneficiary_id=user_id).order_by('-created_at')[:3]
    return render(request, 'beneficiary/dashboard.html', {'recent_requests': recent_requests})


def my_requests(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user = User.objects.get(id=request.session['user_id'])
    if user.role != 'beneficiary':
        return redirect('/')

    aid_requests = AidRequest.objects.filter(beneficiary=user).order_by('-created_at')
    return render(request, 'beneficiary/my_requests.html', {'aid_requests': aid_requests})


def aid_request_form(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user = User.objects.filter(id=request.session['user_id']).first()
    if not user or user.role != 'beneficiary':
        return HttpResponseForbidden("ليس لديك صلاحية الوصول إلى هذه الصفحة.")

    return render(request, 'beneficiary/aid_request_form.html')


def submit_aid_request(request):
    if request.method == 'POST':
        if 'user_id' not in request.session:
            return redirect('login')

        user = User.objects.filter(id=request.session['user_id']).first()
        if not user or user.role != 'beneficiary':
            return HttpResponseForbidden("ليس لديك صلاحية.")

        type = request.POST.get('type', '').strip()
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '').strip()
        document = request.FILES.get('document')

        errors = {}
        if not type:
            errors['type'] = "يرجى كتابة نوع المساعدة المطلوبة"
        if not description:
            errors['description'] = "يرجى إدخال وصف للمساعدة"
        if not amount.isdigit():
            errors['amount'] = "يرجى إدخال مبلغ صحيح"
        if not document:
            errors['document'] = "يرجى رفع مستند يوضح الحالة"

        if errors:
            return render(request, 'beneficiary/aid_request_form.html', {'errors': errors})

        AidRequest.objects.create(
            type=type,
            description=description,
            amount_requested=int(amount),
            document=document,
            beneficiary=user
        )

        return redirect('beneficiary_dashboard')

    return HttpResponseForbidden("طريقة غير مسموح بها.")


def delete_aid_request(request, request_id):
    if 'user_id' not in request.session or request.session.get('role') != 'beneficiary':
        return redirect('login')

    aid_request = AidRequest.objects.filter(id=request_id, beneficiary_id=request.session['user_id']).first()

    if not aid_request:
        messages.error(request, "الطلب غير موجود أو غير مسموح لك بحذفه.")
        return redirect('my_requests')

    if aid_request.status != 'pending':
        messages.error(request, "لا يمكنك حذف طلب تمت مراجعته أو الموافقة عليه.")
        return redirect('my_requests')

    aid_request.delete()
    messages.success(request, "تم حذف الطلب بنجاح.")
    return redirect('my_requests')

def pending_approval(request):
    return render(request, 'ngo/pending_approval.html')

def check_ngo_approval(request):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return JsonResponse({'approved': False})

    user = User.objects.get(id=request.session['user_id'])
    ngo_profile = NGOProfile.objects.filter(user=user).first()
    return JsonResponse({'approved': ngo_profile.approved if ngo_profile else False})


def ngo_dashboard(request):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    user = User.objects.get(id=request.session['user_id'])
    ngo_profile = NGOProfile.objects.get(user=user)

    campaigns = Campaign.objects.filter(ngo=ngo_profile)
    total_campaigns = campaigns.count()

    adopted_requests = AidRequest.objects.filter(ngo=ngo_profile)
    adopted_count = adopted_requests.count()

    regions = [r.strip() for r in user.region.split(',') if r.strip()]
    region_requests_count = AidRequest.objects.filter(
        beneficiary__region__in=regions,
        ngo__isnull=True,
    ).exclude(status='rejected').count()


    total_donations = CampaignDonation.objects.filter(
        campaign__ngo=ngo_profile
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    ongoing_campaigns = []
    for campaign in campaigns:
        donated = CampaignDonation.objects.filter(campaign=campaign).aggregate(Sum('amount'))['amount__sum'] or 0
        remaining = campaign.goal_amount - donated

        if remaining > 0 and campaign.deadline >= now().date():
            ongoing_campaigns.append({
                'title': campaign.title,
                'deadline': campaign.deadline,
                'goal': campaign.goal_amount,
                'donated': donated,
                'remaining': remaining
            })

    adopted_requests_data = []
    for req in adopted_requests:
        donated = Donation.objects.filter(request=req).aggregate(Sum('amount'))['amount__sum'] or 0
        remaining = req.amount_requested - donated

        if donated >= req.amount_requested and req.status != 'delivered':
            req.status = 'delivered'
            req.save()

        adopted_requests_data.append({
            'type': req.type,
            'description': req.description,
            'amount_requested': req.amount_requested,
            'donated': donated,
            'remaining': remaining,
            'status': req.status
        })

    context = {
        'profile': ngo_profile,
        'total_campaigns': total_campaigns,
        'adopted_requests_count': adopted_count,
        'region_requests_count': region_requests_count,
        'total_donations': total_donations,
        'ongoing_campaigns': ongoing_campaigns,
        'adopted_requests_data': adopted_requests_data,
    }

    return render(request, 'ngo/dashboard.html', context)


def region_requests(request):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    ngo_user = User.objects.get(id=request.session['user_id'])
    regions = [r.strip() for r in ngo_user.region.split(',') if r.strip()]

    aid_requests = AidRequest.objects.filter(
        beneficiary__region__in=regions,
        status='pending'  
    ).order_by('-created_at')

    return render(request, 'ngo/region_requests.html', {
        'aid_requests': aid_requests,
        'region_list': regions
    })


@require_POST
def approve_aid_request(request, request_id):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    aid_request = AidRequest.objects.filter(id=request_id, status='pending').first()
    if aid_request:
        aid_request.ngo = NGOProfile.objects.get(user_id=request.session['user_id'])
        aid_request.status = 'approved'
        aid_request.save()
    return redirect('region_requests')


@require_POST
def reject_aid_request(request, request_id):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    aid_request = AidRequest.objects.filter(id=request_id, status='pending').first()
    if aid_request:
        aid_request.status = 'rejected'
        aid_request.save()
    return redirect('region_requests')



def adopted_requests(request):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    ngo_user = User.objects.get(id=request.session['user_id'])
    ngo_profile = NGOProfile.objects.filter(user=ngo_user).first()

    adopted_requests = AidRequest.objects.filter(
        ngo=ngo_profile,
        status='approved'
    ).order_by('-created_at')

    for req in adopted_requests:
        total_donated = req.donations.aggregate(Sum('amount'))['amount__sum'] or 0
        req.total_donated = total_donated
        req.is_funded = total_donated >= req.amount_requested
        req.percentage = min(int((total_donated / req.amount_requested) * 100), 100) if req.amount_requested else 0

    return render(request, 'ngo/adopted_requests.html', {
        'adopted_requests': adopted_requests
    })

def my_campaigns(request):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    user = User.objects.get(id=request.session['user_id'])
    ngo_profile = NGOProfile.objects.filter(user=user).first()

    if not ngo_profile:
        messages.error(request, "لا يمكنك عرض الحملات لأن الجمعية غير معتمدة.")
        return redirect('ngo_dashboard')

    campaigns = Campaign.objects.filter(ngo=ngo_profile).order_by('-created_at')

    for campaign in campaigns:
        total = campaign.campaign_donations.aggregate(Sum('amount'))['amount__sum'] or 0
        campaign.total_donated = total
        campaign.is_completed = total >= campaign.goal_amount
        campaign.percentage = min(int((total / campaign.goal_amount) * 100), 100) if campaign.goal_amount else 0

    return render(request, 'ngo/my_campaigns.html', {'campaigns': campaigns})


def create_campaign_form(request):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    return render(request, 'ngo/create_campaign.html')


def create_campaign_submit(request):
    if request.method != 'POST':
        return redirect('create_campaign_form')

    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    user = User.objects.get(id=request.session['user_id'])
    ngo_profile = NGOProfile.objects.filter(user=user, approved=True).first()

    if not ngo_profile:
        messages.error(request, "لا يمكنك إنشاء حملة حتى يتم اعتماد الجمعية.")
        return redirect('ngo_dashboard')

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    goal_amount = request.POST.get('goal_amount', '').strip()
    deadline = request.POST.get('deadline', '').strip()

    Campaign.objects.create(
        title=title,
        description=description,
        goal_amount=int(goal_amount),
        deadline=deadline,
        ngo=ngo_profile
    )

    messages.success(request, "✅ تم إنشاء الحملة بنجاح.")
    return redirect('my_campaigns')


def donor_dashboard(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.filter(id=user_id, role='donor').first()
    if not user:
        return redirect('login')

    campaigns = Campaign.objects.annotate(
        total_donated=Sum('campaign_donations__amount')
    ).filter(
        deadline__gte=timezone.now().date()
    ).filter(
        Q(total_donated__lt=F('goal_amount')) | Q(total_donated__isnull=True)
    ).order_by('-deadline')

    aid_requests = AidRequest.objects.annotate(
        total_donated=Sum('donations__amount')
    ).filter(
        status='approved'
    ).filter(
        Q(total_donated__lt=F('amount_requested')) | Q(total_donated__isnull=True)
    ).order_by('-created_at')

    for campaign in campaigns:
        donated = campaign.total_donated or 0
        campaign.remaining_amount = max(campaign.goal_amount - donated, 0)

    for request_obj in aid_requests:
        donated = request_obj.total_donated or 0
        request_obj.remaining_amount = max(request_obj.amount_requested - donated, 0)

    campaign_donations = CampaignDonation.objects.filter(donor=user).order_by('-created_at')
    aid_donations = Donation.objects.filter(donor=user).order_by('-created_at')

    context = {
        'user': user,
        'campaigns': campaigns,
        'aid_requests': aid_requests,
        'campaign_donations': campaign_donations,
        'aid_donations': aid_donations
    }

    return render(request, 'donor/dashboard.html', context)

def donate_to_campaign(request, campaign_id):
    user_id = request.session.get('user_id')
    user = User.objects.filter(id=user_id).first()
    campaign = Campaign.objects.filter(id=campaign_id).first()

    if not campaign:
        return redirect('donor_dashboard')

    if request.method == "POST":
        amount = request.POST.get('amount')
        if not amount or not amount.isdigit() or int(amount) <= 0:
            return render(request, 'donor/payment_confirmed.html', {
                'campaign': campaign,
                'errors': {'amount': 'يرجى إدخال مبلغ صالح'}
            })

        CampaignDonation.objects.create(
            amount=int(amount),
            donor=user,
            campaign=campaign,
            created_at=timezone.now()
        )

        messages.success(request, f"🌟 شكرًا لك على تبرعك الكريم بمبلغ {amount} شيكل لحملة \"{campaign.title}\"! 🌟")
        return redirect('donor_dashboard')

    return render(request, 'donor/payment_confirmed.html', {
        'campaign': campaign,
    })

def donate_to_request(request, request_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.filter(id=user_id, role='donor').first()
    aid_request = AidRequest.objects.filter(id=request_id, status__in=['approved', 'delivered']).first()

    if not user or not aid_request:
        messages.error(request, "هذه الحالة غير متاحة أو لم يتم اعتمادها.")
        return redirect('donor_dashboard')

    if request.method == 'POST':
        amount = request.POST.get('amount', '').strip()
        error = None

        if not amount or not amount.isdigit() or int(amount) <= 0:
            error = 'يرجى إدخال مبلغ صالح للتبرع.'

        if error:
            return render(request, 'donor/donate_request.html', {
                'request': aid_request,
                'error': error
            })

        amount_int = int(amount)

        Donation.objects.create(
            donor=user,
            request=aid_request,
            amount=amount_int,
            donation_method='direct',
            created_at=timezone.now()
        )

        total_donated = aid_request.donations.aggregate(Sum('amount'))['amount__sum'] or 0
        if total_donated >= aid_request.amount_requested:
            aid_request.status = 'delivered'
            aid_request.save()

        messages.success(request, f"🌟 شكرًا لك على تبرعك الكريم بمبلغ {amount} شيكل.")
        return redirect('donor_dashboard')

    return render(request, 'donor/donate_request.html', {
        'request': aid_request
    })



def all_campaigns(request):
    campaigns = Campaign.objects.annotate(
        total_donated=Sum('campaign_donations__amount')
    ).filter(
        deadline__gte=timezone.now().date()
    ).filter(
        Q(total_donated__lt=F('goal_amount')) | Q(total_donated__isnull=True)
    ).order_by('deadline')

    return render(request, 'campaign/all_campaigns.html', {'campaigns': campaigns})

def about_us(request):
    return render(request, 'about_us.html')

def export_donations_excel(request):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    user = User.objects.get(id=request.session['user_id'])
    ngo = NGOProfile.objects.get(user=user)

    donations = CampaignDonation.objects.filter(campaign__ngo=ngo).select_related('campaign', 'donor')

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=donations.xls'

    html = """
    <html>
    <head><meta charset="UTF-8"></head>
    <body>
    <table border="1">
        <thead>
            <tr>
                <th>الحملة</th>
                <th>المتبرع</th>
                <th>المبلغ</th>
                <th>التاريخ</th>
            </tr>
        </thead>
        <tbody>
    """

    for d in donations:
        html += f"""
            <tr>
                <td>{escape(d.campaign.title)}</td>
                <td>{escape(d.donor.first_name)} {escape(d.donor.last_name)}</td>
                <td>{d.amount}</td>
                <td>{d.created_at.strftime('%Y-%m-%d')}</td>
            </tr>
        """

    html += """
        </tbody>
    </table>
    </body>
    </html>
    """

    response.write(html)
    return response

def export_requests_excel(request):
    if 'user_id' not in request.session or request.session.get('role') != 'ngo':
        return redirect('login')

    user = User.objects.get(id=request.session['user_id'])
    ngo = NGOProfile.objects.get(user=user)
    requests = AidRequest.objects.filter(ngo=ngo).select_related('beneficiary')

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=aid_requests.xls'

    html = """
    <html>
    <head><meta charset="UTF-8"></head>
    <body>
    <table border="1">
        <thead>
            <tr>
                <th>المستفيد</th>
                <th>النوع</th>
                <th>الوصف</th>
                <th>المبلغ المطلوب</th>
                <th>الحالة</th>
                <th>تاريخ الإنشاء</th>
            </tr>
        </thead>
        <tbody>
    """

    for r in requests:
        html += f"""
            <tr>
                <td>{escape(r.beneficiary.first_name)} {escape(r.beneficiary.last_name)}</td>
                <td>{escape(r.type)}</td>
                <td>{escape(r.description)}</td>
                <td>{r.amount_requested}</td>
                <td>{r.status}</td>
                <td>{r.created_at.strftime('%Y-%m-%d')}</td>
            </tr>
        """

    html += """
        </tbody>
    </table>
    </body>
    </html>
    """

    response.write(html)
    return response