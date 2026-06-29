# dictionaries.py


COMMON_CONDITIONS = [
    "multiple sclerosis",
    "Parkinson disease",
    "Alzheimer disease",
    "dementia",
    "epilepsy",
    "migraine",
    "stroke",
    "traumatic brain injury",
    "concussion",
    "autism spectrum disorder",
    "ADHD",
    "depression",
    "anxiety",
    "chronic pain",
    "neuropathy",
    "amyotrophic lateral sclerosis",
    "Huntington disease",
    "cerebral palsy",
    "spinal cord injury",
    "Other / type your own",
]

INTERVENTION_CATEGORIES = {

   "Complementary Medicine",
    
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
    
    "Nutraceuticals": [
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
There are many types of exercise that exist. These approaches may include aerobic exercise, resistance/weight training, dance, pilates, 
and sometimes practices like yoga or Tai Chi.
""",
        "examples": [
            "transcranial magnetic stimulation",
            "focused ultrasound",
            "neurofeedback",
            "virtual reality",
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
