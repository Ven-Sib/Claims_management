import os
from django.http import HttpResponse, Http404
from django.conf import settings
import mimetypes

class MediaServeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if is a media file request
        if request.path.startswith(settings.MEDIA_URL):
            return self.serve_media(request)
        
        response = self.get_response(request)
        return response

    def serve_media(self, request):
        # Remove the MEDIA_URL prefix to get the file path
        file_path = request.path[len(settings.MEDIA_URL):]
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                with open(full_path, 'rb') as f:
                    content_type, _ = mimetypes.guess_type(full_path)
                    response = HttpResponse(
                        f.read(),
                        content_type=content_type or 'application/octet-stream'
                    )
                    return response
            except Exception:
                pass
        
        raise Http404("Media file not found")