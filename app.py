from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv
load_dotenv()

# debugging: print the loaded API key
# print("Loaded Spoonacular key:", os.getenv("SPOONACULAR_API_KEY"))

app = Flask(__name__)

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

# 🧠 Mocked ingredient detector (replace with YOLO later)
def detect_ingredients_mock(image_path):
    # In real use, run YOLOv8 on the image.
    # For now, return sample data for testing.
    return ["eggs", "milk", "spinach", "cheese"]

# 🥘 Fetch recipes from Spoonacular
def fetch_recipes(ingredients):
    joined = ",".join(ingredients)
    url = f"https://api.spoonacular.com/recipes/findByIngredients?ingredients={joined}&number=5&apiKey={SPOONACULAR_API_KEY}"
    res = requests.get(url)
    print("Fetching recipes for:", joined)
    print("Response code:", res.status_code)
    print("Response text:", res.text[:300])
    if res.status_code == 200:
        return res.json()
    else:
        return []



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["image"]
    path = f"static/{file.filename}"
    file.save(path)

    ingredients = detect_ingredients_mock(path)
    recipes = fetch_recipes(ingredients)

    return jsonify({
        "ingredients": ingredients,
        "recipes": recipes
    })

if __name__ == "__main__":
    app.run(debug=True)
