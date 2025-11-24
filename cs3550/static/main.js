console.log("Hello", document.title);

const showPasswordCheckbox = document.getElementById("show-password");

if (showPasswordCheckbox) {
  const passwordInput = document.getElementById("password");

  if (passwordInput) {
    const togglePasswordVisibility = () => {
      const newType = showPasswordCheckbox.checked ? "text" : "password";

      if (passwordInput.type !== newType) {
        try {
          passwordInput.type = newType;
        } catch (err) {
          passwordInput.setAttribute("type", newType);
        }
      }
    };

    showPasswordCheckbox.addEventListener("input", togglePasswordVisibility);
    togglePasswordVisibility();
  } else {
    console.warn("Password input not found on login page.");
  }
}

const prepTimeInput = document.getElementById("prep_time_minutes");
const cookTimeInput = document.getElementById("cook_time_minutes");
const totalTimeInput = document.getElementById("total_time");

if (prepTimeInput && cookTimeInput && totalTimeInput) {
    const updateTotalTime = () => {
        const prepTime = +prepTimeInput.value || 0;
        const cookTime = +cookTimeInput.value || 0;
        const totalTime = prepTime + cookTime;
        totalTimeInput.value = totalTime;
        
    };

    prepTimeInput.addEventListener("input", updateTotalTime);
    cookTimeInput.addEventListener("input", updateTotalTime);

}

const ingredientsList = document.querySelector('aside.recipe__ingredients ul[itemprop="recipeIngredient"]');

if(ingredientsList) {
  const updateIngredientsList = () => {

    // Find all step <li> elements in order
    const stepElements = document.querySelectorAll('section.recipe__steps ol[itemprop="recipeInstructions"] > li');
    const ingredientsDict = {};
    const stepOrder = [];

    // Process each step in order
    stepElements.forEach((stepEl, stepIndex) => {
      //find all ingredient amount inputs in this step
      const amountInputs = stepEl.querySelectorAll('input[id^="ingredient_amount_"], input[id^="extra_ingredient_amount_"], input[id="extra_step_ingredient_amount"]');

      amountInputs.forEach(amountInput => {
        //find the corresponding unit and name inputs

        const id = amountInput.id;
        let unitInput, nameInput;

        if(id.startsWith('ingredient_amount_')) {
          const ingredientId = id.replace('ingredient_amount_', '');
          unitInput = document.getElementById(`ingredient_unit_${ingredientId}`);
          nameInput = document.getElementById(`ingredient_name_${ingredientId}`);

        } else if (id.startsWith('extra_ingredient_amount_')){
          const stepId = id.replace('extra_ingredient_amount_', '');
          unitInput = document.getElementById(`extra_ingredient_unit_${stepId}`);
          nameInput = document.getElementById(`extra_ingredient_name_${stepId}`);
 
        } else if (id === 'extra_step_ingredient_amount') {
          unitInput = document.getElementById('extra_step_ingredient_unit');
          nameInput = document.getElementById('extra_step_ingredient_name');
        }

        if (!unitInput || !nameInput) return;

        // Get values and validate
        const amountStr = amountInput.value.trim();
        const unit = unitInput.value.trim();
        const name = nameInput.value.trim();

        // skip empty ingredients
        if (!amountStr || !name) return;

        const amount = +amountStr || 0;
        if (amount <= 0) return;

        // normalize unit ("ct" becomes "")
        const normalizedUnit = unit === "ct" ? "" : unit;

        // track ingredient and aggregate
        if (!ingredientsDict[name]) {
          ingredientsDict[name] = { units: {}, firstStep: stepIndex };
          stepOrder.push(name);
        }

        // aggregate amounts by unit
       if (normalizedUnit in ingredientsDict[name].units) {
        ingredientsDict[name].units[normalizedUnit] += amount;
       } else {
        ingredientsDict[name].units[normalizedUnit] = amount;
       }
        

      });
    });

    // sort by first appearance
    stepOrder.sort((a, b) => {
      return ingredientsDict[a].firstStep - ingredientsDict[b].firstStep;
    });

    // build new list items
    const newListItems = stepOrder.map(name=> {
      const ingredient = ingredientsDict[name];
      const unitAmounts = [];

      for (const [unit, amount] of Object.entries(ingredient.units)) {
        //format amount
        let formattedAmount;
        if (amount % 1 === 0) {
          formattedAmount = amount.toString();
        } else {
          formattedAmount = parseFloat(amount.toPrecision(2)).toString();
        }

        if (unit) {
          unitAmounts.push(`${formattedAmount} ${unit}`);
        }
        else {
          unitAmounts.push(formattedAmount);
        }

      }

      const amountStr = unitAmounts.join(" and ");
      const li = document.createElement("li");
      li.textContent = `${amountStr} ${name}`;
      return li;
    });

    // update the DOM
    ingredientsList.replaceChildren(...newListItems);
  };

  // find all ingredient inputs and add listeners
  const ingredientInputs = document.querySelectorAll(
    'input[id^="ingredient_amount_"], input[id^="ingredient_unit_"], input[id^="ingredient_name_"], ' +
    'input[id^="extra_ingredient_amount_"], input[id^="extra_ingredient_unit_"], input[id^="extra_ingredient_name_"], '+
    'input[id="extra_step_ingredient_amount"], input[id="extra_step_ingredient_unit"], input[id="extra_step_ingredient_name"]'
  );

  ingredientInputs.forEach(input => {
    input.addEventListener("input", updateIngredientsList);
  });

  // Initial update on page load
  updateIngredientsList();
}

// Phase 5: As-you-type search
const searchInput = document.querySelector('form.search-form input[type="search"]');
const searchResults = document.querySelector('section.recipes ul.recipe-list');

if (searchInput && searchResults) {
  searchInput.addEventListener("input", async () => {
    const query = searchInput.value;
    
    // Build URL with query parameter
    const url = new URL("/api/s", window.location.origin);
    url.searchParams.set("q", query);
    
    try {
      const response = await fetch(url);
      const data = await response.json();
      
      // Check if query still matches (handle concurrency)
      if (data.query !== searchInput.value) {
        return; // Outdated response, ignore it
      }
      
      // Build new recipe cards
      const newListItems = data.results.map(recipe => {
        const li = document.createElement("li");
        const article = document.createElement("article");
        article.className = "recipe-card";
        
        const link = document.createElement("a");
        link.className = "card__link";
        link.href = `/recipe/${recipe.id}`;
        
        const figure = document.createElement("figure");
        figure.className = "card__media";
        
        if (recipe.photo) {
          const img = document.createElement("img");
          img.src = recipe.photo;
          img.alt = `Photo of ${recipe.title}`;
          img.width = 640;
          img.height = 640;
          img.loading = "lazy";
          figure.appendChild(img);
        }
        
        link.appendChild(figure);
        
        const cardBody = document.createElement("div");
        cardBody.className = "card__body";
        
        const title = document.createElement("h3");
        title.className = "card__title";
        title.textContent = recipe.title;
        cardBody.appendChild(title);
        
        const tagsUl = document.createElement("ul");
        tagsUl.className = "tags";
        
        recipe.tags.forEach(tagName => {
          const tagLi = document.createElement("li");
          const tagLink = document.createElement("a");
          tagLink.href = `/s?q=tag:${tagName}`;
          tagLink.textContent = `#${tagName}`;
          tagLi.appendChild(tagLink);
          tagsUl.appendChild(tagLi);
        });
        
        cardBody.appendChild(tagsUl);
        link.appendChild(cardBody);
        article.appendChild(link);
        li.appendChild(article);
        
        return li;
      });
      
      // Update the DOM
      searchResults.replaceChildren(...newListItems);
    } catch (error) {
      console.error("Search error:", error);
    }
  });
}



