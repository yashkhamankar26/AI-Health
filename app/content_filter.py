"""
Content filtering system for healthcare chatbot.
Implements dual-layer filtering: keyword-based and AI system prompt.
"""

# Standardized refusal message constant
REFUSAL_MESSAGE = "Sorry, I can only assist with healthcare-related queries."

# Comprehensive healthcare keywords list
HEALTHCARE_KEYWORDS = [
    # Medical conditions and diseases
    "symptom", "symptoms", "disease", "illness", "condition", "disorder", "syndrome",
    "infection", "virus", "bacteria", "cancer", "tumor", "diabetes", "hypertension",
    "asthma", "arthritis", "depression", "anxiety", "migraine", "headache", "fever",
    "pain", "ache", "injury", "wound", "fracture", "sprain", "strain", "allergy",
    "allergic", "rash", "eczema", "psoriasis", "pneumonia", "bronchitis", "flu",
    "cold", "cough", "sore throat", "nausea", "nauseous", "vomiting", "diarrhea", 
    "constipation", "dizzy", "dizziness", "fatigue", "tired", "weakness", "weak",
    "swelling", "swollen", "inflammation", "bruise", "bleeding", "discharge",
    "breathe", "breathing", "breath", "shortness of breath", "faint", "fainting",
    "unconscious", "lightheaded", "blackout",
    
    # Body parts and anatomy
    "heart", "lung", "liver", "kidney", "brain", "stomach", "intestine", "bone",
    "muscle", "joint", "skin", "eye", "nose", "throat", "chest", "back",
    "neck", "shoulder", "arm", "leg", "hand", "foot", "head", "abdomen", "pelvis",
    
    # Medical procedures and treatments
    "treatment", "therapy", "surgery", "operation", "procedure", "examination",
    "diagnosis", "medical test", "screening", "vaccination", "vaccine", "immunization",
    "medication", "medicine", "drug", "prescription", "dosage", "antibiotic",
    "painkiller", "insulin", "chemotherapy", "radiation", "physical therapy",
    "rehabilitation", "recovery", "healing", "cure", "remedy",
    
    # Healthcare professionals and facilities
    "doctor", "physician", "nurse", "surgeon", "specialist", "cardiologist",
    "dermatologist", "neurologist", "psychiatrist", "psychologist", "therapist",
    "pharmacist", "dentist", "optometrist", "hospital", "clinic", "emergency room",
    "pharmacy", "medical center", "healthcare", "health care",
    
    # Medical terms and concepts
    "medical", "clinical", "health", "healthy", "wellness", "fitness", "nutrition",
    "diet", "exercise", "sleep", "stress", "mental health", "physical health",
    "blood pressure", "heart rate", "body temperature", "weight", "bmi", "cholesterol",
    "glucose", "blood sugar", "immune system", "metabolism", "hormone", "vitamin",
    "mineral", "supplement", "side effect", "adverse reaction", "contraindication",
    
    # Emergency and urgent care
    "emergency", "urgent", "911", "ambulance", "first aid", "cpr", "choking",
    "bleeding", "unconscious", "seizure", "stroke", "heart attack", "overdose",
    "poisoning", "burn", "cut", "bite", "sting",
    
    # Preventive care and lifestyle
    "prevention", "preventive", "screening", "checkup", "annual exam", "mammogram",
    "colonoscopy", "pap smear", "blood work", "x-ray", "mri", "ct scan", "ultrasound",
    "hygiene", "handwashing", "sanitizer", "mask", "social distancing", "quarantine",
    
    # Women's health
    "pregnancy", "pregnant", "prenatal", "postnatal", "labor", "delivery", "birth",
    "contraception", "menstruation", "menopause", "gynecology", "obstetrics",
    
    # Mental health
    "counseling", "therapy", "meditation", "mindfulness", "stress management",
    "mental wellness", "emotional health", "bipolar", "schizophrenia", "ptsd",
    "adhd", "autism", "eating disorder", "substance abuse", "addiction"
]


def is_health_related(query: str) -> bool:
    """
    Determine if a query is healthcare-related using keyword-based filtering.
    
    This function serves as the first gate in the dual-layer content filtering system.
    It performs a case-insensitive search for healthcare keywords in the user query.
    
    Args:
        query (str): The user's input query to evaluate
        
    Returns:
        bool: True if the query contains healthcare-related keywords, False otherwise
        
    Requirements addressed:
        - 3.1: Process healthcare-related questions with AI model
        - 3.2: Respond with refusal message for non-healthcare questions  
        - 3.3: Use keyword-based filtering as first gate
    """
    if not query or not isinstance(query, str):
        return False
    
    # Convert query to lowercase for case-insensitive matching
    query_lower = query.lower()
    
    # Check if any healthcare keyword is present in the query
    for keyword in HEALTHCARE_KEYWORDS:
        if keyword.lower() in query_lower:
            return True
    
    return False


def get_refusal_message() -> str:
    """
    Get the standardized refusal message for non-healthcare queries.
    
    Returns:
        str: The standard refusal message
        
    Requirements addressed:
        - 3.2: Respond with standardized refusal message for non-healthcare questions
    """
    return REFUSAL_MESSAGE


def should_process_query(query: str) -> tuple[bool, str]:
    """
    Determine if a query should be processed and return appropriate response.
    
    This is a convenience function that combines the filtering logic and 
    returns both the decision and the appropriate message.
    
    Args:
        query (str): The user's input query to evaluate
        
    Returns:
        tuple[bool, str]: (should_process, message_if_rejected)
        - should_process: True if query should be sent to AI, False if rejected
        - message_if_rejected: Refusal message if query is rejected, empty string if accepted
        
    Requirements addressed:
        - 3.3: Use keyword-based filtering as first gate
        - 3.4: Use strict healthcare-focused system prompt
    """
    if is_health_related(query):
        return True, ""
    else:
        return False, get_refusal_message()