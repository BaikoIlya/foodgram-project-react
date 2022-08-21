from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (AddAndDeleteFavoriteRecipe, AddAndDeleteFollow,
                    AddAndDeleteShoppingCart, IngredientViewSet, RecipeViewSet,
                    TagViewSet, UserViewSet)

app_name = 'api'

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path(
        'users/<int:user_id>/subscribe/',
        AddAndDeleteFollow.as_view(),
        name='follow'
    ),
    path(
        'recipes/<int:recipe_id>/favorite/',
        AddAndDeleteFavoriteRecipe.as_view(),
        name='favorite'
    ),
    path('recipes/<int:recipe_id>/shopping_cart/',
         AddAndDeleteShoppingCart.as_view(),
         name='shopping_cart'
         ),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken'))
]
