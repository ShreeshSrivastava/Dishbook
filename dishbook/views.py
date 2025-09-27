from . import models
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User

# Create your views here.
def index(request):
    featured_recipes = models.Recipe.objects.all().order_by('-id')[:3]
    return render(request, "index.html", {"recipes": featured_recipes})

def recipe(request, recipe_id):
    recipe = get_object_or_404(models.Recipe, id=recipe_id)
    copies_count = recipe.copies.count()
    aggregated_ingredients = recipe.aggregated_ingredients()
    return render(request, "recipe.html", {
        "recipe": recipe, 
        "copies_count": copies_count,
        "aggregated_ingredients": aggregated_ingredients
    })

def search(request):
    all_recipes = models.Recipe.objects.all()
    return render(request, "search.html", {"recipes": all_recipes})

def profile(request, username):
    author = get_object_or_404(User, username=username)
    user_recipes = models.Recipe.objects.filter(author=author)
    return render(request, "profile.html", {"author": author, "recipes": user_recipes})

def signin(request):
    return render(request, "login.html", { })
