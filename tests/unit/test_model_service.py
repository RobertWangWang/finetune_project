from unittest import TestCase

from app.services.common_services.model_service import chat_with_error_handling


class Test(TestCase):
    def test_chat_with_error_handling(self):
        resp, err = chat_with_error_handling("你好")
        if err is not None:
            print(err)
        else:
            print(resp)
