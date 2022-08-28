from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='tag name',
        unique=True,
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text='Tag Slug',
    )
    color = models.CharField(
        max_length=7,
        unique=True
    )

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='ingredient name',

    )
    measurement_unit = models.CharField(
        max_length=200
    )

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='name of recipe',
    )
    image = models.ImageField(
        'Изображение рецепта',
        upload_to='static/recipe/',
    )
    text = models.TextField()
    cooking_time = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), ]
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='author',
        related_name='recipe',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
    )
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True
    )

    class Meta:
        ordering = ('-pub_date', )


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe')
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient',
    )
    amount = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), ]
    )


class Favorite(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_recipe',
        verbose_name='Пользователь'
    )
    recipe = models.ManyToManyField(
        Recipe,
        related_name='favorite_recipe',
        verbose_name='Рецепт в избранном'
    )


class ShoppingCart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_list',
        verbose_name='Пользователь'
    )
    recipe = models.ManyToManyField(
        Recipe,
        related_name='shopping_list',
        verbose_name='В покупки'
    )
