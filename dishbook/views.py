from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.db.models import Max, Q
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from . import models

MAX_UPLOAD_SIZE = 64 * 1024 * 1024  # 64 MiB
PNG_MAGIC = b"\x89PNG"


# Create your views here.
def _visible_recipe_filter(request):
    visible_filter = Q(is_public=True)
    if request.user.is_authenticated:
        visible_filter |= Q(author=request.user)
    return visible_filter


def index(request):
    visible_filter = _visible_recipe_filter(request)
    featured_recipes = (
        models.Recipe.objects.filter(visible_filter)
        .order_by('-id')
        .distinct()[:3]
    )
    return render(request, "index.html", {"recipes": featured_recipes})


def recipe(request, recipe_id):
    recipe = get_object_or_404(models.Recipe, id=recipe_id)
    if not recipe.is_public and (not request.user.is_authenticated or recipe.author != request.user):
        raise PermissionDenied
    copies_count = recipe.copies.count()
    aggregated_ingredients = recipe.aggregated_ingredients()
    return render(request, "recipe.html", {
        "recipe": recipe,
        "copies_count": copies_count,
        "aggregated_ingredients": aggregated_ingredients
    })


def _perform_search(visible_filter, query):
    """Helper function to perform search filtering. Returns queryset."""
    recipes = models.Recipe.objects.filter(visible_filter)
    
    if query:
        keywords = query.split()
        for keyword in keywords:
            if keyword.startswith("tag:"):
                tag_name = keyword.removeprefix("tag:")
                recipes = recipes.filter(tags__name=tag_name)
            elif keyword.startswith("variation:"):
                recipe_id_str = keyword.removeprefix("variation:")
                try:
                    recipe_id = int(recipe_id_str)
                    recipes = recipes.filter(copied_from_id=recipe_id)
                except ValueError:
                    pass  # Invalid ID, skip this keyword
            else:
                # Regular keyword - search in title
                recipes = recipes.filter(title__icontains=keyword)
    
    return recipes.distinct()


def search(request):
    query = request.GET.get("q", "").strip()
    visible_filter = _visible_recipe_filter(request)
    all_recipes = _perform_search(visible_filter, query)
    return render(request, "search.html", {"recipes": all_recipes, "query": query})


def search_api(request):
    query = request.GET.get("q", "").strip()
    visible_filter = _visible_recipe_filter(request)
    recipes = _perform_search(visible_filter, query)
    
    results = []
    for recipe in recipes:
        result = {
            "id": recipe.id,
            "title": recipe.title,
            "tags": [tag.name for tag in recipe.sorted_tags()]
        }
        if recipe.photo:
            result["photo"] = f"/recipe/{recipe.id}/photo"
        results.append(result)
    
    return JsonResponse({"results": results, "query": query})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    if request.user.is_authenticated and request.user == author:
        user_recipes = models.Recipe.objects.filter(author=author)
    else:
        user_recipes = models.Recipe.objects.filter(author=author, is_public=True)
    return render(request, "profile.html", {"author": author, "recipes": user_recipes})

def signin(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        next_url = request.POST.get("next", "/")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect("/")
        else:
            return render(request, "login.html", {
                "error": "Invalid username or password.",
                "next": next_url,
            })
    else:
        next_param = request.GET.get("next", "/")
        return render(request, "login.html", {"next": next_param})


def signout(request):
    logout(request)
    return redirect("/login/")

@login_required
def edit_recipe(request, recipe_id):
    recipe = get_object_or_404(models.Recipe, id=recipe_id)
    if recipe.author != request.user:
        raise PermissionDenied
    if request.method == "GET":
        aggregated_ingredients = recipe.aggregated_ingredients()
        copies_count = recipe.copies.count()
        return render(request, "edit.html", {
            "recipe": recipe,
            "aggregated_ingredients": aggregated_ingredients,
            "copies_count": copies_count
        })
    elif request.method == "POST":
        errors_list = []
        photo_file = request.FILES.get("recipe_photo")
        
        # Get form data
        title = request.POST.get("title", "")
        prep_time_str = request.POST.get("prep_time_minutes", "")
        cook_time_str = request.POST.get("cook_time_minutes", "")
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
        steps_list = list(recipe.steps.all())
        for step in steps_list:
            step.description = request.POST.get(f'step_{step.id}', "")
        
        # Validate steps
        for step in steps_list:
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
        
        # Update recipe object with form data even if invalid
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
        
        if photo_file:
            is_png, error_message = _is_small_png(photo_file, label="Recipe photo")
            if not is_png:
                errors_list.append(error_message or "Recipe photo must be a valid PNG image.")

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
            old_photo_name = recipe.photo.name
            if photo_file:
                if hasattr(photo_file, "seek"):
                    photo_file.seek(0)
                recipe.photo.save("upload.png", photo_file, save=False)
            recipe.save()
            if recipe.photo.name != old_photo_name:
                models.delete_photo_if_unused(old_photo_name)
            
            # Save steps and their ingredients
            for step in steps_list:
                step.save()
                for ingredient in step.ingredients.all():
                    ingredient.save()
            
        
            for obj in new_objects:
                obj.save()
            
            return redirect(f"/recipe/{recipe_id}")


@login_required
def make_public(request, recipe_id):
    recipe = get_object_or_404(models.Recipe, id=recipe_id)
    if request.method != "POST":
        raise PermissionDenied
    if recipe.author != request.user:
        raise PermissionDenied
    recipe.is_public = True
    recipe.save(update_fields=["is_public"])
    return redirect("recipe", recipe_id=recipe.id)

def _read_first_chunk(file_obj):
    try:
        if hasattr(file_obj, "chunks"):
            iterator = file_obj.chunks()
            chunk = next(iterator)
        elif hasattr(file_obj, "read"):
            position = None
            if hasattr(file_obj, "tell"):
                try:
                    position = file_obj.tell()
                except (OSError, ValueError):
                    position = None
            chunk = file_obj.read(len(PNG_MAGIC))
            if position is not None and hasattr(file_obj, "seek"):
                file_obj.seek(position)
        else:
            chunk = None
    except StopIteration:
        chunk = None
    except Exception:
        chunk = None
    finally:
        if hasattr(file_obj, "seek"):
            try:
                file_obj.seek(0)
            except Exception:
                pass
    return chunk


def _is_small_png(file_obj, label="Photo"):
    size = getattr(file_obj, "size", None)
    if size is None:
        file_attr = getattr(file_obj, "file", None)
        size = getattr(file_attr, "size", None)
    if size is not None and size > MAX_UPLOAD_SIZE:
        return False, f"{label} must be 64 MiB or smaller."

    name = getattr(file_obj, "name", "")
    if name and not name.lower().endswith(".png"):
        return False, f"{label} must be a PNG image."

    first_chunk = _read_first_chunk(file_obj)
    if not first_chunk:
        return False, f"Could not read {label.lower()}."

    if len(first_chunk) < len(PNG_MAGIC) or first_chunk[:len(PNG_MAGIC)] != PNG_MAGIC:
        return False, f"{label} is not a valid PNG file."

    return True, None

def recipe_image(request, recipe_id):
    recipe = get_object_or_404(models.Recipe, id=recipe_id)

    if not recipe.is_public and (not request.user.is_authenticated or recipe.author != request.user):
        raise PermissionDenied

    if not recipe.photo:
        raise Http404("Photo not found")

    is_valid, _ = _is_small_png(recipe.photo, label="Recipe photo")
    if not is_valid:
        raise Http404("Photo not found")

    return FileResponse(recipe.photo.open("rb"), content_type="image/png")


def profile_image(request, username):
    user = get_object_or_404(User, username=username)
    profile = getattr(user, "profile", None)
    if profile is None or not profile.photo:
        raise Http404("Profile photo not found")
    is_valid, _ = _is_small_png(profile.photo, label="Profile photo")
    if not is_valid:
        raise Http404("Photo not found")
    return FileResponse(profile.photo.open("rb"), content_type="image/png")
