# dictionaries.py


COMMON_CONDITIONS = [
    "multiple sclerosis",
    "Parkinson disease",
    "Alzheimer disease",
    "dementia",
    "ADHD",
    "Other / type your own",
]

INTERVENTION_CATEGORIES = {

   "General Complementary and Alternative Medicine": ["complementary medicine", "alternative medicine", "Holistic", "Integrative Medicine"],
    
    "Mind-body": [
        "mindfulness",
        "meditation",
        "yoga",
        "tai chi",
    ],

    "Exercise": [
        "exercise",
        "physical activity",
        "yoga",
        "resistance training",
    ],
  
    "Diets & Nutrition": [
        "nutrition",
        "Mediterranean",
        "Paleo",
        "MIND",
        "Ketogenic",
        "vegetarian",
        "vegan",
        "low-fat diet",
        "low-carbohydrate diet",
    ],
            
    "Supplements & Nutraceuticals": [
        "supplements",
        "nutraceuticals",
        "probiotics",
        "omega-3",
        "vitamin D",
        "prebiotics",
        "fish oils",
        "antioxidants",
        "magnesium"
    ],
    
}


INTERVENTION_DESCRIPTIONS = {

    "Mind-body": {
        "description": """
Mind-body approaches explore how behaviours, lifestyle, and experiences 
can influence brain health and neurological function.

Examples include movement-based approaches, psychological therapies,
stress regulation practices, and rehabilitation strategies.
""",
        "examples": [
            "exercise",
            "mindfulness",
            "yoga",
            "cognitive behavioural therapy",
            "rehabilitation",
        ],
        "video": ""
    },


    "Nutraceuticals": {
        "description": """
Nutraceutical and dietary approaches explore how nutrients, dietary patterns, 
and naturally occurring compounds may influence neurological health.

Research may examine inflammation, metabolism, the gut-brain connection, 
cellular energy, or other biological pathways.
""",
        "examples": [
            "omega-3",
            "vitamin D",
            "creatine",
            "probiotics",
            "ketogenic diet",
        ],
        "video": ""
    },

    "Exercise": {
        "description": """
There are many types of exercise that exist. These approaches may include aerobic exercise (like a cardio workout), resistance (like lifting weights), or special programs like dance or pilates, 
and sometimes practices like yoga or Tai Chi.
""",
        "Diet & Nutrition": {
        "description": """
There are so many different kids of diets that exist, including, vegan, vegetarian, paleo diets, ketogenic diets, the MIND diet, 
and mediterranean diets. 
""",
        "examples": [
            "Ketogenic diet",
            "MIND diet",
            "Vegetarian diet",
        ],
        "video": ""
    },
}
