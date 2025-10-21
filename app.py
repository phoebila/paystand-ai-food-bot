from flask import Flask, render_template, request, jsonify
import requests
from transformers import pipeline
import random

app = Flask(__name__)

# ----------------- Lightweight AI summarizer -----------------
# Uses a small, CPU-friendly model
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# ----------------- Fetch Recipes from TheMealDB -----------------
def fetch_recipes(ingredients):
    recipes = []
    for ingredient in ingredients:
        url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient.strip()}"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and res.json().get("meals"):
                for meal in res.json()["meals"][:5]:  # limit 5 per ingredient
                    recipes.append({
                        "title": meal["strMeal"],
                        "image": meal["strMealThumb"],
                        "id": meal["idMeal"],
                        "link": f"https://www.themealdb.com/meal/{meal['idMeal']}"
                    })
        except Exception:
            pass

    # Remove duplicates
    seen = set()
    unique_recipes = []
    for r in recipes:
        if r["title"] not in seen:
            seen.add(r["title"])
            unique_recipes.append(r)

    return unique_recipes[:15]  # max 15 recipes

# ----------------- Fetch full recipe details -----------------
def fetch_meal_details(meal_id):
    try:
        res = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data and data.get("meals"):
                return data["meals"][0]
    except Exception:
        pass
    return None

# ----------------- Determine meal complexity -----------------
def classify_meal_speed(instructions):
    if not instructions:
        return "Unknown"
    word_count = len(instructions.split())
    if word_count < 80:
        return "Quick"
    elif word_count < 150:
        return "Moderate"
    else:
        return "Weekend Treat"

# ----------------- AI + Smart Weekly Spread -----------------
def summarize_and_spread(recipes):
    if not recipes:
        return "No recipes found for these ingredients."

    # Fetch full details and classify meals
    detailed_meals = []
    for r in recipes[:10]:
        details = fetch_meal_details(r["id"])
        if details:
            category = classify_meal_speed(details.get("strInstructions", ""))
            detailed_meals.append({
                "title": details["strMeal"],
                "category": category,
                "link": details["strSource"] or details["strYoutube"] or f"https://www.themealdb.com/meal/{r['id']}"
            })

    if not detailed_meals:
        return "Could not analyze meal details."

    # Group by category
    quick_meals = [m for m in detailed_meals if m["category"] == "Quick"]
    moderate_meals = [m for m in detailed_meals if m["category"] == "Moderate"]
    weekend_meals = [m for m in detailed_meals if m["category"] == "Weekend Treat"]

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    week_plan = []

    for i, day in enumerate(days):
        if i < 4 and quick_meals:
            meal = quick_meals.pop(0)
        elif i < 6 and moderate_meals:
            meal = moderate_meals.pop(0)
        elif weekend_meals:
            meal = weekend_meals.pop(0)
        else:
            meal = random.choice(detailed_meals)
        week_plan.append(f"{day}: {meal['title']} ({meal['category']}) — {meal['link']}")

    # Summarize overall plan with Hugging Face summarizer
    try:
        text = ". ".join([f"{m['title']} is {m['category']}" for m in detailed_meals])
        ai_summary = summarizer(
            f"Analyze these meals and explain how they fit into a balanced 7-day schedule: {text}",
            max_length=150, min_length=60, do_sample=False
        )[0]['summary_text']
    except Exception:
        ai_summary = "Here’s your smart weekly plan:"

    # Combine everything into a readable summary
    final_text = ai_summary + "\n\nSmart 7-Day Meal Plan:\n" + "\n".join(week_plan)
    return final_text

# ----------------- Generate Smart Grocery List -----------------
def generate_grocery_list(ingredients, recipes):
    all_ingredients = set()

    for r in recipes:
        url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={r['title']}"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and res.json().get("meals"):
                meal = res.json()["meals"][0]
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    if ing and ing.strip():
                        all_ingredients.add(ing.strip())
        except Exception:
            pass

    missing = list(all_ingredients - set(ingredients))
    return missing[:20]

# ----------------- Flask Routes -----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    ingredients_input = data.get("ingredients", "")
    ingredients = [i.strip() for i in ingredients_input.split(",") if i.strip()]

    # Fetch recipes
    recipes = fetch_recipes(ingredients)

    # Smart meal spread with AI summary
    summary = summarize_and_spread(recipes)

    # Grocery list
    grocery_list = generate_grocery_list(ingredients, recipes)

    return jsonify({
        "ingredients": ingredients,
        "recipes": recipes,
        "summary": summary,
        "grocery_list": grocery_list
    })

if __name__ == "__main__":
    app.run(debug=True)
