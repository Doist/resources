# -*- coding: utf-8 -*-
import pytest
from resources import resources

resources.register_mod(__name__)



@resources.register_func
def user(name='John Doe'):
    """
    register function user as a resource.

    The returned (yielded) value will be used as a resource, function
    name will be converted to a resource name
    """
    yield {'name': name}


@resources.register_func
def todo_item(text='Do something'):
    """
    Test of dependent resource which can be added only if user resource
    does exist.
    """
    yield {'user': resources.user, 'text': text}


def test_context_manager():
    assert not hasattr(resources, 'user')
    with resources.user_ctx():
        assert resources.user == {'name': 'John Doe'}
    assert not hasattr(resources, 'user')


def test_context_manager_and_different_user_name():
    assert not hasattr(resources, 'user')
    with resources.user_ctx(name='Mary Moe'):
        assert resources.user == {'name': 'Mary Moe'}
    assert not hasattr(resources, 'user')


def test_context_manager_and_two_resources():
    with resources.user_ctx(name='Mary Moe', _name='mary'):
        with resources.user_ctx(name='John Doe', _name='john'):
            # get resources by names
            assert resources.john == {'name': 'John Doe'}
            assert resources.mary == {'name': 'Mary Moe'}
            # get resources by keys
            assert resources['john'] == {'name': 'John Doe'}
            assert resources['mary'] == {'name': 'Mary Moe'}


def test_dependent_resources():
    with resources.user_ctx():
        with resources.todo_item_ctx():
            assert resources.todo_item['user'] == resources['user']


def test_decorator():

    @resources.user_ctx()
    def func(user):
        assert user == resources.user == {'name': 'John Doe'}
    assert not hasattr(resources, 'user')
    func()
    assert not hasattr(resources, 'user')


def test_decorator_2():
    @resources.user_ctx(name='Mary Moe', _name='mary')
    def func(user):
        assert user == resources.mary == {'name': 'Mary Moe'}
    assert not hasattr(resources, 'mary')
    func()
    assert not hasattr(resources, 'mary')


def test_mgr():
    assert not hasattr(resources, 'user')
    user = resources.user_mgr.start()
    assert user == resources.user == {'name': 'John Doe'}
    resources.user_mgr.stop()
    assert not hasattr(resources, 'user')


def test_mgr_with_different_name():
    assert not hasattr(resources, 'mary')
    resources.user_mgr.start(_name='mary', name='Mary Moe')
    assert resources.mary == {'name': 'Mary Moe'}
    resources.user_mgr.stop(_name='mary')
    assert not hasattr(resources, 'user')


def test_mgr_same_instance():
    assert resources.user_mgr == resources.user_mgr


def test_mgr_stop_unstarted():
    with pytest.raises(RuntimeError):
        resources.user_mgr.stop()


def test_mgr_start_twice():
    resources.user_mgr.start()
    with pytest.raises(RuntimeError):
        resources.user_mgr.start()

def test_mgr_start_twice_with_different_names():
    resources.user_mgr.start(_name='foo')
    resources.user_mgr.start(_name='bar')

    assert hasattr(resources, 'foo')
    assert hasattr(resources, 'bar')

    resources.user_mgr.stop(_name='bar')
    resources.user_mgr.stop(_name='foo')

    assert not hasattr(resources, 'foo')
    assert not hasattr(resources, 'bar')


def test_resources_with_same_name():
    """
    ensure we don't have any IndexErrors or whatever
    """
    with resources.user_ctx():
        with resources.user_ctx():
            pass
