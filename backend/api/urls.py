from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TagViewSet, IngredientViewSet, RecipeViewSet, UserViewSet, AddAndDeleteFollow, AddAndDeleteFavoriteRecipe
app_name = 'api'

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('users/<int:user_id>/subscribe/', AddAndDeleteFollow.as_view(), name='follow'),
    path('recipes/<int:recipe_id>/subscribe', AddAndDeleteFavoriteRecipe.as_view(), name='favorite'),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken'))
]