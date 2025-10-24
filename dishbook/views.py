from . import models
from django.shortcuts import render, get_object_or_404, redirect
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

def edit_recipe(request, recipe_id):
    recipe = get_object_or_404(models.Recipe, id=recipe_id)
    if request.method == "GET":
        aggregated_ingredients = recipe.aggregated_ingredients()
        return render(request, "edit.html", {
            "recipe": recipe,
            "aggregated_ingredients": aggregated_ingredients
        })
    elif request.method == "POST":
        errors_list = []
        if not request.POST.get("title"):
            errors_list.append("Title is required")
        if not request.POST.get("prep_time_minutes"):
            errors_list.append("Prep time is required")
        if not request.POST.get("cook_time"):
            errors_list.append("Cook time is required")
        if not request.POST.get("total_time"):
            errors_list.append("Total time is required")
        if not request.POST.get("serves"):
            errors_list.append("Serves is required")
           
        
        updated_objects = []        
        # Updating recipe objesct
        recipe.title = request.POST.get("title")
        recipe.prep_time_minutes = int(request.POST.get("prep_time_minutes"))
        recipe.cook_time_minutes = int(request.POST.get("cook_time"))
        recipe.total_time = int(request.POST.get("total_time"))
        recipe.serves = int(request.POST.get("serves"))
        recipe.description = request.POST.get("description")
        updated_objects.append(recipe)
        
        for step in recipe.steps.all():
            step.description = request.POST.get(f'step_{step.id}')
            updated_objects.append(step)

        for step in recipe.steps.all():
            for ingredient in step.ingredients.all():
                # Handle empty values safely
                amount_str = request.POST.get(f'ingredient_amount_{ingredient.id}')
                if amount_str:
                    ingredient.amount = float(amount_str)
                else:
                    ingredient.amount = 0  # Default value
                
                ingredient.unit = request.POST.get(f'ingredient_unit_{ingredient.id}')
                ingredient.name = request.POST.get(f'ingredient_name_{ingredient.id}')
                updated_objects.append(ingredient)

        
      
        for obj in updated_objects: obj.save()
        
        return redirect(f"/recipe/{recipe_id}")



