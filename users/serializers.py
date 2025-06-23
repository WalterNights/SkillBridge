from .models import *
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'rol']
        
    def create(self, validate_data):
        password = validate_data.pop('password')
        user = User(**validate_data)
        user.set_password(password)
        user.save()
        UserProfile.objects.create(user=user)
        return user
        

class UserProfileSerializer(serializers.ModelSerializer):
    phone_code = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'first_name', 
            'last_name',
            'number_id',
            'phone_code',
            'phone_number',
            'phone', 
            'city', 
            'education', 
            'skills', 
            'experience', 
            'resume', 
            'linkedin_url', 
            'portfolio_url'
            ]
        read_only_fields = ['phone']
        
    def create(self, validate_data):
        phone_code = validate_data.pop("phone_code")
        phone_number = validate_data.pop("phone_number")
        validate_data["phone"] = f"{phone_code} {phone_number}"
        return super().create(validate_data)
    
    def update(self, instance, validate_data):
        phone_code = validate_data.pop("phone_code", None)
        phone_number = validate_data.pop("phone_number", None)
        if phone_code and phone_number:
            validate_data["phone"] = f"{phone_code} {phone_number}"
        return super().update(instance, validate_data)