# -*- coding: utf-8 -*-
"""
"import" is not the same as "register"
"""
from resources import resources

@resources.register_func
def foo():
    yield 'foo'


def test_import_vs_register():
    assert not hasattr(resources, 'foo_ctx')
    resources.register_mod(__name__)
    assert hasattr(resources, 'foo_ctx')
    resources.unregister_mod(__name__)
    assert not hasattr(resources, 'foo_ctx')
