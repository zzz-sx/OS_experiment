"""独立模块入口，共享审计过的实现。"""
import sys
from server import main
if __name__ == "__main__":
    sys.argv += ["--module", "process"]
    main()
