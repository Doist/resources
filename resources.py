# -*- coding: utf-8 -*-
import inspect
from functools import wraps


class ResourceCollectionManager(object):

    def __init__(self):
        self._modules = set()
        # resource functions (functions making objects)
        self._resource_makers = {}
        # resource registry (attributes, available in current context)
        self._resource_registry = {}
        # resource managers (those which ensure "start" and "stop" functionality)
        self._resource_managers = {}

    @property
    def __members__(self):
        return self._resource_registry.keys()

    @property
    def __methods__(self):
        keys = self._resource_makers.keys()
        ctx_keys = ['%s_ctx' % key for key in keys]
        mgr_keys = ['%s_mgr' % key for key in keys]
        return ctx_keys + mgr_keys

    def register_mod(self, module_name):
        """
        Find and register all resources in the module with a given name
        :param module_name: string with a module name
        """
        self._modules.add(module_name)
        __import__(module_name)

    def register_func(self, func):
        """
        Decorator to register function as a resource
        """
        resource_id = getattr(func, 'func_name', func.__name__)
        self._resource_makers[resource_id] = {'func': func}
        return func

    def __getattr__(self, item):
        if item.endswith('_ctx'):
            return self._get_decorator_and_context_manager(item[:-4])
        elif item.endswith('_mgr'):
            return self._get_manager(item[:-4])
        else:
            try:
                return self._resource_registry[item]
            except KeyError as e:
                raise AttributeError(str(e))

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError as e:
            raise KeyError(str(e))

    def _get_decorator_and_context_manager(self, resource_id):

        if resource_id not in self._resource_makers.keys():
            raise RuntimeError("Don't know how to create resource %s" % resource_id)
        resource_maker = self._resource_makers[resource_id]['func']

        class DecoratorAndContextManager(object):

            def __init__(mgr, *args, **kwargs):
                # args and kwargs are function args and kwargs...
                mgr.name = kwargs.pop('_name', resource_id)
                mgr.args = args
                mgr.kwargs = kwargs

            def __enter__(mgr):
                mgr.generator = resource_maker(*mgr.args, **mgr.kwargs)
                resource = next(mgr.generator)
                self._resource_registry[mgr.name] = resource
                return resource

            def __exit__(mgr, exc_type, exc_val, exc_tb):
                next(mgr.generator, None)
                self._resource_registry.pop(mgr.name, None)

            def __call__(deco, callable):

                def wrapper(*args, **kwargs):
                    generator = resource_maker(*deco.args, **deco.kwargs)
                    resource = next(generator)
                    self._resource_registry[deco.name] = resource
                    new_args = [resource, ]
                    new_args += list(args)
                    ret = callable(*new_args, **kwargs)
                    next(generator, None)
                    self._resource_registry.pop(deco.name, None)
                    return ret

                # actually, if you don't use py.test which tries to instrospect
                # function signature, it's enough to write
                # add @wraps(callable) decorator to the wrapper and the return it
                # But as we need to "mock" the function signature too,
                # we're forced to do the trick.
                # See http://emptysquare.net/blog/copying-a-python-functions-signature/
                # and http://www.python.org/dev/peps/pep-0362/#boundarguments-object

                argspec = inspect.getargspec(callable)

                try:
                    argspec.args.pop(0)
                except IndexError as e:
                    pass

                formatted_args = inspect.formatargspec(*argspec).lstrip('(').rstrip(')')
                fndef = 'lambda %s: wrapper(%s)' % (formatted_args, formatted_args)
                fake_fn = eval(fndef, {'wrapper': wrapper})
                return wraps(callable)(fake_fn)

        return DecoratorAndContextManager

    def _get_manager(self, resource_id):

        if resource_id in self._resource_managers:
            return self._resource_managers[resource_id]

        if resource_id not in self._resource_makers.keys():
            raise RuntimeError("Don't know how to create resource %s" % resource_id)
        resource_maker = self._resource_makers[resource_id]['func']
        resource_manager = ResourceManager(self, resource_id, resource_maker)
        self._resource_managers[resource_id] = resource_manager

        return resource_manager


class ResourceManager(object):

    def __init__(self, resource_collection_manager, resource_id, resource_maker):
        self.resource_collection_manager = resource_collection_manager
        self.resource_id = resource_id
        self.resource_maker = resource_maker
        self.generators = {}

    def start(self, *args, **kwargs):
        name = kwargs.pop('_name', self.resource_id)
        if name in self.resource_collection_manager._resource_registry:
            raise RuntimeError('Resource with name %r has been already started' % name)

        generator = self.resource_maker(*args, **kwargs)
        resource = next(generator)
        self.generators[name] = generator
        self.resource_collection_manager._resource_registry[name] = resource
        return resource

    def stop(self, _name=None):
        name = _name or self.resource_id
        try:
            generator = self.generators[name]
        except KeyError:
            raise RuntimeError('Resource %r has not been started' % name)
        next(generator, None)
        self.generators.pop(name, None)
        self.resource_collection_manager._resource_registry.pop(name, None)


resources = ResourceCollectionManager()
