from .models import *
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm

class CustomUserCreationFom(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'number_id', 'email')
        
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationFom
    model = User
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
                'fields': (
                    'username',
                    'number_id',
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
    fieldsets = UserAdmin.fieldsets + (
        ('Aditional Infortmation', {'fields': ('number_id',)}),
    )
    list_display = ('username', 'email', 'number_id', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'number_id', 'email')
    
    
admin.site.register(User, CustomUserAdmin)
