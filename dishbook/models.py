from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Recipe(models.Model):
    title = models.CharField(max_length=200)
    photo = models.ImageField(upload_to="media/", null=True, blank=True)
    description = models.TextField()
    prep_time_minutes = models.IntegerField()
    cook_time_minutes = models.IntegerField()
    serves = models.IntegerField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    copied_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="copies")
    featured_on = models.DateField(null=True, blank=True)
    tags = models.ManyToManyField('Tag', blank=True)
    
    def total_time(self):
        return self.prep_time_minutes + self.cook_time_minutes
    
    def sorted_tags(self):
        return self.tags.all().order_by('name')
    
    def aggregated_ingredients(self):
        ingredients_dict = {}
        
        for step in self.steps.all().order_by('order'):
            for ingredient in step.ingredients.all():
                name = ingredient.name
                amount = float(ingredient.amount)
                unit = ingredient.unit
                
                
                if unit == "ct":
                    unit = ""
                
                
                if name not in ingredients_dict:
                    ingredients_dict[name] = {}
                
                
                if unit in ingredients_dict[name]:
                    ingredients_dict[name][unit] += amount
                else:
                    ingredients_dict[name][unit] = amount
        
        
        result = []
        for name, units in ingredients_dict.items():

            unit_amounts = []
            for unit, amount in units.items():
                if unit:
                    unit_amounts.append(f"{amount:.2g} {unit}")
                else:
                    unit_amounts.append(f"{amount:.2g}")
            
            # Join with " and "
            amount_str = " and ".join(unit_amounts)
            result.append({
                'name': name,
                'amount': amount_str
            })
        
        return result

class Step(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')
    order = models.IntegerField()
    description = models.TextField()

    def calculate_rows(self):
        """Calculate the number of rows needed for textarea based on description length"""
        if not self.description:
            return 1
        length = len(self.description)
        rows = (length + 49) // 50 + 1
        return max(1, rows)
        
class Ingredient(models.Model):
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='ingredients')
    amount = models.CharField(max_length=50)
    unit = models.CharField(max_length=50)
    name = models.CharField(max_length=100)

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to="media/", null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
