import ctypes
import logging
import os
import pathlib
import secrets
import sys
import tempfile
import zipfile
from typing import Any, List, Optional, Union

__all__ = [
    "Config",
    "find_chrome_executable",
    "temp_profile_dir",
    "is_root",
    "is_posix",
    "PathLike",
]

logger = logging.getLogger(__name__)
is_posix = sys.platform.startswith(("darwin", "cygwin", "linux", "linux2"))

PathLike = Union[str, pathlib.Path]
AUTO = None


class Config:
    """
    Config object
    """

    def __init__(
        self,
        user_data_dir: Optional[PathLike] = AUTO,
        headless: Optional[bool] = False,
        browser_executable_path: Optional[PathLike] = AUTO,
        browser_args: Optional[List[str]] = AUTO,
        sandbox: Optional[bool] = True,
        lang: Optional[str] = None,
        host: str | None = AUTO,
        port: int | None = AUTO,
        expert: bool | None = AUTO,
        browser_connection_timeout: float = 0.25,
        browser_connection_max_tries: int = 10,
        user_agent: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        creates a config object.
        Can be called without any arguments to generate a best-practice config, which is recommended.

        calling the object, eg :  myconfig() , will return the list of arguments which
        are provided to the browser.

        additional arguments can be added using the :py:obj:`~add_argument method`

        Instances of this class are usually not instantiated by end users.

        :param user_data_dir: the data directory to use (must be unique if using multiple browsers)
        :param headless: set to True for headless mode
        :param browser_executable_path: specify browser executable, instead of using autodetect
        :param browser_args: forwarded to browser executable. eg : ["--some-chromeparam=somevalue", "some-other-param=someval"]
        :param sandbox: disables sandbox
        :param autodiscover_targets: use autodiscovery of targets
        :param lang: language string to use other than the default "en-US,en;q=0.9"
        :param user_agent: custom user-agent string
        :param expert: when set to True, enabled "expert" mode.
               This conveys, the inclusion of parameters: --disable-web-security ----disable-site-isolation-trials,
               as well as some scripts and patching useful for debugging (for example, ensuring shadow-root is always in "open" mode)

        :param kwargs:

        :type user_data_dir: PathLike
        :type headless: bool
        :type browser_executable_path: PathLike
        :type browser_args: list[str]
        :type sandbox: bool
        :type lang: str
        :type user_agent: str
        :type kwargs: dict
        """

        if not browser_args:
            browser_args = []

        # defer creating a temp user data dir until the browser requests it so
        # config can be used/reused as a template for multiple browser instances
        self._user_data_dir = None
        self._custom_data_dir = False
        if user_data_dir:
            self.user_data_dir = str(user_data_dir)

        if not browser_executable_path:
            browser_executable_path = find_chrome_executable()

        self._browser_args = browser_args
        self.browser_executable_path = browser_executable_path
        self.headless = headless
        self.user_agent = user_agent
        self.sandbox = sandbox
        self.host = host
        self.port = port
        self.expert = expert
        self._extensions: list[PathLike] = []

        # when using posix-ish operating system and running as root
        # you must use no_sandbox = True, which in case is corrected here
        if is_posix and is_root() and sandbox:
            logger.info("detected root usage, auto disabling sandbox mode")
            self.sandbox = False

        self.autodiscover_targets = True
        self.lang = lang

        self.browser_connection_timeout = browser_connection_timeout
        self.browser_connection_max_tries = browser_connection_max_tries

        # other keyword args will be accessible by attribute
        self.__dict__.update(kwargs)
        super().__init__()
        self._default_browser_args = [
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-service-autorun",
            "--no-default-browser-check",
            "--homepage=about:blank",
            "--no-pings",
            "--password-store=basic",
            "--disable-infobars",
            "--disable-breakpad",
            "--disable-component-update",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-background-networking",
            "--disable-dev-shm-usage",
            "--disable-features=IsolateOrigins,DisableLoadExtensionCommandLineSwitch,site-per-process",
            "--disable-session-crashed-bubble",
            "--disable-search-engine-choice-screen",
        ]

    @property
    def browser_args(self):
        return sorted(self._default_browser_args + self._browser_args)

    @property
    def user_data_dir(self) -> str:
        """
        Get the user data dir or lazily create a new one if unset.

        Returns:
            str: User data directory (used for Chrome profile)
        """
        if not self._user_data_dir:
            self._user_data_dir = temp_profile_dir()
            self._custom_data_dir = False

        return self._user_data_dir

    @user_data_dir.setter
    def user_data_dir(self, path: PathLike):
        if path:
            self._user_data_dir = str(path)
            self._custom_data_dir = True
        else:
            self._user_data_dir = None
            self._custom_data_dir = False

    @property
    def uses_custom_data_dir(self) -> bool:
        return self._custom_data_dir

    def add_extension(self, extension_path: PathLike):
        """
        adds an extension to load, you could point extension_path
        to a folder (containing the manifest), or extension file (crx)

        :param extension_path:
        :type extension_path:
        :return:
        :rtype:
        """
        path = pathlib.Path(extension_path)

        if not path.exists():
            raise FileNotFoundError("could not find anything here: %s" % str(path))

        if path.is_file():
            tf = tempfile.mkdtemp(prefix="extension_", suffix=secrets.token_hex(4))
            with zipfile.ZipFile(path, "r") as z:
                z.extractall(tf)
                self._extensions.append(tf)

        elif path.is_dir():
            for item in path.rglob("manifest.*"):
                path = item.parent
            self._extensions.append(path)

    # def __getattr__(self, item):
    #     if item not in self.__dict__:

    def __call__(self):
        # the host and port will be added when starting
        # the browser, as by the time it starts, the port
        # is probably already taken
        args = self._default_browser_args.copy()

        args += ["--user-data-dir=%s" % self.user_data_dir]
        args += ["--disable-features=IsolateOrigins,site-per-process"]
        args += ["--disable-session-crashed-bubble"]
        if self.expert:
            args += ["--disable-web-security", "--disable-site-isolation-trials"]
        if self._browser_args:
            args.extend([arg for arg in self._browser_args if arg not in args])
        if self.headless:
            args.append("--headless=new")
        if self.user_agent:
            args.append(f"--user-agent={self.user_agent}")
        if not self.sandbox:
            args.append("--no-sandbox")
        if self.host:
            args.append("--remote-debugging-host=%s" % self.host)
        if self.port:
            args.append("--remote-debugging-port=%s" % self.port)
        return args

    def add_argument(self, arg: str):
        if any(
            x in arg.lower()
            for x in [
                "headless",
                "data-dir",
                "data_dir",
                "no-sandbox",
                "no_sandbox",
                "lang",
            ]
        ):
            raise ValueError(
                '"%s" not allowed. please use one of the attributes of the Config object to set it'
                % arg
            )
        self._browser_args.append(arg)

    def __repr__(self):
        s = f"{self.__class__.__name__}"
        for k, v in ({**self.__dict__, **self.__class__.__dict__}).items():
            if k[0] == "_":
                continue
            if not v:
                continue
            if isinstance(v, property):
                v = getattr(self, k)
            if callable(v):
                continue
            s += f"\n\t{k} = {v}"
        return s

    #     d = self.__dict__.copy()
    #     d.pop("browser_args")
    #     d["browser_args"] = self()
    #     return d


def is_root():
    """
    helper function to determine if user trying to launch chrome
    under linux as root, which needs some alternative handling
    :return:
    :rtype:
    """
    if sys.platform == "win32":
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    else:
        return os.getuid() == 0


def temp_profile_dir():
    """generate a temp dir (path)"""
    path = os.path.normpath(tempfile.mkdtemp(prefix="uc_"))
    return path


def find_chrome_executable() -> PathLike:
    """
    Finds the chrome, beta, canary, chromium executable
    and returns the disk path
    """
    candidates = []
    if is_posix:
        for item in os.environ["PATH"].split(os.pathsep):
            for subitem in (
                "google-chrome",
                "chromium",
                "chromium-browser",
                "chrome",
                "google-chrome-stable",
            ):
                candidates.append(os.sep.join((item, subitem)))
        if "darwin" in sys.platform:
            candidates += [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]

    else:
        for item2 in map(
            os.environ.get,
            ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA", "PROGRAMW6432"),
        ):
            if item2 is not None:
                for subitem in (
                    "Google/Chrome/Application",
                    "Google/Chrome Beta/Application",
                    "Google/Chrome Canary/Application",
                    "Google/Chrome SxS/Application",
                ):
                    candidates.append(os.sep.join((item2, subitem, "chrome.exe")))
    rv = []
    for candidate in candidates:
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            logger.debug("%s is a valid candidate... " % candidate)
            rv.append(candidate)
        else:
            logger.debug(
                "%s is not a valid candidate because don't exist or not executable "
                % candidate
            )

    winner = None

    if rv and len(rv) > 1:
        # assuming the shortest path wins
        winner = min(rv, key=lambda x: len(x))

    elif len(rv) == 1:
        winner = rv[0]

    if winner:
        return os.path.normpath(winner)

    raise FileNotFoundError(
        "could not find a valid chrome browser binary. please make sure chrome is installed."
        "or use the keyword argument 'browser_executable_path=/path/to/your/browser' "
    )
