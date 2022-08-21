from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import models
from django.db.models import Count
from django.db.models.expressions import Exists, OuterRef, Value
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from recipe.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from user.models import Follow

from .filters import RecipeFilter
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
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserListSerializer

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
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Пароль изменен!'},
                status=status.HTTP_201_CREATED)
        return Response(
            {'error': 'Введите верные данные!'},
            status=status.HTTP_400_BAD_REQUEST)

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

    def create(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id)
        instance = user
        if request.user.id == instance.id:
            return Response(
                'Подписаться на самого себя нельзя!',
                status=status.HTTP_400_BAD_REQUEST
            )
        if Follow.objects.filter(
                follower=request.user,
                following=instance
        ).exists():
            return Response(
                'Вы уже подписаны на этого пользователя!',
                status=status.HTTP_400_BAD_REQUEST
            )
        follow = Follow.objects.create(
            follower=request.user,
            following=instance
        )
        serializer = self.get_serializer(follow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)


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
