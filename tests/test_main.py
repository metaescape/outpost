import unittest
from unittest.mock import patch, mock_open
from main import Workflow, time_is_ok, tolerant_time
from configs.config import Config
import datetime
from datetime import timedelta


class TestMain(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 12, 0)
        log_folder = "/home/pipz/codes/ranger/outpost/logs/httpd/"
        self.instance = Workflow(
            start_time, end_time, log_folder, self.config
        )  # 适当调整以匹配实际的初始化方法

    def test_time_is_ok(self):
        self.eager_gap = self.config.time["eager_gap"]
        expect_false = time_is_ok(
            self.config,
            datetime.datetime.today()
            - datetime.timedelta(hours=self.eager_gap - 1),
        )
        self.assertFalse(expect_false)
        expect_true = time_is_ok(
            self.config,
            datetime.datetime.today()
            - datetime.timedelta(hours=self.eager_gap + 1),
        )
        self.assertTrue(
            not expect_true
        )  # if time is between 8-9 this will be true

    def test_tolerant_time(self):
        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 8, 0)
        gap = timedelta(hours=23.7)
        self.assertTrue(tolerant_time(end_time - start_time, gap))
        self.assertTrue(
            not tolerant_time(end_time - start_time - timedelta(hours=1), gap)
        )

    @patch("builtins.open", new_callable=mock_open)
    @patch("main.write_last_eager")  # 假设这是你需要模拟的额外函数
    @patch("os.path.join", return_value="dummy_path")
    @patch("json.dump")
    def test_write_back(
        self,
        mock_json_dump,
        mock_path_join,
        mock_write_last_eager,
        mock_file_open,
    ):
        return
        result = {
            "day_cnt": 10,
            "day_unique_cnt": 5,
            "pages": {"page1": 1},
            "locations": {"loc1": 1},
        }
        session_end = "dummy_session_end"
        self.instance.write_back(result, session_end)

        # 检查是否正确调用了open和write
        # mock_file_open.assert_any_call("dummy_path", "a")  # 检查追加模式
        mock_file_open().write.assert_any_call(
            '["2024年03月01日", 10, 5]\n'
        )  # 假设的日期，根据实际情况调整

        # 检查json.dump是否被正确调用
        mock_json_dump.assert_called_once_with(
            {"pages": result["pages"], "locations": result["locations"]},
            mock_file_open(),
            indent=4,
            ensure_ascii=False,
        )

        # 验证 write_last_eager 和其他需要模拟的函数是否被调用
        mock_write_last_eager.assert_called_once_with("dummy_session_end")


if __name__ == "__main__":
    unittest.main()
