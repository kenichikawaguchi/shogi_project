from django.contrib import admin
from django.urls import path, include
from matches import views as match_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", match_views.home, name="home"),  # ルートページ
    path('join_match/<int:match_id>/', match_views.join_match, name='join_match'),
    path("accounts/", include("allauth.urls")),  # django-allauth のURL設定
    path("api/get_moves/", match_views.get_moves, name='get_moves'),
    path("api/move_piece/", match_views.move_piece, name='move_piece'),
    path("api/drop_piece/", match_views.drop_piece, name='drop_piece'),
    path("board/", include('matches.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
