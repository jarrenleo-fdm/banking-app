"""Django context processors for banking app."""
from .models import PendingTransaction


def authoriser_pending_count(request):
    if not request.user.is_authenticated:
        return {"authoriser_pending_count": 0}
    if not hasattr(request.user, "authoriser_profile"):
        return {"authoriser_pending_count": 0}
    count = PendingTransaction.objects.filter(
        business_account=request.user.authoriser_profile.business_account,
        status=PendingTransaction.PENDING,
    ).count()
    return {"authoriser_pending_count": count}
