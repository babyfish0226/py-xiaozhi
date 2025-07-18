import argparse
import asyncio
import sys
import time

from src.application import Application
from src.utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def parse_args():
    """
    解析命令行參數.
    """
    parser = argparse.ArgumentParser(description="小智Ai客戶端")
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="運行模式：gui(圖形界面) 或 cli(命令行)",
    )
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "websocket"],
        default="websocket",
        help="通信協議：mqtt 或 websocket",
    )
    parser.add_argument(
        "--skip-activation",
        action="store_true",
        help="跳過激活流程，直接啟動應用（僅用於調試）",
    )
    return parser.parse_args()


async def handle_activation(mode: str) -> bool:
    """處理設備激活流程.

    Args:
        mode: 運行模式，"gui"或"cli"

    Returns:
        bool: 激活是否成功
    """
    try:
        from src.core.system_initializer import SystemInitializer

        logger.info("開始設備激活流程檢查...")

        # 創建SystemInitializer實例
        system_initializer = SystemInitializer()

        # 運行初始化流程
        init_result = await system_initializer.run_initialization()

        # 檢查初始化是否成功
        if not init_result.get("success", False):
            logger.error(f"系統初始化失敗: {init_result.get('error', '未知錯誤')}")
            return False

        # 獲取激活版本
        activation_version = init_result.get("activation_version", "v1")
        logger.info(f"當前激活版本: {activation_version}")

        # 如果是v1協議，直接返回成功
        if activation_version == "v1":
            logger.info("v1協議：系統初始化完成，無需激活流程")
            return True

        # 如果是v2協議，檢查是否需要激活界面
        if not init_result.get("need_activation_ui", False):
            logger.info("v2協議：無需顯示激活界面，設備已激活")
            return True

        logger.info("v2協議：需要顯示激活界面，準備激活流程")

        # 需要激活界面，根據模式處理
        if mode == "gui":
            # GUI模式需要先創建QApplication
            try:
                # 導入必要的庫
                import qasync
                from PyQt5.QtCore import QTimer
                from PyQt5.QtWidgets import QApplication

                # 創建臨時QApplication實例
                logger.info("創建臨時QApplication實例用於激活流程")
                temp_app = QApplication(sys.argv)

                # 創建事件循環
                loop = qasync.QEventLoop(temp_app)
                asyncio.set_event_loop(loop)

                # 創建Future來等待激活完成（使用新的事件循環）
                activation_future = loop.create_future()

                # 創建激活窗口
                from src.views.activation.activation_window import ActivationWindow

                activation_window = ActivationWindow(system_initializer)

                # 設置激活完成回調
                def on_activation_completed(success: bool):
                    logger.info(f"激活完成，結果: {success}")
                    if not activation_future.done():
                        activation_future.set_result(success)

                # 設置窗口關閉回調
                def on_window_closed():
                    logger.info("激活窗口被關閉")
                    if not activation_future.done():
                        activation_future.set_result(False)

                # 連接信號
                activation_window.activation_completed.connect(on_activation_completed)
                activation_window.window_closed.connect(on_window_closed)

                # 顯示激活窗口
                activation_window.show()
                logger.info("激活窗口已顯示")

                # 確保窗口顯示出來
                QTimer.singleShot(100, lambda: logger.info("激活窗口顯示確認"))

                # 等待激活完成
                try:
                    logger.info("開始等待激活完成")
                    activation_success = loop.run_until_complete(activation_future)
                    logger.info(f"激活流程完成，結果: {activation_success}")
                except Exception as e:
                    logger.error(f"激活流程異常: {e}")
                    activation_success = False

                # 關閉窗口
                activation_window.close()

                # 銷毀臨時QApplication
                logger.info("激活流程完成，銷毀臨時QApplication實例")
                activation_window = None
                temp_app = None

                # 強制垃圾回收，確保QApplication被銷毀
                import gc

                gc.collect()

                # 等待一小段時間確保資源釋放（使用同步sleep）
                logger.info("等待資源釋放...")
                time.sleep(0.5)

                return activation_success

            except ImportError as e:
                logger.error(f"GUI模式需要qasync和PyQt5庫: {e}")
                return False
        else:
            # CLI模式
            from src.views.activation.cli_activation import CLIActivation

            cli_activation = CLIActivation(system_initializer)
            return await cli_activation.run_activation_process()

    except Exception as e:
        logger.error(f"激活流程異常: {e}", exc_info=True)
        return False


async def main():
    """
    主函數.
    """
    setup_logging()
    args = parse_args()

    logger.info("啟動小智AI客戶端")

    # 處理激活流程
    if not args.skip_activation:
        activation_success = await handle_activation(args.mode)
        if not activation_success:
            logger.error("設備激活失敗，程序退出")
            return 1
    else:
        logger.warning("跳過激活流程（調試模式）")

    # 創建並啟動應用程序
    app = Application.get_instance()
    return await app.run(mode=args.mode, protocol=args.protocol)


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("程序被用戶中斷")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序異常退出: {e}", exc_info=True)
        sys.exit(1)
