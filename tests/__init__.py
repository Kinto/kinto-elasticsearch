# -*- coding: utf-8 -*-
import os
import configparser

from kinto import main as kinto_main
from kinto.core.testing import get_user_headers, BaseWebTest as CoreWebTest


here = os.path.abspath(os.path.dirname(__file__))


class BaseWebTest(CoreWebTest):
    api_prefix = "v1"
    entry_point = kinto_main
    config = 'config.ini'

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.headers.update(get_user_headers('mat'))

    def tearDown(self):
        super().tearDown()
        self.app.app.registry.indexer.flush()

    @classmethod
    def get_app_settings(cls, extras=None):
        ini_path = os.path.join(here, cls.config)
        config = configparser.ConfigParser()
        config.read(ini_path)
        settings = dict(config.items('app:main'))
        if extras:
            settings.update(extras)
        return settings
