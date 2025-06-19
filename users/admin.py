from .models import *
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm

class CustomUserCreationFom(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email')
        
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationFom
    model = User
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
                'fields': (
                    'username',
                    'email',
                    'password1',
                    'password2',
                    'is_staff',
                    'is_superuser',
                    'is_active'
                )
            }
        ),
    )
    list_display = ('username', 'email', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email')
    
    
admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile)
