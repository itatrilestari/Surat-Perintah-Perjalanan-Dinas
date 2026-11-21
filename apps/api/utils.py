from rest_framework.pagination import PageNumberPagination
from api.models import Log

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"
    max_page_size = 100

def create_log(user, action, feature_name, message):
    log = Log.objects.create(user=user, action=action, feature_name=feature_name, message=message)
    return log