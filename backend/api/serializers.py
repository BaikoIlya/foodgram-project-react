import django.contrib.auth.password_validation as validators
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from drf_base64.fields import Base64ImageField
from recipe.models import Ingredient, Recipe, RecipeIngredient, Tag
from rest_framework import serializers
from user.models import Subscribe

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return user.follower.filter(following=obj).exists()


class UserCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
        )

    def validate_password(self, password):
        validators.validate_password(password)
        return password


class UserPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    current_password = serializers.CharField()

    def validate_current_password(self, current_password):
        user = self.context['request'].user
        if not authenticate(
            username=user.email,
            password=current_password
        ):
            raise serializers.ValidationError(detail='Пароль не подходит.')
        return current_password

    def validate_new_password(self, new_password):
        validators.validate_password(new_password)
        return new_password

    def create(self, validated_data):
        user = self.context['request'].user
        password = make_password(
            validated_data.get('new_password')
        )
        user.password = password
        user.save()
        return validated_data


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'color',
            'slug',
        )


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientsEditSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'amount',
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient.id'
    )
    name = serializers.StringRelatedField(
        source='ingredient.name'
    )
    measurement_unit = serializers.StringRelatedField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount',
        )


class RecipeInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagSerializer(
        many=True,
        read_only=True,
    )
    author = UserListSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField(read_only=True,)
    image = Base64ImageField()
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def get_ingredients(self, obj):
        all_ingredients = RecipeIngredient.objects.filter(recipe=obj)
        return RecipeIngredientSerializer(all_ingredients, many=True).data


class RecipeAddAndEditSerializer(serializers.ModelSerializer):
    image = Base64ImageField(use_url=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = IngredientsEditSerializer(many=True)
    author = serializers.ReadOnlyField()

    class Meta:
        model = Recipe
        fields = '__all__'

    def validate_cooking_time(self, cooking_time):
        if int(cooking_time) < 1:
            raise serializers.ValidationError(
                'Время приготовления минимум 1 минута!'
            )
        return cooking_time

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError('Добавьте тэг для рецепта')
        return tags

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Блюд без ингредиентов не бывает. Добавьте хотя бы 1!'
            )
        ingredients_add = []
        for elem in ingredients:
            ingredient = get_object_or_404(Ingredient, id=elem['id'])
            if ingredient in ingredients_add:
                raise serializers.ValidationError(
                    'У вас два одинаковых ингредиента.'
                )
            ingredients_add.append(ingredient)
        return ingredients

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        objs = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount')
            )
            for ingredient in ingredients
        ]
        RecipeIngredient.objects.bulk_create(objs)

        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            objs = [
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=ingredient.get('id'),
                    amount=ingredient.get('amount')
                )
                for ingredient in ingredients
            ]
            RecipeIngredient.objects.bulk_create(objs)
        if 'tags' in validated_data:
            tags = validated_data.pop('tags')
            instance.tags.set(tags)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context={
                'request': self.context.get('request')
            }).data


class FollowsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(
        source='following.id',
        read_only=True
    )
    email = serializers.EmailField(
        source='following.email',
        read_only=True
    )
    username = serializers.CharField(
        source='following.username',
        read_only=True
    )
    first_name = serializers.CharField(
        source='following.first_name',
        read_only=True
    )
    last_name = serializers.CharField(
        source='following.last_name',
        read_only=True
    )
    recipes = serializers.SerializerMethodField()
    is_subscribed = serializers.BooleanField(read_only=True)
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscribe
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):

        requests = self.context.get('request')
        limit = requests.GET.get('recipes_limit')
        if limit:
            recipes = obj.following.recipes.all()[:int(limit)]
        else:
            recipes = obj.following.recipes.all()
        return RecipeInfoSerializer(recipes, many=True).data

    def validate(self, data):
        request = self.context['request']
        follower = request.user
        user_id = self.context['view'].kwargs.get('user_id')
        following = get_object_or_404(User, pk=user_id)
        if follower == following:
            raise serializers.ValidationError(
                'Подписаться на самого себя нельзя!'
            )
        if Subscribe.objects.filter(
                follower=follower,
                following=following
        ).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя!'
            )
        return data

    def create(self, validated_data):
        request = self.context['request']
        user_id = self.context['view'].kwargs.get('user_id')
        following = get_object_or_404(User, pk=user_id)
        follow = Subscribe.objects.create(
            follower=request.user,
            following=following
        )
        return follow
