"""
Tests for the recipe API
"""

from decimal import Decimal
import tempfile
import os
from PIL import Image

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer
)


RECIPIES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """ Create and return recipe detail URL """
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """ Create and return an image upload URL """
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_user(**params):
    """ Helper function to create and return user """
    return get_user_model().objects.create_user(**params)


def create_recipe(user, **params):
    """ Create and return a sample recipe """
    defaults = {
        'title': 'Sample Recipe',
        'time_minutes': 22,
        'price': Decimal('5.00'),
        'description': 'Sample recipe description',
        'link': 'https://example.com/recipe.pdf'
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """ Test unauthenticated recipe API access """

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """ Test that authentication is required """
        res = self.client.get(RECIPIES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """ Test authenticated recipe API access """

    def setUp(self):
        self.user = create_user(
            email='user@example.com',
            password='test123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_recipes(self):
        """ Test retrieving a list of recipes """
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPIES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """ Test retrieving recipes for user """
        other_user = create_user(
            email='other@example.com',
            password='test123'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPIES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_one_detail(self):
        """ Test get recipe detail  """
        recipe = create_recipe(user=self.user)
        # recipe.tags.add(create_tag(user=self.user))
        # recipe.ingredients.add(create_ingredient(user=self.user))

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.data, serializer.data)

    def test_create(self):
        """ Test create recipe  """
        payload = {
            'title': 'Chocolate Cake',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }
        res = self.client.post(RECIPIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """ Test partial update of a recipe  """
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            link=original_link,
            title='Original Title'
        )

        payload = {'title': 'New Title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """ Test full update of a recipe  """
        recipe = create_recipe(
            user=self.user,
            title='New Title',
            time_minutes=25,
            price=Decimal('5.99'),
        )

        payload = {
            'title': 'Updated Title',
            'link': 'https://example.com/updated.pdf',
            'description': 'Updated description',
            'time_minutes': 10,
            'price': Decimal('8.35'),
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """ Test that user cannot be updated  """
        new_user = create_user(
            email='user2@example.com',
            password='test123'
        )
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete(self):
        """ Test delete recipe successful  """
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """ Test that user cannot delete other user's recipe  """
        new_user = create_user(
            email='user2@example.com',
            password='test123'
        )
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_tags(self):
        """ Test creating a recipe with tags  """
        payload = {
            'title': 'Chocolate Cake',
            'time_minutes': 30,
            'price': Decimal('5.99'),
            'tags': [{'name': 'Sweet'}, {'name': 'Dessert'}]
        }
        res = self.client.post(RECIPIES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """ Test creating a recipe with existing tags  """
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Indian Curry',
            'time_minutes': 30,
            'price': Decimal('5.99'),
            'tags': [{'name': 'Indian'}, {'name': 'Spicy'}]
        }
        res = self.client.post(RECIPIES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """ Test creating a tag on update  """
        tag_name_vegan = 'Vegan'
        recipe = create_recipe(user=self.user)
        payload = {
            'tags': [{'name': tag_name_vegan}]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name=tag_name_vegan)
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """ Test assigning an existing tag when updating a recipe """
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {
            'tags': [{'name': 'Lunch'}]
        }
        ulr = detail_url(recipe.id)
        res = self.client.patch(ulr, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """ Test clearing all tags from a recipe """
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {
            'tags': []
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_ingredients(self):
        """ Test creating a recipe with ingredients  """
        payload = {
            'title': 'Chocolate Cake',
            'time_minutes': 30,
            'price': Decimal('5.99'),
            'ingredients': [{'name': 'Flour'}, {'name': 'Sugar'}]
        }
        res = self.client.post(RECIPIES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipi_with_existing_ingredients(self):
        """ Test creating a recipe with existing ingredients  """
        ingredient_salt = Ingredient.objects.create(
            user=self.user, name='Salt')
        payload = {
            'title': 'Salted Caramel',
            'time_minutes': 30,
            'price': Decimal('5.99'),
            'ingredients': [{'name': 'Salt'}, {'name': 'Sugar'}]
        }
        res = self.client.post(RECIPIES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_salt, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """ Test creating an ingredient on update  """
        ingredient_name = 'Salt'
        recipe = create_recipe(user=self.user)
        payload = {
            'ingredients': [{'name': ingredient_name}]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(
            user=self.user, name=ingredient_name)
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """ Test assigning an existing ingredient when updating a recipe """
        ingredient_1 = Ingredient.objects.create(
            user=self.user, name='Flour')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_1)

        ingredient_2 = Ingredient.objects.create(
            user=self.user, name='Sugar')
        payload = {
            'ingredients': [{'name': 'Sugar'}]
        }
        ulr = detail_url(recipe.id)
        res = self.client.patch(ulr, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_2, recipe.ingredients.all())
        self.assertNotIn(ingredient_1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """ Test clearing all ingredients from a recipe """
        ingredient = Ingredient.objects.create(user=self.user, name='Flour')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {
            'ingredients': []
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_recipes_by_tags(self):
        """ Test returning recipes with specific tags """
        recipe1 = create_recipe(user=self.user, title='Recipe 1')
        recipe2 = create_recipe(user=self.user, title='Recipe 2')
        recipe3 = create_recipe(user=self.user, title='Recipe 3')
        tag1 = Tag.objects.create(user=self.user, name='Tag 1')
        tag2 = Tag.objects.create(user=self.user, name='Tag 2')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)

        res = self.client.get(
            RECIPIES_URL,
            {'tags': f'{tag1.id},{tag2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipies_by_ingridients(self):
        """ Test returning recipes with specific ingredients """
        recipe1 = create_recipe(user=self.user, title='Recipe 1')
        recipe2 = create_recipe(user=self.user, title='Recipe 2')
        recipe3 = create_recipe(user=self.user, title='Recipe 3')
        ingredient1 = Ingredient.objects.create(
            user=self.user, name='Ingredient 1')
        ingredient2 = Ingredient.objects.create(
            user=self.user, name='Ingredient 2')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)

        res = self.client.get(
            RECIPIES_URL,
            {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)


class ImageUploadTests(TestCase):
    """ Test fot the image upload API """

    def setUp(self):
        self.user = create_user(
            email='user@example.com',
            password='test123'
        )
        self.recipi = create_recipe(user=self.user)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.recipi.image.delete()

    def test_upload_image_to_recipe(self):
        """ Test uploading an image to recipe """
        url = image_upload_url(self.recipi.id)

        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            image = Image.new('RGB', (10, 10))
            image.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')
        self.recipi.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipi.image.path))

    def test_upload_image_bad_request(self):
        """ Test uploading an invalid image """
        url = image_upload_url(self.recipi.id)
        res = self.client.post(url, {'image': 'notimage'}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
