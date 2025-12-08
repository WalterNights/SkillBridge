from rest_framework import serializers

from users.models import User, UserProfile

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
    user = UserSerializer(read_only=True)
    phone_code = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True)
    
    
    class Meta:
        model = UserProfile
        fields = [
            'user',
            'first_name', 
            'last_name',
            'number_id',
            'phone_code',
            'phone_number',
            'phone', 
            'city',
            'professional_title',
            'summary',
            'education', 
            'skills', 
            'experience', 
            'resume', 
            'linkedin_url', 
            'portfolio_url'
            ]
        read_only_fields = ['phone']
        
    def validate_linkedin_url(self, value):
        if value and not value.startswith(("https://www")):
            value = f"https://www.{value}"
        return value
        
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
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.phone:
            parts = instance.phone.strip().split()
            if len(parts) >= 2:
                rep["phone_code"] = parts[0]
                rep["phone_number"] = " ".join(parts[1:])
        return rep