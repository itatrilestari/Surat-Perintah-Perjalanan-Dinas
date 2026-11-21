from django.urls import path, include
from sppd.views import (
    master_data_views,
    document_views
)

urlpatterns = [
    path('master-data/', include([
        path('travel-purpose/', master_data_views.MasterDataTravelPurposeListAPIView.as_view(), name='master-data-travel-purpose'),
        path('transportation/', master_data_views.MasterDataTransportationListAPIView.as_view(), name='master-data-transportation'),
        path('cost-category/', master_data_views.MasterDataCostCategoryListAPIView.as_view(), name='master-data-cost-category'),
        path('budget-account/', master_data_views.MasterDataBudgetAccountListAPIView.as_view(), name='master-data-budget-account'),
        path('destination/', master_data_views.MasterDataDestinationListAPIView.as_view(), name='master-data-destination'),
    ])),

    path('document/', include([
        path('', document_views.SPPDListCreateAPIView.as_view(), name='sppd-list-create'),
        path('<uuid:pk>/', document_views.SPPDRetrieveUpdateDestroyAPIView.as_view(), name='sppd-detail-update-delete'),
        path('<uuid:pk>/approve/', document_views.SPPDAPIView.as_view({'post': 'approve'}), name='sppd-approve'),
        path('<uuid:pk>/reject/', document_views.SPPDAPIView.as_view({'post': 'reject'}), name='sppd-reject'),
        path('<uuid:pk>/cancel/', document_views.SPPDAPIView.as_view({'post': 'cancel'}), name='sppd-cancel'),
        path('estimate-costs/', document_views.SPPDEstimateCostCreateAPIView.as_view(), name='sppd-estimate-cost'),
        path('<uuid:id>/generate-document/', document_views.GenerateHTMLDocumentSPPDRetrieveAPIView.as_view(), name='sppd-generate-document'),
        path('upload-spj/', document_views.SPPDUploadSPJCreateAPIView.as_view(), name='sppd-upload-spj'),
        path('dashboard/', document_views.SPPDDashboardAPIView.as_view({'get': 'get'}), name='sppd-dashboard'),

        path('spj/', include([
            path('upload/', document_views.SPPDUploadSPJCreateAPIView.as_view(), name='sppd-upload-spj'),
            path('<uuid:id>/', document_views.SPJRetrieveUpdateDestroyAPIView.as_view(), name='sppd-detail-spj'),
        ])),
    ])),
]
