from django.contrib import admin
from .models import User, NGOProfile, AidRequest, Campaign, Donation, CampaignDonation


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'role', 'region', 'created_at')
    list_filter = ('role', 'region')
    search_fields = ('first_name', 'last_name', 'email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(NGOProfile)
class NGOProfileAdmin(admin.ModelAdmin):
    exclude = ('user',)
    list_display = ('organization_name', 'user', 'approved')
    list_filter = ('approved',)
    search_fields = ('organization_name', 'user__email')
    readonly_fields = ('license_document', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not change and not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(AidRequest)
class AidRequestAdmin(admin.ModelAdmin):
    list_display = ('type', 'amount_requested', 'status', 'beneficiary', 'created_at')
    list_filter = ('status',)
    search_fields = ('type', 'description', 'beneficiary__email')
    readonly_fields = ('document', 'created_at', 'updated_at')


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'ngo', 'goal_amount', 'deadline', 'created_at')
    list_filter = ('deadline',)
    search_fields = ('title', 'ngo__organization_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('donor', 'request', 'amount', 'donation_method', 'anonymous', 'created_at')
    list_filter = ('donation_method', 'anonymous')
    search_fields = ('donor__email', 'request__type')
    readonly_fields = ('created_at',)


@admin.register(CampaignDonation)
class CampaignDonationAdmin(admin.ModelAdmin):
    list_display = ('donor', 'campaign', 'amount', 'created_at')
    search_fields = ('donor__email', 'campaign__title')
    readonly_fields = ('created_at',)
