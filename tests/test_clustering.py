"""
Tests for Smart Clustering functionality
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock

from app.services.llm_svc import LLMService
from app.domain.models import SignalCard


@pytest.mark.asyncio
async def test_cluster_signals_with_valid_data():
    """Test clustering with valid signal data"""
    # Mock settings
    mock_settings = Mock()
    mock_settings.OPENAI_API_KEY = "test-key"
    mock_settings.CHAT_MODEL = "gpt-4o-mini"
    
    # Create service
    service = LLMService(settings=mock_settings)
    
    # Mock OpenAI client
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '''
    {
        "themes": [
            {
                "name": "Climate Tech",
                "description": "Technologies for climate change mitigation",
                "signal_ids": [0, 1],
                "relevance_score": 8.5
            },
            {
                "name": "AI Policy",
                "description": "Regulatory frameworks for artificial intelligence",
                "signal_ids": [2, 3],
                "relevance_score": 7.8
            }
        ]
    }
    '''
    
    service.client = Mock()
    service.client.chat = Mock()
    service.client.chat.completions = Mock()
    service.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Test data
    signals = [
        {"title": "Carbon Capture", "summary": "New carbon capture technology"},
        {"title": "Solar Panels", "summary": "Efficient solar panel design"},
        {"title": "AI Regulation", "summary": "New AI safety regulations"},
        {"title": "ML Ethics", "summary": "Machine learning ethical guidelines"}
    ]
    
    # Call clustering
    result = await service.cluster_signals(signals)
    
    # Assertions
    assert "themes" in result
    assert len(result["themes"]) == 2
    assert result["themes"][0]["name"] == "Climate Tech"
    assert result["themes"][0]["signal_ids"] == [0, 1]
    assert result["themes"][1]["name"] == "AI Policy"


@pytest.mark.asyncio
async def test_cluster_signals_no_api_key():
    """Test clustering without OpenAI API key"""
    mock_settings = Mock()
    mock_settings.OPENAI_API_KEY = None
    
    service = LLMService(settings=mock_settings)
    
    signals = [
        {"title": "Test", "summary": "Test signal"}
    ]
    
    result = await service.cluster_signals(signals)
    
    # Should return empty themes
    assert result == {"themes": []}


@pytest.mark.asyncio
async def test_cluster_signals_empty_list():
    """Test clustering with empty signal list"""
    mock_settings = Mock()
    mock_settings.OPENAI_API_KEY = "test-key"
    mock_settings.CHAT_MODEL = "gpt-4o-mini"
    
    service = LLMService(settings=mock_settings)
    
    result = await service.cluster_signals([])
    
    assert result == {"themes": []}


@pytest.mark.asyncio
async def test_cluster_signals_with_signal_card_objects():
    """Test clustering with SignalCard objects"""
    mock_settings = Mock()
    mock_settings.OPENAI_API_KEY = "test-key"
    mock_settings.CHAT_MODEL = "gpt-4o-mini"
    
    service = LLMService(settings=mock_settings)
    
    # Mock response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"themes": [{"name": "Test", "description": "Test", "signal_ids": [0], "relevance_score": 8.0}]}'
    
    service.client = Mock()
    service.client.chat = Mock()
    service.client.chat.completions = Mock()
    service.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Create SignalCard objects
    signals = [
        SignalCard(
            title="Test Signal",
            url="http://test.com",
            summary="Test summary",
            source="Test",
            mission="General",
            date="2024-01-01",
            score_activity=5.0,
            score_attention=6.0,
            score_recency=7.0,
            final_score=8.0,
            typology="Nascent"
        )
    ]
    
    result = await service.cluster_signals(signals)
    
    assert "themes" in result
    assert len(result["themes"]) > 0


@pytest.mark.asyncio
async def test_cluster_signals_api_error():
    """Test clustering when API call fails"""
    mock_settings = Mock()
    mock_settings.OPENAI_API_KEY = "test-key"
    mock_settings.CHAT_MODEL = "gpt-4o-mini"
    
    service = LLMService(settings=mock_settings)
    
    # Mock API error
    service.client = Mock()
    service.client.chat = Mock()
    service.client.chat.completions = Mock()
    service.client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
    
    signals = [{"title": "Test", "summary": "Test"}]
    
    result = await service.cluster_signals(signals)
    
    # Should return empty themes on error
    assert result == {"themes": []}


@pytest.mark.asyncio
async def test_cluster_signals_invalid_json_response():
    """Test clustering with invalid JSON response"""
    mock_settings = Mock()
    mock_settings.OPENAI_API_KEY = "test-key"
    mock_settings.CHAT_MODEL = "gpt-4o-mini"
    
    service = LLMService(settings=mock_settings)
    
    # Mock invalid response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Not valid JSON"
    
    service.client = Mock()
    service.client.chat = Mock()
    service.client.chat.completions = Mock()
    service.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    signals = [{"title": "Test", "summary": "Test"}]
    
    result = await service.cluster_signals(signals)
    
    # Should return empty themes on parse error
    assert result == {"themes": []}
