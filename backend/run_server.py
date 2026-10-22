"""PyInstaller 打包入口：启动本地 uvicorn 服务（供桌面 exe 拉起）。

- 绑定 127.0.0.1，仅本机可访问；
- 端口 / 主机可通过环境变量 SMARTMALL_HOST / SMARTMALL_PORT 覆盖。
"""
import os

import uvicorn

from main import app


def main() -> None:
    host = os.environ.get("SMARTMALL_HOST", "127.0.0.1")
    port = int(os.environ.get("SMARTMALL_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
