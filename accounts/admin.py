from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('id', 'username', 'email', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'email')
    ordering = ('id',)

admin.site.register(CustomUser, CustomUserAdmin)

