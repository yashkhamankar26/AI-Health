"""
Edge case tests for content filtering system.

Tests complex scenarios, boundary conditions, and edge cases
for the healthcare content filtering functionality.
"""

import pytest
from app.content_filter import (
    is_health_related,
    should_process_query,
    get_refusal_message,
    REFUSAL_MESSAGE,
    HEALTHCARE_KEYWORDS
)


class TestContentFilterEdgeCases:
    """Test edge cases for content filtering."""
    
    def test_minimal_healthcare_keywords(self):
        """Test queries with minimal healthcare keywords."""
        minimal_queries = [
            "pain",  # Single keyword
            "doctor?",  # Keyword with punctuation
            "HEALTH",  # Uppercase keyword
            "medical.",  # Keyword with period
            "symptom!",  # Keyword with exclamation
            "medicine???",  # Keyword with multiple punctuation
        ]
        
        for query in minimal_queries:
            assert is_health_related(query), f"Minimal healthcare query should pass: {query}"
            should_process, message = should_process_query(query)
            assert should_process, f"Minimal healthcare query should be processed: {query}"
            assert message == "", f"No refusal message for healthcare query: {query}"
    
    def test_healthcare_keywords_in_non_healthcare_context(self):
        """Test healthcare keywords used in non-healthcare contexts."""
        # These should still be considered healthcare-related due to keyword presence
        ambiguous_queries = [
            "I'm reading a medical journal about cooking",  # Medical + cooking
            "The doctor character in this movie is funny",  # Doctor + entertainment
            "My car's engine has symptoms of failure",  # Symptoms + automotive
            "This medicine bottle makes a good vase",  # Medicine + crafts
            "The hospital in the video game is realistic",  # Hospital + gaming
        ]
        
        for query in ambiguous_queries:
            assert is_health_related(query), f"Query with healthcare keywords should pass: {query}"
            should_process, message = should_process_query(query)
            assert should_process, f"Query with healthcare keywords should be processed: {query}"
    
    def test_healthcare_abbreviations_and_acronyms(self):
        """Test healthcare abbreviations and acronyms."""
        abbreviation_queries = [
            "I need to see an MD",
            "My BP is high",
            "The ER was busy",
            "I have ADHD symptoms",
            "My BMI is concerning",
            "The ICU staff was helpful",
            "I need a CBC test",
            "My EKG results are ready"
        ]
        
        # Note: These might not be detected if abbreviations aren't in keyword list
        # This test documents current behavior and can guide future improvements
        for query in abbreviation_queries:
            result = is_health_related(query)
            # Document the current behavior - some may pass, some may not
            print(f"Abbreviation query '{query}': {result}")
    
    def test_healthcare_keywords_with_typos(self):
        """Test healthcare keywords with common typos."""
        typo_queries = [
            "I have a hedache",  # headache
            "My stomache hurts",  # stomach
            "I need medecine",  # medicine
            "The docter said",  # doctor
            "I have symtoms",  # symptoms
            "My blod pressure",  # blood
            "I feel nauscious",  # nauseous
        ]
        
        # Current implementation may not catch typos
        # This test documents expected behavior for future improvements
        for query in typo_queries:
            result = is_health_related(query)
            print(f"Typo query '{query}': {result}")
            # Most typos will likely not be detected with current keyword matching
    
    def test_multilingual_healthcare_terms(self):
        """Test non-English healthcare terms."""
        multilingual_queries = [
            "I have dolor in my chest",  # Spanish: pain
            "Je suis malade",  # French: I am sick
            "Ich habe Kopfschmerzen",  # German: I have headaches
            "Tengo fiebre",  # Spanish: I have fever
            "Mi duele la cabeza",  # Spanish: My head hurts
        ]
        
        # Current implementation only supports English keywords
        # This test documents current limitations
        for query in multilingual_queries:
            result = is_health_related(query)
            print(f"Multilingual query '{query}': {result}")
            # These will likely not be detected with current English-only keywords
    
    def test_very_long_healthcare_queries(self):
        """Test very long queries with healthcare content."""
        long_healthcare_query = (
            "I have been experiencing persistent headaches for the past three weeks, "
            "along with occasional dizziness and nausea. The pain is usually located "
            "on the right side of my head and tends to worsen in the afternoon. "
            "I have tried over-the-counter pain medications like ibuprofen and "
            "acetaminophen, but they only provide temporary relief. I'm also "
            "experiencing some sensitivity to light and sound during these episodes. "
            "My sleep patterns have been disrupted, and I've noticed that stress "
            "seems to trigger these headaches more frequently. I'm wondering if "
            "this could be related to my recent change in work schedule or if "
            "I should be concerned about something more serious. Should I see "
            "a doctor for further evaluation, and what kind of tests might be "
            "recommended to determine the underlying cause of these symptoms?"
        )
        
        assert is_health_related(long_healthcare_query)
        should_process, message = should_process_query(long_healthcare_query)
        assert should_process
        assert message == ""
    
    def test_very_long_non_healthcare_queries(self):
        """Test very long queries without healthcare content."""
        long_non_healthcare_query = (
            "I'm planning a vacation to Europe next summer and I'm trying to decide "
            "between visiting Italy, France, or Spain. I've heard great things about "
            "the food in Italy, especially the pasta and pizza in Rome and the "
            "gelato in Florence. France appeals to me because of the art museums "
            "in Paris, particularly the Louvre and the Musée d'Orsay, and I'd love "
            "to see the Eiffel Tower and walk along the Seine River. Spain is "
            "interesting because of the architecture in Barcelona, especially the "
            "works of Antoni Gaudí like the Sagrada Familia and Park Güell. "
            "I'm also curious about the flamenco dancing and the nightlife in Madrid. "
            "The weather is important to me, so I'm wondering which country would "
            "have the best climate in July. Budget is also a consideration, as "
            "I'm a student and need to keep costs reasonable. What would you "
            "recommend for a first-time traveler to Europe who wants to experience "
            "culture, history, and good food without breaking the bank?"
        )
        
        assert not is_health_related(long_non_healthcare_query)
        should_process, message = should_process_query(long_non_healthcare_query)
        assert not should_process
        assert message == REFUSAL_MESSAGE
    
    def test_queries_with_mixed_languages(self):
        """Test queries mixing English healthcare terms with other languages."""
        mixed_queries = [
            "I have dolor and need a doctor",  # Spanish + English
            "My tête hurts, I need medicine",  # French + English
            "Je suis sick and need help",  # French + English
            "Tengo pain in my stomach",  # Spanish + English
        ]
        
        for query in mixed_queries:
            # Should be detected due to English healthcare keywords
            assert is_health_related(query), f"Mixed language healthcare query should pass: {query}"
    
    def test_queries_with_numbers_and_measurements(self):
        """Test healthcare queries with numbers and measurements."""
        numeric_queries = [
            "My blood pressure is 140/90",
            "I have a fever of 101.5 degrees",
            "My weight is 180 lbs and I'm concerned",
            "I take 500mg of medication daily",
            "My heart rate is 120 bpm",
            "I'm 6 feet tall and have back pain",
            "My cholesterol is 250 mg/dL",
            "I need to lose 20 pounds for my health"
        ]
        
        for query in numeric_queries:
            assert is_health_related(query), f"Numeric healthcare query should pass: {query}"
    
    def test_queries_with_special_characters(self):
        """Test queries with special characters and symbols."""
        special_char_queries = [
            "I have a headache :-(",
            "My doctor said I'm healthy! :)",
            "Pain level: 8/10",
            "Symptoms include: fever, cough, fatigue",
            "Medicine dosage -> 2 pills daily",
            "Health status = concerning",
            "Doctor's note: rest & hydration",
            "Emergency!!! Need medical help NOW!!!"
        ]
        
        for query in special_char_queries:
            assert is_health_related(query), f"Special character healthcare query should pass: {query}"
    
    def test_queries_with_urls_and_references(self):
        """Test queries mentioning URLs or references."""
        reference_queries = [
            "I read on WebMD about my symptoms",
            "According to Mayo Clinic, I might have flu",
            "My doctor's website says to take medicine",
            "The health article mentioned these symptoms",
            "I found this medical study about my condition"
        ]
        
        for query in reference_queries:
            assert is_health_related(query), f"Reference healthcare query should pass: {query}"
    
    def test_boundary_keyword_matching(self):
        """Test boundary conditions for keyword matching."""
        boundary_queries = [
            "healthcare",  # Exact keyword
            "healthcareworker",  # Keyword as part of compound word
            "health care",  # Keyword with space
            "health-care",  # Keyword with hyphen
            "HEALTHCARE",  # All caps
            "Healthcare",  # Title case
            "hEaLtHcArE",  # Mixed case
        ]
        
        for query in boundary_queries:
            result = is_health_related(query)
            # Document current behavior - depends on exact keyword list
            print(f"Boundary query '{query}': {result}")
    
    def test_contextual_healthcare_terms(self):
        """Test terms that could be healthcare-related depending on context."""
        contextual_queries = [
            "I'm feeling blue",  # Could be depression or just sad
            "I have a bug",  # Could be illness or software bug
            "My system is down",  # Could be immune system or computer
            "I need a shot",  # Could be injection or photograph
            "I'm running a temperature",  # Could be fever or measurement
            "I have a cold",  # Could be illness or temperature
            "I'm feeling under the weather",  # Idiom for feeling sick
        ]
        
        for query in contextual_queries:
            result = is_health_related(query)
            print(f"Contextual query '{query}': {result}")
            # Results will depend on specific keywords in the list
    
    def test_negated_healthcare_queries(self):
        """Test queries that negate healthcare content."""
        negated_queries = [
            "I don't have any symptoms",
            "I'm not sick",
            "No pain today",
            "I don't need a doctor",
            "Not feeling any symptoms",
            "I'm not taking any medicine",
            "No health problems here"
        ]
        
        for query in negated_queries:
            # Should still be considered healthcare-related due to keywords
            assert is_health_related(query), f"Negated healthcare query should still pass: {query}"
    
    def test_hypothetical_healthcare_queries(self):
        """Test hypothetical or conditional healthcare queries."""
        hypothetical_queries = [
            "What if I had a fever?",
            "If someone has chest pain, what should they do?",
            "Suppose I needed to see a doctor",
            "In case of emergency, what medicine should I take?",
            "What would happen if I had these symptoms?",
            "If my friend has a headache, what should I tell them?"
        ]
        
        for query in hypothetical_queries:
            assert is_health_related(query), f"Hypothetical healthcare query should pass: {query}"
    
    def test_healthcare_queries_with_profanity(self):
        """Test healthcare queries with mild profanity or strong language."""
        profanity_queries = [
            "This damn headache won't go away",
            "I feel like crap, need a doctor",
            "My back hurts like hell",
            "This pain is driving me crazy",
            "I'm sick as hell"
        ]
        
        for query in profanity_queries:
            # Should still be processed as healthcare despite language
            assert is_health_related(query), f"Healthcare query with profanity should pass: {query}"
    
    def test_empty_and_whitespace_edge_cases(self):
        """Test empty and whitespace-only inputs."""
        edge_cases = [
            "",
            " ",
            "   ",
            "\n",
            "\t",
            "\r\n",
            "   \n\t   ",
            None
        ]
        
        for case in edge_cases:
            assert not is_health_related(case), f"Empty/whitespace case should not pass: '{case}'"
            should_process, message = should_process_query(case)
            assert not should_process, f"Empty/whitespace case should not be processed: '{case}'"
            assert message == REFUSAL_MESSAGE, f"Should return refusal message for: '{case}'"
    
    def test_non_string_inputs(self):
        """Test non-string inputs to content filter."""
        non_string_inputs = [
            123,
            [],
            {},
            True,
            False,
            object(),
            lambda x: x
        ]
        
        for input_val in non_string_inputs:
            assert not is_health_related(input_val), f"Non-string input should not pass: {input_val}"
            should_process, message = should_process_query(input_val)
            assert not should_process, f"Non-string input should not be processed: {input_val}"
            assert message == REFUSAL_MESSAGE, f"Should return refusal message for: {input_val}"


class TestHealthcareKeywordEdgeCases:
    """Test edge cases related to healthcare keywords."""
    
    def test_keyword_list_integrity(self):
        """Test that the healthcare keywords list maintains integrity."""
        # Keywords should be non-empty
        assert len(HEALTHCARE_KEYWORDS) > 0, "Healthcare keywords list should not be empty"
        
        # All keywords should be strings
        for keyword in HEALTHCARE_KEYWORDS:
            assert isinstance(keyword, str), f"All keywords should be strings: {keyword}"
            assert keyword.strip(), f"Keywords should not be empty or whitespace: '{keyword}'"
        
        # Keywords should be lowercase for consistent matching
        for keyword in HEALTHCARE_KEYWORDS:
            assert keyword == keyword.lower(), f"Keywords should be lowercase: {keyword}"
        
        # No duplicate keywords
        assert len(HEALTHCARE_KEYWORDS) == len(set(HEALTHCARE_KEYWORDS)), "No duplicate keywords allowed"
    
    def test_essential_medical_terms_coverage(self):
        """Test that essential medical terms are covered."""
        essential_terms = [
            "health", "medical", "doctor", "hospital", "medicine",
            "symptom", "pain", "fever", "cough", "headache",
            "treatment", "therapy", "diagnosis", "prescription",
            "emergency", "urgent", "sick", "illness", "disease"
        ]
        
        missing_terms = []
        for term in essential_terms:
            if term not in HEALTHCARE_KEYWORDS:
                missing_terms.append(term)
        
        if missing_terms:
            print(f"Warning: Essential terms not in keywords: {missing_terms}")
    
    def test_keyword_variations_and_forms(self):
        """Test that keyword variations are handled appropriately."""
        # Test singular/plural forms
        test_pairs = [
            ("symptom", "symptoms"),
            ("doctor", "doctors"),
            ("medicine", "medicines"),
            ("hospital", "hospitals"),
            ("treatment", "treatments")
        ]
        
        for singular, plural in test_pairs:
            singular_query = f"I have a {singular}"
            plural_query = f"I have multiple {plural}"
            
            singular_result = is_health_related(singular_query)
            plural_result = is_health_related(plural_query)
            
            # At least one form should be detected
            assert singular_result or plural_result, f"Either '{singular}' or '{plural}' should be detected"
    
    def test_compound_healthcare_terms(self):
        """Test compound healthcare terms."""
        compound_terms = [
            "healthcare",
            "bloodpressure",
            "heartrate",
            "bodytemperature",
            "stomachache",
            "backpain",
            "headache",
            "toothache"
        ]
        
        for term in compound_terms:
            query = f"I have issues with {term}"
            result = is_health_related(query)
            print(f"Compound term '{term}': {result}")
    
    def test_medical_specialties_and_departments(self):
        """Test medical specialties and department names."""
        medical_specialties = [
            "cardiology", "dermatology", "neurology", "oncology",
            "pediatrics", "psychiatry", "radiology", "surgery",
            "emergency room", "intensive care", "outpatient",
            "clinic", "pharmacy", "laboratory"
        ]
        
        for specialty in medical_specialties:
            query = f"I need to visit {specialty}"
            result = is_health_related(query)
            print(f"Medical specialty '{specialty}': {result}")


class TestContentFilterPerformance:
    """Test content filter performance with edge cases."""
    
    def test_very_long_text_performance(self):
        """Test performance with very long text."""
        # Create a very long text with healthcare keywords scattered throughout
        long_text = "I went to the store and bought groceries. " * 100
        long_text += "I have a headache and need medicine. "
        long_text += "The weather is nice today. " * 100
        
        # Should still detect healthcare content efficiently
        result = is_health_related(long_text)
        assert result, "Should detect healthcare content in long text"
    
    def test_many_repeated_keywords(self):
        """Test with many repeated keywords."""
        repeated_text = "doctor " * 1000 + "I need help"
        
        result = is_health_related(repeated_text)
        assert result, "Should detect healthcare content with repeated keywords"
    
    def test_keyword_at_different_positions(self):
        """Test keyword detection at different text positions."""
        base_text = "This is a long sentence with many words that don't relate to healthcare at all. "
        
        # Keyword at beginning
        beginning_text = "Doctor, " + base_text
        assert is_health_related(beginning_text)
        
        # Keyword at end
        end_text = base_text + " I need a doctor."
        assert is_health_related(end_text)
        
        # Keyword in middle
        middle_text = base_text[:50] + " doctor " + base_text[50:]
        assert is_health_related(middle_text)


class TestRefusalMessageConsistency:
    """Test refusal message consistency across edge cases."""
    
    def test_refusal_message_consistency(self):
        """Test that refusal message is consistent."""
        non_healthcare_queries = [
            "What's the weather?",
            "",
            None,
            123,
            "How to cook pasta?",
            "Tell me a joke"
        ]
        
        for query in non_healthcare_queries:
            should_process, message = should_process_query(query)
            if not should_process:
                assert message == REFUSAL_MESSAGE, f"Inconsistent refusal message for: {query}"
    
    def test_get_refusal_message_function(self):
        """Test get_refusal_message function consistency."""
        message1 = get_refusal_message()
        message2 = get_refusal_message()
        
        assert message1 == message2, "get_refusal_message should return consistent results"
        assert message1 == REFUSAL_MESSAGE, "get_refusal_message should match REFUSAL_MESSAGE constant"
        assert isinstance(message1, str), "Refusal message should be a string"
        assert len(message1) > 0, "Refusal message should not be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])