from django.urls import path
from . import views

urlpatterns = [
    path('<int:match_id>/', views.board_view, name='board_view'),
    path('get_moves/', views.get_moves, name='get_moves'),
    path('new/', views.new_match, name='new_match'),
    path('move_piece/', views.move_piece, name='move_piece'),
    path('drop_piece/', views.drop_piece, name='drop_piece'),
    path('resign/', views.resign_match, name='resign_match'),
    # 例: 対局画面を表示するビューを追加する場合
]

