from rest_framework import serializers
from django.db import transaction
from sppd.models import TravelPurpose, Transportation, SBMMaster, BudgetAccount, Destination
from django.contrib.auth.models import User

class MasterDataTravelPusposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelPurpose
        fields = "__all__"

class MasterDataTransportationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transportation
        fields = "__all__"

class MasterDataCostCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SBMMaster
        fields = "__all__"

class MasterDataBudgetAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetAccount
        fields = "__all__"

class MasterDataDestinationSerializer(serializers.ModelSerializer):
    id_province = serializers.SerializerMethodField()
    province = serializers.SerializerMethodField()
    id_city = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    class Meta:
        model = Destination
        fields = [
            "id_province",
            "province",
            "id_city",
            "city",
            "category"
        ]

    def get_id_province(self, obj):
        return str(obj.province.id)

    def get_province(self, obj):
        return obj.province.name

    def get_id_city(self, obj):
        return str(obj.id)

    def get_city(self, obj):
        return obj.name

    def get_category(self, obj):
        return obj.category