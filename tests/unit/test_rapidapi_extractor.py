"""
Unit tests for RapidAPI LinkedIn Extractor
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'app_production'))

from agents.extract_agent.rapidapi_linkedin_extractor import RapidAPILinkedInExtractor


class TestRapidAPILinkedInExtractor:
    """Test suite for RapidAPI LinkedIn Extractor"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance with mock API key"""
        with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test_key_123'}):
            return RapidAPILinkedInExtractor()

    @pytest.fixture
    def mock_api_response(self):
        """Mock successful API response"""
        return {
            'success': True,
            'data': [
                {
                    'id': '123456',
                    'title': 'Senior Data Engineer',
                    'company': {'name': 'Tech Corp', 'id': '789', 'url': 'https://linkedin.com/company/tech-corp'},
                    'location': 'São Paulo, Brazil',
                    'url': 'https://linkedin.com/jobs/view/123456',
                    'listed_at': '2025-10-06'
                },
                {
                    'id': '789012',
                    'title': 'Data Analyst',
                    'company': {'name': 'Data Inc'},
                    'location': 'Rio de Janeiro, RJ (remote)',
                    'url': 'https://linkedin.com/jobs/view/789012',
                    'listed_at': '2025-10-05'
                }
            ]
        }

    def test_initialization(self, extractor):
        """Test extractor initialization"""
        assert extractor.api_key == 'test_key_123'
        assert extractor.max_requests == 100
        assert extractor.request_count == 0

    def test_initialization_without_api_key(self):
        """Test that initialization fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="RAPIDAPI_KEY não encontrada"):
                RapidAPILinkedInExtractor()

    @patch('requests.get')
    def test_search_jobs_success(self, mock_get, extractor, mock_api_response):
        """Test successful job search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_get.return_value = mock_response

        jobs = extractor.search_jobs(keyword='Data Engineer', location='Brazil')

        assert len(jobs) == 2
        assert jobs[0]['job_title'] == 'Senior Data Engineer'
        assert jobs[0]['company_name'] == 'Tech Corp'
        assert jobs[1]['work_modality'] == 'remote'
        assert extractor.request_count == 1

    @patch('requests.get')
    def test_search_jobs_rate_limit(self, mock_get, extractor):
        """Test rate limit handling"""
        extractor.request_count = 100  # Max requests reached

        jobs = extractor.search_jobs(keyword='Data Engineer')

        assert len(jobs) == 0
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_search_jobs_api_error(self, mock_get, extractor):
        """Test API error handling"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        jobs = extractor.search_jobs(keyword='Data Engineer')

        assert len(jobs) == 0
        assert extractor.request_count == 1

    @patch('requests.get')
    def test_search_jobs_429_rate_limit(self, mock_get, extractor):
        """Test 429 rate limit response"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        jobs = extractor.search_jobs(keyword='Data Engineer')

        assert len(jobs) == 0

    def test_normalize_jobs_with_remote_location(self, extractor):
        """Test work_modality inference from location"""
        jobs = [
            {
                'id': '123',
                'title': 'Remote Engineer',
                'company': {'name': 'Company A'},
                'location': 'São Paulo, Brazil (remote)',
                'url': 'https://test.com',
                'listed_at': '2025-10-06'
            }
        ]

        normalized = extractor._normalize_jobs(jobs, 'test')

        assert len(normalized) == 1
        assert normalized[0]['work_modality'] == 'remote'

    def test_normalize_jobs_with_hybrid_location(self, extractor):
        """Test work_modality inference for hybrid"""
        jobs = [
            {
                'id': '456',
                'title': 'Hybrid Engineer',
                'company': {'name': 'Company B'},
                'location': 'Rio de Janeiro (hybrid)',
                'url': 'https://test.com',
                'listed_at': '2025-10-06'
            }
        ]

        normalized = extractor._normalize_jobs(jobs, 'test')

        assert normalized[0]['work_modality'] == 'hybrid'

    def test_normalize_jobs_posted_time_ts_conversion(self, extractor):
        """Test posted_time_ts conversion to ISO format and recent posting flag"""
        from datetime import datetime, timedelta
        # Use data recente (< 7 dias) para garantir is_recent_posting = True
        recent_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        jobs = [
            {
                'id': '789',
                'title': 'Recent Job',
                'company': {'name': 'Company C'},
                'location': 'Remote',
                'url': 'https://test.com',
                'listed_at': recent_date
            }
        ]

        normalized = extractor._normalize_jobs(jobs, 'test')

        assert normalized[0]['posted_time_ts'] is not None
        # posted_time_ts now returns ISO format string (JSON serializable)
        assert isinstance(normalized[0]['posted_time_ts'], str)
        # Validate it's a valid ISO format
        from dateutil import parser
        parsed_date = parser.parse(normalized[0]['posted_time_ts'])
        assert parsed_date is not None
        assert normalized[0]['is_recent_posting'] is True

    def test_normalize_jobs_location_parsing(self, extractor):
        """Test location parsing into city, state, country"""
        jobs = [
            {
                'id': '999',
                'title': 'Test Job',
                'company': {'name': 'Company D'},
                'location': 'São Paulo, SP, Brazil',
                'url': 'https://test.com',
                'listed_at': '2025-10-06'
            }
        ]

        normalized = extractor._normalize_jobs(jobs, 'test')

        assert normalized[0]['city'] == 'São Paulo'
        assert normalized[0]['state'] == 'SP'
        assert normalized[0]['country'] == 'Brazil'

    def test_normalize_jobs_missing_fields(self, extractor):
        """Test handling of missing fields"""
        jobs = [
            {
                'id': '111',
                'title': '',  # Empty title
                'company': {},  # Empty company
                'location': '',
                'url': 'https://test.com',
                'listed_at': ''
            }
        ]

        normalized = extractor._normalize_jobs(jobs, 'test')

        # Should still normalize but with empty/None values
        assert len(normalized) == 1
        assert normalized[0]['job_title'] == ''
        assert normalized[0]['company_name'] == ''

    def test_get_usage_stats(self, extractor):
        """Test usage statistics"""
        extractor.request_count = 25

        stats = extractor.get_usage_stats()

        assert stats['requests_used'] == 25
        assert stats['requests_remaining'] == 75
        assert stats['limit'] == 100
        assert stats['usage_percentage'] == 25.0

    @patch('requests.get')
    def test_search_jobs_with_geo_id_filter(self, mock_get, extractor, mock_api_response):
        """Test that geo_id for Brazil is included in request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_get.return_value = mock_response

        extractor.search_jobs(keyword='Data Engineer', location='Brazil')

        # Verify geo_id was included in params
        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params['geo_id'] == '106057199'  # Brazil geocode

    def test_normalize_jobs_validation(self, extractor):
        """Test job validation - should accept jobs with title OR url"""
        jobs = [
            {
                'id': '1',
                'title': 'Valid Job',
                'company': {'name': 'Company'},
                'location': 'Brazil',
                'url': '',  # No URL but has title
                'listed_at': '2025-10-06'
            },
            {
                'id': '2',
                'title': '',  # No title but has URL
                'company': {'name': 'Company'},
                'location': 'Brazil',
                'url': 'https://test.com',
                'listed_at': '2025-10-06'
            },
            {
                'id': '3',
                'title': '',  # No title AND no URL - should be rejected
                'company': {'name': 'Company'},
                'location': 'Brazil',
                'url': '',
                'listed_at': '2025-10-06'
            }
        ]

        normalized = extractor._normalize_jobs(jobs, 'test')

        # Should accept first two, reject third
        assert len(normalized) == 2


@pytest.mark.integration
class TestRapidAPIIntegration:
    """Integration tests for RapidAPI (requires real API key)"""

    @pytest.mark.skip(reason="Requires real API key and consumes quota")
    def test_real_api_call(self):
        """Test real API call (skip by default to preserve quota)"""
        extractor = RapidAPILinkedInExtractor()
        jobs = extractor.search_jobs(keyword='Data Engineer', location='Brazil', limit=5)

        assert len(jobs) > 0
        assert all('job_id' in job for job in jobs)
        assert all('job_title' in job for job in jobs)
