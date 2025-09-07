import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, mock_open
from fastapi import HTTPException
import asyncio

from process_proxy.mobbin.login import load_cookies, login
from process_proxy.mobbin.captcha import solve_captcha
from process_proxy.mobbin.sse_decoder import parse_sse_response


class TestLoadCookies:
    @pytest.mark.asyncio
    async def test_load_cookies_success(self):
        mock_cookies = [{"name": "test_cookie", "value": "test_value"}]
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_cookies))):
            result = await load_cookies()
            
        assert result == mock_cookies

    @pytest.mark.asyncio
    async def test_load_cookies_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                await load_cookies()

    @pytest.mark.asyncio
    async def test_load_cookies_invalid_json(self):
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with pytest.raises(json.JSONDecodeError):
                await load_cookies()


class TestLogin:
    @pytest.fixture
    def mock_session(self):
        mock_session = AsyncMock()
        mock_response = Mock()
        mock_response.text = ""
        mock_response.cookies = {"test_cookie": "test_value"}
        mock_session.post.return_value = mock_response
        return mock_session

    @pytest.mark.asyncio
    async def test_login_success_no_captcha(self, mock_session):
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class:
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await login()
            
            assert result == {"test_cookie": "test_value"}
            assert mock_session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_login_with_captcha_challenge(self, mock_session):
        captcha_response = Mock()
        captcha_response.text = "1:{\"rateLimited\":{\"challenge\":\"test_challenge\"}}"
        
        final_response = Mock()
        final_response.text = ""
        final_response.cookies = {"test_cookie": "test_value"}
        
        mock_session.post.side_effect = [captcha_response, final_response]
        
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class, \
             patch("src.process_proxy.mobbin.login.solve_captcha", return_value="test_token"), \
             patch("src.process_proxy.mobbin.login.json.dumps", return_value="test_payload"):
            
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await login()
            
            assert result == {"test_cookie": "test_value"}
            assert mock_session.post.call_count == 3

    @pytest.mark.asyncio
    async def test_login_lock_mechanism(self):
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            first_result = await login()
            second_result = await login()
            
            assert first_result == {}
            assert second_result == {}

    @pytest.mark.asyncio
    async def test_login_captcha_solve_failure(self, mock_session):
        captcha_response = Mock()
        captcha_response.text = "1:{\"rateLimited\":{\"challenge\":\"test_challenge\"}}"
        
        final_response = Mock()
        final_response.text = ""
        final_response.cookies = {"test_cookie": "test_value"}
        
        mock_session.post.side_effect = [captcha_response, final_response]
        
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class, \
             patch("src.process_proxy.mobbin.login.solve_captcha", return_value=""), \
             patch("src.process_proxy.mobbin.login.json.dumps", return_value="test_payload"):
            
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await login()
            
            assert result == {"test_cookie": "test_value"}

    @pytest.mark.asyncio
    async def test_login_captcha_submit_success(self, mock_session):
        captcha_response = Mock()
        captcha_response.text = "1:{\"rateLimited\":{\"challenge\":\"test_challenge\"}}"
        
        submit_response = Mock()
        submit_response.status_code = 303
        
        final_response = Mock()
        final_response.text = ""
        final_response.cookies = {"test_cookie": "test_value"}
        
        mock_session.post.side_effect = [captcha_response, submit_response, final_response]
        
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class, \
             patch("src.process_proxy.mobbin.login.solve_captcha", return_value="test_token"), \
             patch("src.process_proxy.mobbin.login.json.dumps", return_value="test_payload"):
            
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await login()
            
            assert result == {"test_cookie": "test_value"}

    @pytest.mark.asyncio
    async def test_login_captcha_submit_failure(self, mock_session):
        captcha_response = Mock()
        captcha_response.text = "1:{\"rateLimited\":{\"challenge\":\"test_challenge\"}}"
        
        submit_response = Mock()
        submit_response.status_code = 200
        
        final_response = Mock()
        final_response.text = ""
        final_response.cookies = {"test_cookie": "test_value"}
        
        mock_session.post.side_effect = [captcha_response, submit_response, final_response]
        
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class, \
             patch("src.process_proxy.mobbin.login.solve_captcha", return_value="test_token"), \
             patch("src.process_proxy.mobbin.login.json.dumps", return_value="test_payload"):
            
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await login()
            
            assert result == {"test_cookie": "test_value"}

    @pytest.mark.asyncio
    async def test_login_file_write_success(self, mock_session):
        mock_response = Mock()
        mock_response.text = ""
        mock_response.cookies = {"test_cookie": "test_value"}
        mock_session.post.return_value = mock_response
        
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class, \
             patch("builtins.open", mock_open()) as mock_file:
            
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await login()
            
            mock_file.assert_called_once_with("keys/mobbin_cookies.json", "w")
            mock_file().write.assert_called_once()


class TestCaptchaIntegration:
    @pytest.mark.asyncio
    async def test_solve_captcha_success(self):
        with patch("src.process_proxy.mobbin.captcha.TwoCaptcha") as mock_solver_class:
            mock_solver = Mock()
            mock_solver.turnstile.return_value = {"code": "test_token"}
            mock_solver_class.return_value = mock_solver
            
            result = await solve_captcha("test_key", "test_url")
            
            assert result == "test_token"
            mock_solver.turnstile.assert_called_once_with(
                sitekey='0x4AAAAAABQ3CCKaTml7wReF',
                url='test_url'
            )

    @pytest.mark.asyncio
    async def test_solve_captcha_exception(self):
        with patch("src.process_proxy.mobbin.captcha.TwoCaptcha") as mock_solver_class, \
             patch("src.process_proxy.mobbin.captcha.logging.error") as mock_logging:
            
            mock_solver = Mock()
            mock_solver.turnstile.side_effect = Exception("Test error")
            mock_solver_class.return_value = mock_solver
            
            result = await solve_captcha("test_key", "test_url")
            
            assert result == ""
            mock_logging.assert_called_once()


class TestSSEDecoderIntegration:
    def test_parse_sse_response_valid(self):
        response_text = "1:{\"rateLimited\":{\"challenge\":\"test_challenge\"}}\n2:{\"data\":\"test_data\"}"
        
        result = parse_sse_response(response_text)
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["data"]["rateLimited"]["challenge"] == "test_challenge"
        assert result[1]["id"] == 2
        assert result[1]["data"]["data"] == "test_data"

    def test_parse_sse_response_empty(self):
        result = parse_sse_response("")
        assert result == []

    def test_parse_sse_response_invalid_json(self):
        response_text = "1:invalid json\n2:{\"valid\":\"json\"}"
        
        result = parse_sse_response(response_text)
        
        assert len(result) == 1
        assert result[0]["id"] == 2
        assert result[0]["data"]["valid"] == "json"

    def test_parse_sse_response_mixed_content(self):
        response_text = "1:{\"test\":\"data\"}\n\n2:{\"another\":\"test\"}\ninvalid_line"
        
        result = parse_sse_response(response_text)
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2


class TestIntegrationScenarios:
    @pytest.mark.asyncio
    async def test_full_login_flow_with_captcha(self):
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class, \
             patch("src.process_proxy.mobbin.login.solve_captcha", return_value="test_token"), \
             patch("src.process_proxy.mobbin.login.json.dumps", return_value="test_payload"), \
             patch("builtins.open", mock_open()):
            
            mock_session = AsyncMock()
            captcha_response = Mock()
            captcha_response.text = "1:{\"rateLimited\":{\"challenge\":\"test_challenge\"}}"
            
            submit_response = Mock()
            submit_response.status_code = 303
            
            final_response = Mock()
            final_response.text = ""
            final_response.cookies = {"session": "test_session", "auth": "test_auth"}
            
            mock_session.post.side_effect = [captcha_response, submit_response, final_response]
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await login()
            
            assert result == {"session": "test_session", "auth": "test_auth"}
            assert mock_session.post.call_count == 3

    @pytest.mark.asyncio
    async def test_login_flow_without_captcha(self):
        with patch("src.process_proxy.mobbin.login.requests.AsyncSession") as mock_session_class, \
             patch("builtins.open", mock_open()):
            
            mock_session = AsyncMock()
            mock_response = Mock()
            mock_response.text = ""
            mock_response.cookies = {"session": "test_session"}
            mock_session.post.return_value = mock_response
            
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await login()
            
            assert result == {"session": "test_session"}
            assert mock_session.post.call_count == 2
