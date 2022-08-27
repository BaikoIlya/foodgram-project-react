from django.contrib import admin

from .models import Ingredient, Recipe, RecipeIngredient, Tag, Favorite, ShoppingCart

EMPTY_MSG = '-пусто-'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'color', 'slug',)
    search_fields = ('name', 'slug',)
    empty_value_display = EMPTY_MSG


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit',)
    search_fields = ('name', 'measurement_unit',)
    list_filter = ('name', 'measurement_unit',)
    empty_value_display = EMPTY_MSG


class RecipeIngredientAdmin(admin.TabularInline):
    model = RecipeIngredient
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'author', 'name', 'text',
        'cooking_time', 'get_tags', 'get_ingredients',
        'pub_date', 'get_favorite_count')
    search_fields = (
        'name', 'cooking_time',
        'author__email', 'ingredients__name')
    list_filter = ('author', 'name', 'tags',)
    inlines = (RecipeIngredientAdmin,)
    empty_value_display = EMPTY_MSG

    def get_tags(self, obj):
        list_ = [_.name for _ in obj.tags.all()]
        return ', '.join(list_)

    def get_ingredients(self, obj):
        return '\n '.join([
            f'{item["ingredient__name"]} - {item["amount"]}'
            f' {item["ingredient__measurement_unit"]}.'
            for item in obj.recipe.values(
                'ingredient__name',
                'amount', 'ingredient__measurement_unit')])

    def get_favorite_count(self, obj):
        return obj.favorite_recipe.count()


admin.site.register(Favorite)
admin.site.register(ShoppingCart)
