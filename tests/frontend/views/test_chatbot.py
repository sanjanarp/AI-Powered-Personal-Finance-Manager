import unittest
from unittest.mock import patch, MagicMock
from frontend.views.Chatbot import show_chatbot

class TestChatbotUI(unittest.TestCase):

    def test_chat_flow_rag(self):
        """Test the RAG-powered chat flow."""
        mock_st = MagicMock()
        mock_config = MagicMock()
        mock_chat_rag = MagicMock(return_value=("Mocked RAG response", [], "retrieved context"))
        mock_ingest = MagicMock()
        mock_vector_store_class = MagicMock()
        mock_vector_store = MagicMock()
        mock_vector_store.count.return_value = 42
        mock_vector_store_class.return_value = mock_vector_store

        mock_session = MagicMock()
        mock_session.transactions = [{"amount": 100}]
        mock_session.chat_started = False
        mock_session.conversation_history = []
        mock_session.retrieved_contexts = []

        mock_session.__getitem__.side_effect = lambda key: getattr(mock_session, key)
        mock_session.__setitem__.side_effect = lambda key, value: setattr(mock_session, key, value)
        mock_session.__contains__.side_effect = lambda key: hasattr(mock_session, key)
        mock_session.get = MagicMock(side_effect=lambda key, default=None: getattr(mock_session, key, default))

        mock_st.session_state = mock_session
        mock_st.button.return_value = True
        mock_st.spinner.return_value.__enter__.return_value = None
        mock_st.spinner.return_value.__exit__.return_value = None
        mock_st.rerun = MagicMock()
        mock_st.chat_input.return_value = None

        with patch("frontend.views.Chatbot.st", mock_st), \
            patch("frontend.views.Chatbot.Config", mock_config), \
            patch("frontend.views.Chatbot.FinanceVectorStore", mock_vector_store_class), \
            patch("frontend.views.Chatbot.ingest_all", mock_ingest), \
            patch.dict(show_chatbot.__globals__, {"chat_with_advisor_rag": mock_chat_rag}):

            mock_config.get_openai_api_key.return_value = "fake-key"
            show_chatbot()

        mock_ingest.assert_called_once()
        mock_chat_rag.assert_called_once()
        mock_st.rerun.assert_called_once()

    def test_no_api_key(self):
        mock_st = MagicMock()
        mock_config = MagicMock()
        mock_config.get_openai_api_key.side_effect = ValueError("Missing key")

        mock_session = MagicMock()
        mock_session.transactions = [{"amount": 50}]
        mock_session.chat_started = False

        mock_session.__getitem__.side_effect = lambda key: getattr(mock_session, key)
        mock_session.__setitem__.side_effect = lambda key, value: setattr(mock_session, key, value)
        mock_session.__contains__.side_effect = lambda key: hasattr(mock_session, key)

        mock_st.session_state = mock_session
        mock_st.button.return_value = True
        mock_st.spinner.return_value.__enter__.return_value = None
        mock_st.spinner.return_value.__exit__.return_value = None
        mock_st.error = MagicMock()

        with patch("frontend.views.Chatbot.st", mock_st), \
             patch("frontend.views.Chatbot.Config", mock_config):

            show_chatbot()

        mock_st.error.assert_called_with("⚠️ OpenAI API key not configured. Please add it to your .env file.")

    def test_no_transactions(self):
        """Test that a warning is shown when no transactions exist."""
        mock_st = MagicMock()

        mock_session = MagicMock()
        mock_session.chat_started = False
        mock_session.conversation_history = []
        mock_session.retrieved_contexts = []

        mock_session.__getitem__.side_effect = lambda key: getattr(mock_session, key)
        mock_session.__setitem__.side_effect = lambda key, value: setattr(mock_session, key, value)
        mock_session.__contains__.side_effect = lambda key: key in ['conversation_history', 'chat_started', 'retrieved_contexts']

        mock_st.session_state = mock_session

        with patch("frontend.views.Chatbot.st", mock_st):
            show_chatbot()

        mock_st.warning.assert_called_with("⚠️ Please fetch transactions from the Home page first.")

    def test_followup_uses_rag(self):
        """Test that follow-up questions use RAG retrieval."""
        mock_st = MagicMock()
        mock_config = MagicMock()
        mock_config.get_openai_api_key.return_value = "fake-key"
        mock_chat_rag = MagicMock(return_value=("Follow-up response", [{"role": "assistant", "content": "hi"}], "follow-up context"))

        mock_vector_store = MagicMock()

        mock_session = MagicMock()
        mock_session.transactions = [{"amount": 100}]
        mock_session.chat_started = True
        mock_session.conversation_history = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "initial question"},
            {"role": "assistant", "content": "initial response"},
        ]
        mock_session.retrieved_contexts = ["initial context"]
        mock_session.vector_store = mock_vector_store
        mock_session.rag_doc_count = 42

        mock_session.__getitem__.side_effect = lambda key: getattr(mock_session, key)
        mock_session.__setitem__.side_effect = lambda key, value: setattr(mock_session, key, value)
        mock_session.__contains__.side_effect = lambda key: hasattr(mock_session, key)
        mock_session.get = MagicMock(side_effect=lambda key, default=None: getattr(mock_session, key, default))

        mock_st.session_state = mock_session
        mock_st.chat_input.return_value = "follow-up question"
        mock_st.chat_message.return_value.__enter__.return_value = None
        mock_st.chat_message.return_value.__exit__.return_value = None
        mock_st.expander.return_value.__enter__.return_value = MagicMock()
        mock_st.expander.return_value.__exit__.return_value = None
        mock_st.spinner.return_value.__enter__.return_value = None
        mock_st.spinner.return_value.__exit__.return_value = None
        mock_st.button.return_value = False

        with patch("frontend.views.Chatbot.st", mock_st), \
             patch("frontend.views.Chatbot.Config", mock_config), \
             patch.dict(show_chatbot.__globals__, {"chat_with_advisor_rag": mock_chat_rag}):

            show_chatbot()

        mock_chat_rag.assert_called_once()
        # Verify it was called with the follow-up question
        call_kwargs = mock_chat_rag.call_args
        self.assertIn("follow-up question", str(call_kwargs))

if __name__ == "__main__":
    unittest.main()
