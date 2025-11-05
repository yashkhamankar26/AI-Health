"""
Unit tests for content filtering system.
Tests healthcare keyword detection and filtering logic.
"""

import pytest
from app.content_filter import (
    is_health_related,
    get_refusal_message,
    should_process_query,
    REFUSAL_MESSAGE,
    HEALTHCARE_KEYWORDS
)


class TestIsHealthRelated:
    """Test cases for is_health_related function."""
    
    def test_healthcare_queries_return_true(self):
        """Test that healthcare-related queries are correctly identified."""
        healthcare_queries = [
            "I have a headache",
            "What are the symptoms of diabetes?",
            "How to treat a fever?",
            "I need to see a doctor",
            "My blood pressure is high",
            "What medication should I take for pain?",
            "I'm experiencing chest pain",
            "How to prevent heart disease?",
            "What are the side effects of this drug?",
            "I need emergency medical help",
            "How to manage stress and anxiety?",
            "What should I eat for better nutrition?",
            "I'm pregnant and have questions",
            "How to treat a wound?",
            "What are the signs of a stroke?"
        ]
        
        for query in healthcare_queries:
            assert is_health_related(query), f"Query should be healthcare-related: {query}"
    
    def test_non_healthcare_queries_return_false(self):
        """Test that non-healthcare queries are correctly rejected."""
        non_healthcare_queries = [
            "What's the weather today?",
            "How to cook pasta?",
            "What's the capital of France?",
            "Tell me a joke",
            "How to fix my car?",
            "What's the latest news?",
            "How to learn programming?",
            "What movies should I watch?",
            "How to invest in stocks?",
            "What's the best restaurant nearby?",
            "How to play guitar?",
            "What's 2 + 2?",
            "Tell me about history",
            "How to travel to Japan?",
            "What's the meaning of life?"
        ]
        
        for query in non_healthcare_queries:
            assert not is_health_related(query), f"Query should not be healthcare-related: {query}"
    
    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        test_cases = [
            "I have a HEADACHE",
            "What are SYMPTOMS of flu?",
            "My DOCTOR said...",
            "HEART problems",
            "MEDICAL advice needed"
        ]
        
        for query in test_cases:
            assert is_health_related(query), f"Case-insensitive matching failed for: {query}"
    
    def test_partial_keyword_matching(self):
        """Test that keywords are found within larger words and sentences."""
        test_cases = [
            "My headaches are getting worse",
            "The doctor's appointment is tomorrow",
            "I'm feeling symptoms of something",
            "Heart-related issues concern me",
            "Medical professionals recommend this"
        ]
        
        for query in test_cases:
            assert is_health_related(query), f"Partial matching failed for: {query}"
    
    def test_edge_cases(self):
        """Test edge cases and invalid inputs."""
        # Empty string
        assert not is_health_related("")
        
        # None input
        assert not is_health_related(None)
        
        # Non-string input
        assert not is_health_related(123)
        assert not is_health_related([])
        assert not is_health_related({})
        
        # Whitespace only
        assert not is_health_related("   ")
        assert not is_health_related("\n\t")
    
    def test_mixed_content_queries(self):
        """Test queries that mix healthcare and non-healthcare content."""
        mixed_queries = [
            "I have a headache, also what's the weather?",
            "After seeing the doctor, I want to watch a movie",
            "My symptoms include fever, and I'm also hungry",
            "The medication works well, unlike my broken car"
        ]
        
        for query in mixed_queries:
            assert is_health_related(query), f"Mixed content query should be healthcare-related: {query}"
    
    def test_healthcare_keywords_coverage(self):
        """Test that all defined healthcare keywords are properly detected."""
        # Test a sample of keywords to ensure they work
        sample_keywords = [
            "symptom", "doctor", "medicine", "hospital", "pain", 
            "treatment", "health", "medical", "emergency", "therapy"
        ]
        
        for keyword in sample_keywords:
            assert keyword in HEALTHCARE_KEYWORDS, f"Keyword {keyword} should be in HEALTHCARE_KEYWORDS"
            assert is_health_related(f"I need help with {keyword}"), f"Keyword {keyword} not detected"


class TestGetRefusalMessage:
    """Test cases for get_refusal_message function."""
    
    def test_returns_correct_message(self):
        """Test that the function returns the correct refusal message."""
        expected_message = "Sorry, I can only assist with healthcare-related queries."
        assert get_refusal_message() == expected_message
    
    def test_message_consistency(self):
        """Test that the message is consistent with the constant."""
        assert get_refusal_message() == REFUSAL_MESSAGE


class TestShouldProcessQuery:
    """Test cases for should_process_query function."""
    
    def test_healthcare_query_processing(self):
        """Test that healthcare queries are approved for processing."""
        healthcare_queries = [
            "I have a fever",
            "What are diabetes symptoms?",
            "Need medical advice"
        ]
        
        for query in healthcare_queries:
            should_process, message = should_process_query(query)
            assert should_process, f"Healthcare query should be processed: {query}"
            assert message == "", f"No refusal message should be returned for healthcare query: {query}"
    
    def test_non_healthcare_query_rejection(self):
        """Test that non-healthcare queries are rejected with refusal message."""
        non_healthcare_queries = [
            "What's the weather?",
            "How to cook?",
            "Tell me a joke"
        ]
        
        for query in non_healthcare_queries:
            should_process, message = should_process_query(query)
            assert not should_process, f"Non-healthcare query should be rejected: {query}"
            assert message == REFUSAL_MESSAGE, f"Refusal message should be returned for non-healthcare query: {query}"
    
    def test_return_type(self):
        """Test that the function returns the correct tuple type."""
        should_process, message = should_process_query("I have a headache")
        assert isinstance(should_process, bool)
        assert isinstance(message, str)
        
        should_process, message = should_process_query("What's the weather?")
        assert isinstance(should_process, bool)
        assert isinstance(message, str)


class TestHealthcareKeywords:
    """Test cases for healthcare keywords list."""
    
    def test_keywords_are_strings(self):
        """Test that all keywords are strings."""
        for keyword in HEALTHCARE_KEYWORDS:
            assert isinstance(keyword, str), f"Keyword should be string: {keyword}"
    
    def test_keywords_are_lowercase(self):
        """Test that keywords are in lowercase for consistent matching."""
        for keyword in HEALTHCARE_KEYWORDS:
            assert keyword == keyword.lower(), f"Keyword should be lowercase: {keyword}"
    
    def test_no_empty_keywords(self):
        """Test that there are no empty keywords."""
        for keyword in HEALTHCARE_KEYWORDS:
            assert keyword.strip(), f"Keyword should not be empty: '{keyword}'"
    
    def test_keywords_list_not_empty(self):
        """Test that the keywords list is not empty."""
        assert len(HEALTHCARE_KEYWORDS) > 0, "Healthcare keywords list should not be empty"
    
    def test_essential_keywords_present(self):
        """Test that essential healthcare keywords are present."""
        essential_keywords = [
            "health", "medical", "doctor", "symptom", "pain", 
            "treatment", "medicine", "hospital", "emergency", "disease"
        ]
        
        for keyword in essential_keywords:
            assert keyword in HEALTHCARE_KEYWORDS, f"Essential keyword missing: {keyword}"


class TestIntegrationScenarios:
    """Integration test scenarios for content filtering."""
    
    def test_realistic_user_queries(self):
        """Test with realistic user queries that might be submitted."""
        test_scenarios = [
            # Healthcare queries that should pass
            ("I've been having headaches for the past week, what could be causing them?", True),
            ("My child has a fever of 101°F, should I be concerned?", True),
            ("What are the early signs of diabetes I should watch for?", True),
            ("I'm experiencing chest pain and shortness of breath", True),
            ("Can you recommend some exercises for back pain relief?", True),
            ("What medications are safe during pregnancy?", True),
            ("How do I know if I need to see a cardiologist?", True),
            ("I'm feeling anxious and stressed, what can help?", True),
            
            # Non-healthcare queries that should be rejected
            ("What's the best pizza place in town?", False),
            ("How do I reset my password?", False),
            ("What's the weather forecast for tomorrow?", False),
            ("Can you help me with my math homework?", False),
            ("What's the latest news about the election?", False),
            ("How do I fix my computer?", False),
            ("What movies are playing this weekend?", False),
            ("Can you tell me a funny story?", False),
        ]
        
        for query, expected_healthcare in test_scenarios:
            is_healthcare = is_health_related(query)
            should_process, refusal_msg = should_process_query(query)
            
            assert is_healthcare == expected_healthcare, f"Query classification failed for: {query}"
            assert should_process == expected_healthcare, f"Processing decision failed for: {query}"
            
            if expected_healthcare:
                assert refusal_msg == "", f"No refusal message expected for healthcare query: {query}"
            else:
                assert refusal_msg == REFUSAL_MESSAGE, f"Refusal message expected for non-healthcare query: {query}"


if __name__ == "__main__":
    pytest.main([__file__])