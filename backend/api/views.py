import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import models
from django.db.models import Count, Sum
from django.db.models.expressions import Exists, OuterRef, Value
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from recipe.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .permission import IsAdminOrReadOnly, IsAuthorPermission
from .serializers import (FollowsSerializer, IngredientSerializer,
                          RecipeAddAndEditSerializer, RecipeInfoSerializer,
                          RecipeReadSerializer, TagSerializer,
                          UserCreateSerializer, UserListSerializer,
                          UserPasswordSerializer)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return UserListSerializer
        return UserCreateSerializer

    def perform_create(self, serializer):
        password = make_password(self.request.data['password'])
        serializer.save(password=password)

    @action(
        detail=False,
        methods=['get', ],
        url_path='me',
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        user = self.request.user
        serializer = UserCreateSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post', ],
        url_path='set_password',
        permission_classes=[permissions.IsAuthenticated],
    )
    def set_password(self, request):
        serializer = UserPasswordSerializer(
            data=request.data,
            context={
                'request': request
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Пароль изменен!'},
            status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['get', ],
        url_path='subscriptions',
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscriptions(self, request):
        queryset = self.request.user.follower.select_related(
            'following'
        ).prefetch_related(
            'following__recipes'
        ).annotate(
            recipes_count=Count('following__recipes'),
            is_subscribed=Value(
                value=True,
                output_field=models.BooleanField()),
        )
        serializer = FollowsSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddAndDeleteFollow(generics.CreateAPIView, generics.DestroyAPIView):
    serializer_class = FollowsSerializer

    def get_queryset(self):
        return self.request.user.follower.select_related(
            'following'
        ).prefetch_related(
            'following__recipes'
        ).annotate(
            recipes_count=Count('following__recipes'),
            is_subscribed=Value(
                value=True,
                output_field=models.BooleanField()),
        )

    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id)
        self.check_object_permissions(self.request, user)
        return user

    def perform_destroy(self, instance):
        self.request.user.follower.filter(following=instance).delete()


class AddAndDeleteFavoriteRecipe(
    generics.CreateAPIView,
    generics.DestroyAPIView
):
    serializer_class = RecipeInfoSerializer

    def get_object(self):
        recipe_id = self.kwargs['recipe_id']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        self.check_object_permissions(self.request, recipe)
        return recipe

    def create(self, request, *args, **kwargs):
        recipe_id = self.kwargs['recipe_id']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user)
        favorite.recipe.add(recipe)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.favorite_recipe.recipe.remove(instance)


class AddAndDeleteShoppingCart(
    generics.CreateAPIView,
    generics.DestroyAPIView
):
    serializer_class = RecipeInfoSerializer

    def get_object(self):
        recipe_id = self.kwargs['recipe_id']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        self.check_object_permissions(self.request, recipe)
        return recipe

    def create(self, request, *args, **kwargs):
        recipe_id = self.kwargs['recipe_id']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        shopping, created = ShoppingCart.objects.get_or_create(
            user=request.user
        )
        shopping.recipe.add(recipe)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.shopping_list.recipe.remove(instance)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeReadSerializer
    permission_classes = (IsAuthorPermission,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Recipe.objects.all().annotate(
                is_favorited=Exists(Favorite.objects.filter(
                    user=self.request.user,
                    recipe=OuterRef('id'))
                ),
                is_in_shopping_cart=Exists(ShoppingCart.objects.filter(
                    user=self.request.user,
                    recipe=OuterRef('id'))
                )
            ).select_related('author')
        else:
            return Recipe.objects.all().annotate(
                is_favorited=Value(
                    value=False,
                    output_field=models.BooleanField()
                ),
                is_in_shopping_cart=Value(
                    value=False,
                    output_field=models.BooleanField()
                )
            ).select_related('author')

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeAddAndEditSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=False,
        methods=['get'],
    )
    def download_shopping_cart(self, request):
        shopping_cart = request.user.shopping_list.recipe.values(
            'ingredients__name',
            'ingredients__measurement_unit'
        ).annotate(amount=Sum('recipe__amount')).order_by('ingredients__name')
        fd, path = tempfile.mkstemp(suffix='.txt', text=True)
        if shopping_cart:
            with open(path, 'w+') as file:
                for index, recipe_ingredient in enumerate(
                        shopping_cart,
                        start=1
                ):
                    file.write(
                        f'{index}.) '
                        f'{recipe_ingredient["ingredients__name"]} '
                        f'{recipe_ingredient["amount"]} '
                        f'{recipe_ingredient["ingredients__measurement_unit"]}'
                        f'\n'
                    )
        return FileResponse(
            fd,
            as_attachment=True,
            filename=path
        )
