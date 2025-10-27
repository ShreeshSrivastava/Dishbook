from . import models
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.db.models import Max


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
        
        # Get form data
        title = request.POST.get("title", "")
        prep_time_str = request.POST.get("prep_time_minutes", "")
        cook_time_str = request.POST.get("cook_time", "")
        total_time_str = request.POST.get("total_time", "")
        serves_str = request.POST.get("serves", "")
        description = request.POST.get("description", "")
        
        # Validate title (required, max 200 chars)
        if not title or title.strip() == "":
            errors_list.append("Title is required")
        elif len(title) > 200:
            errors_list.append("Title must be 200 characters or less")
        
        # Validate prep time (required, non-negative integer)
        if not prep_time_str:
            errors_list.append("Prep time is required")
        else:
            try:
                prep_time = int(prep_time_str)
                if prep_time < 0:
                    errors_list.append("Prep time must be non-negative")
            except ValueError:
                errors_list.append("Prep time must be a valid number")
        
        # Validate cook time (required, non-negative integer)
        if not cook_time_str:
            errors_list.append("Cook time is required")
        else:
            try:
                cook_time = int(cook_time_str)
                if cook_time < 0:
                    errors_list.append("Cook time must be non-negative")
            except ValueError:
                errors_list.append("Cook time must be a valid number")
        
        # Validate total time (required, non-negative integer)
        if not total_time_str:
            errors_list.append("Total time is required")
        else:
            try:
                total_time = int(total_time_str)
                if total_time < 0:
                    errors_list.append("Total time must be non-negative")
            except ValueError:
                errors_list.append("Total time must be a valid number")
        
        # Validate serves (required, positive integer)
        if not serves_str:
            errors_list.append("Serves is required")
        else:
            try:
                serves = int(serves_str)
                if serves <= 0:
                    errors_list.append("Serves must be a positive number")
            except ValueError:
                errors_list.append("Serves must be a valid number")
        
        # Validate description (required)
        if not description or description.strip() == "":
            errors_list.append("Description is required")
        
        # Update steps with form data BEFORE validation
        for step in recipe.steps.all():
            step.description = request.POST.get(f'step_{step.id}', "")
        
        # Validate steps
        for step in recipe.steps.all():
            if not step.description or step.description.strip() == "":
                errors_list.append(f"Step {step.order} description is required")
        
        # Validate ingredients
        for step in recipe.steps.all():
            for ingredient in step.ingredients.all():
                amount_str = request.POST.get(f'ingredient_amount_{ingredient.id}', "")
                unit = request.POST.get(f'ingredient_unit_{ingredient.id}', "")
                name = request.POST.get(f'ingredient_name_{ingredient.id}', "")
                
                # Validate amount (required, positive number, can be fractional)
                if not amount_str:
                    errors_list.append(f"Ingredient amount for '{name}' is required")
                else:
                    try:
                        amount = float(amount_str)
                        if amount <= 0:
                            errors_list.append(f"Ingredient amount for '{name}' must be positive")
                    except ValueError:
                        errors_list.append(f"Ingredient amount for '{name}' must be a valid number")
                
                # Validate unit (max 50 chars)
                if len(unit) > 50:
                    errors_list.append(f"Ingredient unit for '{name}' must be 50 characters or less")
                
                # Validate name (required, max 100 chars)
                if not name or name.strip() == "":
                    errors_list.append("Ingredient name is required")
                elif len(name) > 100:
                    errors_list.append(f"Ingredient name must be 100 characters or less")
        
        # Handle extra step and ingredients
        extra_step_description = request.POST.get('extra_step_description', "").strip()
        extra_step_created = False
        new_objects = []  # Store new objects to save if validation passes
        
        # Check if extra step has content
        if extra_step_description:
            # Create new step object (don't save yet) - Fixed Max import
            max_order = recipe.steps.all().aggregate(Max('order'))['order__max'] or 0
            new_step = models.Step(
                recipe=recipe,
                order=max_order + 1,
                description=extra_step_description
            )
            new_objects.append(new_step)
            extra_step_created = True
        
        # Handle extra ingredients for existing steps
        for step in recipe.steps.all():
            amount_str = request.POST.get(f'extra_ingredient_amount_{step.id}', "")
            unit = request.POST.get(f'extra_ingredient_unit_{step.id}', "").strip()
            name = request.POST.get(f'extra_ingredient_name_{step.id}', "").strip()
            
            # Check if any field is non-empty
            if amount_str or unit or name:
                # Validate amount (required if any field is filled)
                if not amount_str:
                    errors_list.append(f"Extra ingredient amount for step {step.order} is required")
                else:
                    try:
                        amount = float(amount_str)
                        if amount <= 0:
                            errors_list.append(f"Extra ingredient amount for step {step.order} must be positive")
                    except ValueError:
                        errors_list.append(f"Extra ingredient amount for step {step.order} must be a valid number")
                
                # Validate unit (max 50 chars)
                if len(unit) > 50:
                    errors_list.append(f"Extra ingredient unit for step {step.order} must be 50 characters or less")
                
                # Validate name (required if any field is filled)
                if not name:
                    errors_list.append(f"Extra ingredient name for step {step.order} is required")
                elif len(name) > 100:
                    errors_list.append(f"Extra ingredient name for step {step.order} must be 100 characters or less")
                
                # If validation passes, create ingredient object
                if amount_str and name:
                    try:
                        amount = float(amount_str)
                        if amount > 0:
                            new_ingredient = models.Ingredient(
                                step=step,
                                amount=str(amount),
                                unit=unit,
                                name=name
                            )
                            new_objects.append(new_ingredient)
                    except ValueError:
                        pass  # Error already added above
        
        # Handle extra ingredient for extra step
        if extra_step_created:
            amount_str = request.POST.get('extra_step_ingredient_amount', "")
            unit = request.POST.get('extra_step_ingredient_unit', "").strip()
            name = request.POST.get('extra_step_ingredient_name', "").strip()
            
            # Check if any field is non-empty
            if amount_str or unit or name:
                # Validate amount (required if any field is filled)
                if not amount_str:
                    errors_list.append("Extra ingredient amount for extra step is required")
                else:
                    try:
                        amount = float(amount_str)
                        if amount <= 0:
                            errors_list.append("Extra ingredient amount for extra step must be positive")
                    except ValueError:
                        errors_list.append("Extra ingredient amount for extra step must be a valid number")
                
                # Validate unit (max 50 chars)
                if len(unit) > 50:
                    errors_list.append("Extra ingredient unit for extra step must be 50 characters or less")
                
                # Validate name (required if any field is filled)
                if not name:
                    errors_list.append("Extra ingredient name for extra step is required")
                elif len(name) > 100:
                    errors_list.append("Extra ingredient name for extra step must be 100 characters or less")
                
                # If validation passes, create ingredient object
                if amount_str and name:
                    try:
                        amount = float(amount_str)
                        if amount > 0:
                            new_ingredient = models.Ingredient(
                                step=new_step,
                                amount=str(amount),
                                unit=unit,
                                name=name
                            )
                            new_objects.append(new_ingredient)
                    except ValueError:
                        pass  # Error already added above
        
        # Update recipe object with form data (even if invalid)
        recipe.title = title
        recipe.description = description
        
        # Only update numeric fields if they're valid numbers
        try:
            recipe.prep_time_minutes = int(prep_time_str) if prep_time_str else 0
        except ValueError:
            recipe.prep_time_minutes = 0
            
        try:
            recipe.cook_time_minutes = int(cook_time_str) if cook_time_str else 0
        except ValueError:
            recipe.cook_time_minutes = 0
            
        try:
            recipe.total_time = int(total_time_str) if total_time_str else 0
        except ValueError:
            recipe.total_time = 0
            
        try:
            recipe.serves = int(serves_str) if serves_str else 1
        except ValueError:
            recipe.serves = 1
        
        # Update ingredients with form data
        for step in recipe.steps.all():
            for ingredient in step.ingredients.all():
                amount_str = request.POST.get(f'ingredient_amount_{ingredient.id}', "")
                try:
                    ingredient.amount = float(amount_str) if amount_str else 0
                except ValueError:
                    ingredient.amount = 0
                ingredient.unit = request.POST.get(f'ingredient_unit_{ingredient.id}', "")
                ingredient.name = request.POST.get(f'ingredient_name_{ingredient.id}', "")
        
        # If there are errors, re-render the page with errors
        if errors_list:
            aggregated_ingredients = recipe.aggregated_ingredients()
            return render(request, "edit.html", {
                "recipe": recipe,
                "aggregated_ingredients": aggregated_ingredients,
                "errors_list": errors_list
            })
        else:
            # No errors, save and redirect
            recipe.save()
            
            # Save steps and their ingredients
            steps = list(recipe.steps.all())
            for step in steps:
                step.save()
                for ingredient in step.ingredients.all():
                    ingredient.save()
            
            # Save new objects (extra step and ingredients)
            for obj in new_objects:
                obj.save()
            
            return redirect(f"/recipe/{recipe_id}")


