from django.contrib import admin
from .models import GameState, Match, Move


admin.site.register(GameState)
admin.site.register(Match)
admin.site.register(Move)

