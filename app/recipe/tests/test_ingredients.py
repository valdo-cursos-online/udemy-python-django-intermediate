"""
Test the ingredients API
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """ Create and return ingredient detail URL """
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(
    email='user@example.com',
    password='test123'
):
    """ Create a return a new user """
    return get_user_model().objects.create_user(email, password)


def create_ingredient(user, name='Cucumber'):
    """ Create and return a new ingredient """
    return Ingredient.objects.create(user=user, name=name)


class PublicIngredientsApiTests(TestCase):
    """ Test the publicly API requests """

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """ Test that login is required to access the endpoint """
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """ Test the private API requests """

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """ Test retrieving a list of ingredients """
        create_ingredient(user=self.user, name='salt')
        create_ingredient(user=self.user, name='pepper')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """ Test list of ingredients is limited to authenticated user """
        user2 = create_user(email='user2@example.com')
        create_ingredient(user=user2, name='sugar')
        ingredient = create_ingredient(user=self.user, name='sugar')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """ Test updating an ingredient with patch """
        ingredient = create_ingredient(user=self.user, name='Carrot')

        payload = {'name': 'Cabbage'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """ Test deleting an ingredient """
        ingredient = create_ingredient(user=self.user, name='Carrot')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())

    def test_filter_ingredients_assigned_to_recipies(self):
        """ Test filtering ingredients by those assigned to recipies """
        ingredient1 = create_ingredient(user=self.user, name='Apple')
        ingredient2 = create_ingredient(user=self.user, name='Banana')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Apple pie',
            time_minutes=30,
            price=Decimal('5.00')
        )
        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_ingredients_assigned_unique(self):
        """ Test filtering ingredients by assigned returns unique items """
        ingredient1 = create_ingredient(user=self.user, name='Apple')
        create_ingredient(user=self.user, name='Banana')
        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Apple pie',
            time_minutes=30,
            price=Decimal('5.00')
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Apple crumble',
            time_minutes=20,
            price=Decimal('3.00')
        )
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
