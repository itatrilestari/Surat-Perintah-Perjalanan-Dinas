from django.urls import path, include
from sppd.views import (
    master_data_views
)

urlpatterns = [
    path('master-data/', include([
        path('travel-purpose/', master_data_views.MasterDataTravelPurposeListAPIView.as_view(), name='master-data-travel-purpose'),
        path('transportation/', master_data_views.MasterDataTransportationListAPIView.as_view(), name='master-data-transportation'),
        path('cost-category/', master_data_views.MasterDataCostCategoryListAPIView.as_view(), name='master-data-cost-category'),
        path('budget-account/', master_data_views.MasterDataBudgetAccountListAPIView.as_view(), name='master-data-budget-account'),
        path('destination/', master_data_views.MasterDataDestinationListAPIView.as_view(), name='master-data-destination'),
    ])),
]
