from django.contrib.auth import get_user_model
from django.db.models.expressions import Exists, OuterRef, Value
from django.contrib.auth.hashers import make_password
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from rest_framework import permissions, viewsets, status, filters, generics
from rest_framework.decorators import permission_classes, action
from user.models import Follow
from rest_framework.response import Response
from recipe.models import Tag, Ingredient, Recipe, Favorite
from .serializers import TagSerializer, IngredientSerializer, RecipeReadSerializer, UserListSerializer, UserCreateSerializer, UserPasswordSerializer, FollowsSerializer, RecipeInfoSerializer
from rest_framework.views import APIView
from django.db import models
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
        methods=['get',],
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
    def set_password(self,request):
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
            is_subscribed=Value(value=True, output_field=models.BooleanField()), )
        serializer = FollowsSerializer(queryset, many=True, context={'request': request})
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
            is_subscribed=Value(value=True, output_field=models.BooleanField()), )

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
            return Response('Подписаться на самого себя нельзя!', status=status.HTTP_400_BAD_REQUEST)
        if Follow.objects.filter(follower=request.user, following=instance).exists():
            return Response('Вы уже подписаны на этого пользователя!', status=status.HTTP_400_BAD_REQUEST)
        follow = Follow.objects.create(
            follower=request.user,
            following=instance
        )
        serializer = self.get_serializer(follow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.follower.filter(following=instance).delete()


class AddAndDeleteFavoriteRecipe(generics.CreateAPIView, generics.DestroyAPIView):

    serializer_class = RecipeInfoSerializer

    def get_object(self):
        recipe_id = self.kwargs['recipe_id']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        self.check_object_permissions(self.request, recipe)
        return recipe

    def create(self, request, *args, **kwargs):
        recipe_id = self.kwargs['recipe_id']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if Favorite.objects.filter(user=self.request.user, recipe=recipe).exists():
            return Response('Вы уже добавили этот рецепт в избранное!', status=status.HTTP_400_BAD_REQUEST)
        Favorite.objects.create(
            user=request.user,
            recipe=recipe
        )
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.favorite_recipe.filter(recipe=instance).delete()



class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeReadSerializer
    permission_classes = (permissions.AllowAny,)