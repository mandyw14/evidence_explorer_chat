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

   "General Complementary and Alternative Medicine": ["complementary medicine","complementary therapy","alternative medicine", "alternative therapy", "Holistic Health", "Integrative Medicine"],
    
    "Mind-body": [
        "mindfulness",
        "meditation",
        "yoga",
        "tai chi",
        "qigong",
    ],

    "Exercise": [
        "exercise",
        "physical activity",
        "yoga",
        "resistance training",
    ],
  
    "Diets & Nutrition": [
        "diet",
        "nutrition",
        "Mediterranean",
        "Paleo",
        "MIND",
        "Ketogenic",
        "nutrition",
        "vegetarian",
        "vegan",
        "antioxidant",
        "high-protein diet",
        "low-fat diet",
        "low-carbohydrate diet",
        "dietician",
    ],
            
    "Supplements & Nutraceuticals": [
        "supplements",
        "nutraceuticals",
        "probiotics",
        "omega-3",
        "vitamin D",
        "microbiome",
        "fecal transplants",
        "microbiome treatments",
        "prebiotics",
        "byturic acid",
        "fish oils",
        "hyperbaric oxygen",
        "antioxidants",
        "magnesium"
    ],

    "Gut Health": [
        "microbiome",
        "fecal microbiota transplants",
        "microbiota",
        "gut health",
        "probiotic",
    ],
    

    "Neurotechnology": [
        "transcranial magnetic stimulation",
        "transcranial direct current stimulation",
        "intermittent theta burst stimulation",
        "focused ultrasound",
        "neurofeedback",
        "biofeedback",
        "deep brain stimulation",
        "vagus nerve stimulation",
        "red light therapy",
        "electroceutical",
        "spinal cord stimulation",
    ],

    "Neurostimulation": [
        "Transcranial magnetic stimulation", "Transcranial Direct Current Stimulation", 
        "Intermittent theta-burst stimulation", 
         "ultrasound",  "Focused Ultrasound", "transcranial focused ultrasound", 
        "Light Flickering Stimulation",   "Epidural Electrical Stimulation",  "electrical stimulation",      
        "Frequency-Domain Near-Infrared Spectroscopy", "fNIRS", 
        "spinal cord stimulation",
        "deep brain stimulation",
        "vagus nerve stimulation",
    ]

    
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
        "examples": [
            "resistance training",
            "aerobic exercise",
            "weight training",
            "running",
        ],
        "video": ""
    },

    "Neurotechnology": {
        "description": """
Neurotechnology involves a variety of technologies that stimulate the brain, both invasively and non-invasively. 
It also includes neurofeedback technology. Generally, this also includes the term "neuromodulation". 
""",
        "examples": [
            "Transcranial magnetic stimulation",
            "vagus nerve stimulation",
            "neurofeedback",
            "functional electrical stimulation",
            "ultrasound",
        ],
        "video": ""
    },

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
