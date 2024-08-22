"""
Views for the recipe API
"""

from rest_framework import viewsets, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Recipe, Tag
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
    TagSerializer
)


class RecipeViewSet(viewsets.ModelViewSet):
    """ Manage recipes in the database """
    serializer_class = RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """ Return objects for the current authenticated user only """
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        """ Return the serializer class for request """
        if self.action == 'list':
            return RecipeSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        """ Create a new recipe """
        serializer.save(user=self.request.user)


class TagViewSet(mixins.DestroyModelMixin,
                 mixins.UpdateModelMixin,
                 mixins.ListModelMixin,
                 viewsets.GenericViewSet):
    """ Manage tags in the database """
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """ Return objects for the current authenticated user only """
        return self.queryset.filter(user=self.request.user).order_by('-name')

    # def perform_create(self, serializer):
    #     """ Create a new tag """
    #     serializer.save(user=self.request.user)
