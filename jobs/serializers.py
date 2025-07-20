from .models import JobOffer
from rest_framework import serializers

class JobOfferSerializer(serializers.ModelSerializer):
    matched_skills = serializers.SerializerMethodField()
    missing_skills = serializers.SerializerMethodField()
    match_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = JobOffer
        fields = '__all__'
        extra_fields = ['matched_skills', 'missing_skills', 'match_percentage']
        
    def get_match_percentage(self, job):
        return getattr(job, 'match_percentage', None)
    
    
    def get_matched_skills(self, job):
        return getattr(job, 'matched_skills', [])
    
    
    def get_missing_skills(self, job):
        return getattr(job, 'missing_skills', [])