from django.contrib import admin
from django.urls import path, include
from accounts.views import home  # 追加
from matches import views as match_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),  # ルートページ
    path("accounts/", include("allauth.urls")),  # django-allauth のURL設定
    path("api/get_moves/", match_views.get_moves, name='get_moves'),
    path("api/move_piece/", match_views.move_piece, name='move_piece'),
    path("board/", include('matches.urls')),
]

