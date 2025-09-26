from . import models
from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, "index.html", { })

def recipe(request, recipe_id):
    return render(request, "recipe.html", { })

def search(request):
    return render(request, "search.html", { })

def profile(request, username):
    return render(request, "profile.html", { })

def signin(request):
    return render(request, "login.html", { })
