"""
Integration tests for chat processing with content filtering.
Tests the complete flow from user input through filtering to AI response.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from fastapi.testclient import TestClient

from app.main import app, validate_ai_response, call_openai_api, get_fallback_response
from app.content_filter import get_refusal_message, REFUSAL_MESSAGE
from app.models import ChatIn, ChatOut


class TestChatIntegrationFiltering:
    """Integration tests for chat endpoint with content filtering."""
    
    def setup_method(self):
        """Set up test client and mock data."""
        self.client = TestClient(app)
        self.valid_token = "test_token_123"
        
        # Add token to active tokens for testing
        from app.main import active_tokens
        active_tokens.add(self.valid_token)
    
    def teardown_method(self):
        """Clean up after tests."""
        from app.main import active_tokens
        active_tokens.clear()
    
    def test_healthcare_query_processing_flow(self):
        """Test complete flow for healthcare queries."""
        healthcare_queries = [
            "I have a headache, what should I do?",
            "What are the symptoms of diabetes?",
            "My blood pressure is high, should I see a doctor?",
            "I'm experiencing chest pain",
            "What medications help with anxiety?"
        ]
        
        for query in healthcare_queries:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare advice for: {query}"
                
                response = self.client.post(
                    "/api/chat",
                    json={"message": query, "token": self.valid_token}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "reply" in data
                assert data["reply"] != REFUSAL_MESSAGE
                assert "Healthcare advice for:" in data["reply"]
                mock_openai.assert_called_once_with(query)
    
    def test_non_healthcare_query_rejection_flow(self):
        """Test complete flow for non-healthcare queries."""
        non_healthcare_queries = [
            "What's the weather today?",
            "How do I cook pasta?",
            "Tell me a joke",
            "What's the capital of France?",
            "How to fix my car?"
        ]
        
        for query in non_healthcare_queries:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                response = self.client.post(
                    "/api/chat",
                    json={"message": query, "token": self.valid_token}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "reply" in data
                assert data["reply"] == REFUSAL_MESSAGE
                # OpenAI should not be called for non-healthcare queries
                mock_openai.assert_not_called()
    
    def test_mixed_content_query_processing(self):
        """Test queries that mix healthcare and non-healthcare content."""
        mixed_queries = [
            "I have a headache, also what's the weather?",
            "After seeing the doctor, I want to watch a movie",
            "My symptoms include fever, and I'm also hungry for pizza"
        ]
        
        for query in mixed_queries:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare response for: {query}"
                
                response = self.client.post(
                    "/api/chat",
                    json={"message": query, "token": self.valid_token}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "reply" in data
                # Mixed content with healthcare keywords should be processed
                assert data["reply"] != REFUSAL_MESSAGE
                mock_openai.assert_called_once_with(query)
    
    def test_openai_api_fallback_flow(self):
        """Test fallback mechanism when OpenAI API is unavailable."""
        healthcare_query = "I have a fever, what should I do?"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None  # Simulate API failure
            
            response = self.client.post(
                "/api/chat",
                json={"message": healthcare_query, "token": self.valid_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert data["reply"] != REFUSAL_MESSAGE
            assert "limited mode" in data["reply"] or "consult" in data["reply"]
            mock_openai.assert_called_once_with(healthcare_query)
    
    def test_secondary_filtering_validation(self):
        """Test secondary filtering of AI responses."""
        healthcare_query = "What are diabetes symptoms?"
        
        # Test case where AI tries to refuse healthcare query
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Sorry, I can only assist with healthcare-related queries."
            
            response = self.client.post(
                "/api/chat",
                json={"message": healthcare_query, "token": self.valid_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["reply"] == REFUSAL_MESSAGE
    
    @patch('app.main.log_chat_interaction', new_callable=AsyncMock)
    def test_chat_logging_integration(self, mock_log):
        """Test that chat interactions are properly logged."""
        healthcare_query = "I have a headache"
        expected_response = "Healthcare advice for headache"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = expected_response
            
            response = self.client.post(
                "/api/chat",
                json={"message": healthcare_query, "token": self.valid_token}
            )
            
            assert response.status_code == 200
            # Verify logging was called with correct parameters
            mock_log.assert_called_once_with(healthcare_query, expected_response)
    
    @patch('app.main.log_chat_interaction', new_callable=AsyncMock)
    def test_refusal_logging_integration(self, mock_log):
        """Test that refusal responses are properly logged."""
        non_healthcare_query = "What's the weather?"
        
        response = self.client.post(
            "/api/chat",
            json={"message": non_healthcare_query, "token": self.valid_token}
        )
        
        assert response.status_code == 200
        # Verify logging was called with refusal message
        mock_log.assert_called_once_with(non_healthcare_query, REFUSAL_MESSAGE)


class TestValidateAiResponse:
    """Test cases for AI response validation function."""
    
    def test_valid_healthcare_response_passes(self):
        """Test that valid healthcare responses pass validation."""
        valid_responses = [
            "Headaches can be caused by various factors including stress, dehydration, or tension.",
            "Diabetes symptoms include increased thirst, frequent urination, and fatigue.",
            "For chest pain, it's important to seek immediate medical attention.",
            "Regular exercise and a balanced diet can help manage blood pressure.",
            "Anxiety can be managed through therapy, medication, and lifestyle changes."
        ]
        
        for response in valid_responses:
            validated = validate_ai_response(response)
            assert validated == response, f"Valid response should pass: {response}"
    
    def test_ai_refusal_responses_converted(self):
        """Test that AI refusal responses are converted to standard refusal."""
        ai_refusal_responses = [
            "Sorry, I can only assist with healthcare-related queries.",
            "I can only help with healthcare topics.",
            "I'm designed to assist with healthcare matters only.",
            "Please ask me about health-related topics."
        ]
        
        for response in ai_refusal_responses:
            validated = validate_ai_response(response)
            assert validated == REFUSAL_MESSAGE, f"AI refusal should be standardized: {response}"
    
    def test_non_healthcare_indicators_rejected(self):
        """Test that responses indicating non-healthcare topics are rejected."""
        non_healthcare_responses = [
            "I don't have information about cooking recipes.",
            "I can't help with weather forecasts.",
            "I can't help with entertainment recommendations.",
            "That's not related to healthcare, so I can't assist.",
            "That's outside my healthcare expertise."
        ]
        
        for response in non_healthcare_responses:
            validated = validate_ai_response(response)
            assert validated == REFUSAL_MESSAGE, f"Non-healthcare response should be rejected: {response}"
    
    def test_edge_cases(self):
        """Test edge cases for AI response validation."""
        # Empty response
        assert validate_ai_response("") == REFUSAL_MESSAGE
        
        # None response
        assert validate_ai_response(None) == REFUSAL_MESSAGE
        
        # Non-string response
        assert validate_ai_response(123) == REFUSAL_MESSAGE
        assert validate_ai_response([]) == REFUSAL_MESSAGE


class TestOpenAiIntegration:
    """Test cases for OpenAI API integration with filtering."""
    
    @pytest.mark.asyncio
    async def test_openai_api_with_system_prompt(self):
        """Test that OpenAI API calls include the healthcare system prompt."""
        user_message = "I have a headache"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Healthcare advice for headache"}}]
            }
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Mock environment variable
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
                result = await call_openai_api(user_message)
                
                assert result == "Healthcare advice for headache"
                
                # Verify the API call was made with correct parameters
                call_args = mock_client.return_value.__aenter__.return_value.post.call_args
                assert call_args is not None
                
                # Check that system prompt was included
                payload = call_args[1]['json']
                assert len(payload['messages']) == 2
                assert payload['messages'][0]['role'] == 'system'
                assert payload['messages'][1]['role'] == 'user'
                assert payload['messages'][1]['content'] == user_message
    
    @pytest.mark.asyncio
    async def test_openai_api_error_handling(self):
        """Test OpenAI API error handling."""
        user_message = "I have a headache"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate API error
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=Exception("API Error"))
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
                result = await call_openai_api(user_message)
                
                assert result is None


class TestFallbackResponses:
    """Test cases for fallback response system."""
    
    def test_symptom_related_fallback(self):
        """Test fallback responses for symptom-related queries."""
        symptom_queries = [
            "I have symptoms of flu",
            "I'm feeling pain in my chest",
            "My head aches constantly"
        ]
        
        for query in symptom_queries:
            response = get_fallback_response(query)
            assert "limited mode" in response
            assert "healthcare professional" in response
            assert response != REFUSAL_MESSAGE
    
    def test_medication_related_fallback(self):
        """Test fallback responses for medication-related queries."""
        medication_queries = [
            "What medication should I take?",
            "Tell me about this prescription drug",
            "Are there side effects to this medicine?"
        ]
        
        for query in medication_queries:
            response = get_fallback_response(query)
            assert "limited mode" in response
            assert "doctor or pharmacist" in response
            assert response != REFUSAL_MESSAGE
    
    def test_emergency_related_fallback(self):
        """Test fallback responses for emergency-related queries."""
        emergency_queries = [
            "This is an emergency!",
            "I need urgent medical help",
            "Should I call 911?"
        ]
        
        for query in emergency_queries:
            response = get_fallback_response(query)
            assert "911" in response or "emergency" in response
            assert response != REFUSAL_MESSAGE
    
    def test_general_healthcare_fallback(self):
        """Test fallback responses for general healthcare queries."""
        general_query = "I have a general health question"
        response = get_fallback_response(general_query)
        
        assert "limited mode" in response
        assert "healthcare professional" in response
        assert response != REFUSAL_MESSAGE


class TestEndToEndScenarios:
    """End-to-end test scenarios for complete filtering integration."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.valid_token = "test_token_456"
        
        from app.main import active_tokens
        active_tokens.add(self.valid_token)
    
    def teardown_method(self):
        """Clean up after tests."""
        from app.main import active_tokens
        active_tokens.clear()
    
    def test_complete_healthcare_journey(self):
        """Test complete user journey with healthcare queries."""
        test_scenarios = [
            {
                "query": "I've been having headaches for a week",
                "should_reach_ai": True,
                "expected_not_refusal": True
            },
            {
                "query": "What's the weather like?",
                "should_reach_ai": False,
                "expected_not_refusal": False
            },
            {
                "query": "My doctor said I have high blood pressure",
                "should_reach_ai": True,
                "expected_not_refusal": True
            },
            {
                "query": "How do I cook pasta?",
                "should_reach_ai": False,
                "expected_not_refusal": False
            }
        ]
        
        for scenario in test_scenarios:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                if scenario["should_reach_ai"]:
                    mock_openai.return_value = f"Healthcare response for: {scenario['query']}"
                
                response = self.client.post(
                    "/api/chat",
                    json={"message": scenario["query"], "token": self.valid_token}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                if scenario["expected_not_refusal"]:
                    assert data["reply"] != REFUSAL_MESSAGE
                else:
                    assert data["reply"] == REFUSAL_MESSAGE
                
                if scenario["should_reach_ai"]:
                    mock_openai.assert_called_once()
                else:
                    mock_openai.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])