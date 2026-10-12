from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError


def custom_exception_handler(exc, context):
    # Let DRF build its normal response first
    response = exception_handler(exc, context)

    # If DRF didn't handle it (a real server crash), leave it alone
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        # Field errors, e.g. {"price": ["This field is required."]}
        response.data = {
            'detail': 'Validation failed.',
            'errors': response.data,
        }
    elif isinstance(response.data, dict) and 'detail' in response.data:
        # 401, 403, 404, 429: already have a message, just keep it
        response.data = {'detail': str(response.data['detail'])}
    else:
        response.data = {'detail': str(response.data)}

    return response