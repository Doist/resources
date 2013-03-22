# -*- coding: utf-8 -*-
"""
"import" is not the same as "register"
"""
from resources import resources, ResourceCollectionManager

@resources.register_func
def foo():
    yield 'foo'


def test_import_vs_register():
    assert not hasattr(resources, 'foo_ctx')
    resources.register_mod(__name__)
    assert hasattr(resources, 'foo_ctx')
    resources.unregister_mod(__name__)
    assert not hasattr(resources, 'foo_ctx')


def test_regiser_with_several_resources():
    resources1 = ResourceCollectionManager()
    resources1.register_mod(__name__)
    assert hasattr(resources1, 'foo_ctx')

    resources2 = ResourceCollectionManager()
    resources2.register_mod(__name__)
    assert hasattr(resources2, 'foo_ctx')
