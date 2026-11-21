from django.db import transaction
from rest_framework import generics
from apps.api.utils import CustomPagination
from sppd.models import TravelPurpose, Transportation, SBMMaster, BudgetAccount, Destination
from sppd.serializers.master_data_serializers import *

class MasterDataTravelPurposeListAPIView(generics.ListAPIView):
    pagination_class = CustomPagination
    serializer_class = MasterDataTravelPusposeSerializer
    queryset = TravelPurpose.objects.filter(is_delete=False)
    
class MasterDataTransportationListAPIView(generics.ListAPIView):
    pagination_class = CustomPagination
    serializer_class = MasterDataTransportationSerializer
    queryset = Transportation.objects.filter(is_delete=False)

class MasterDataCostCategoryListAPIView(generics.ListAPIView):
    pagination_class = CustomPagination
    serializer_class = MasterDataCostCategorySerializer
    queryset = SBMMaster.objects.filter(is_delete=False)

class MasterDataBudgetAccountListAPIView(generics.ListAPIView):
    pagination_class = CustomPagination
    serializer_class = MasterDataBudgetAccountSerializer
    queryset = BudgetAccount.objects.filter(is_delete=False)

class MasterDataDestinationListAPIView(generics.ListAPIView):
    pagination_class = CustomPagination
    serializer_class = MasterDataDestinationSerializer
    queryset = Destination.objects.filter(is_delete=False).order_by('name')