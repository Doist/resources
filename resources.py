# -*- coding: utf-8 -*-
import inspect
from functools import wraps

# resource functions (functions making objects)
# key is the resource name (i.e. "user"), value is the dict, containing
# currently only one key: func: callable object

# It's a global object, because it should be shared between all resource
# instances
_resource_makers = {}


def register_func(func):
    """
    Decorator to register function as a resource
    """
    resource_id = func.__name__
    _resource_makers[resource_id] = {'func': func}
    return func


class ResourceCollectionManager(object):

    def __init__(self):
        self._modules = set()
        # resource registry (attributes, available in current context)
        # key is the resource name (i.e. "user"), value is the instantiated
        # object, if any (the object will be instantiated if we are within the
        # "with"-context, for example.
        self._resource_registry = {}
        # resource managers (those which ensure "start" and "stop" functionality)
        # actually, it's a dict which contains unfinished generators.
        # key is the resource name, value is the generator instance
        # Instances are added to this dict, when a xxx_mgr.start()/xxx_mgr.stop()
        # methods are used.
        self._resource_managers = {}

    def _active_resource_makers(self):
        """
        Return the subset of _resource_makers.keys() registered with "register_mod"
        """
        ret = set()
        for key, value in _resource_makers.items():
            if value['func'].__module__ in self._modules:
                ret.add(key)
        return ret

    @property
    def __members__(self):
        return self._resource_registry.keys()

    @property
    def __methods__(self):
        keys = self._active_resource_makers()
        ctx_keys = ['%s_ctx' % key for key in keys]
        mgr_keys = ['%s_mgr' % key for key in keys]
        return ctx_keys + mgr_keys

    def register_mod(self, module_name):
        """
        Find and register all resources in the module with a given name
        :param module_name: string with a module name
        """
        self._modules.add(module_name)
        mod = __import__(module_name)

    def unregister_mod(self, module_name):
        """
        Unregister a module, make resources from the module unavailable.
        :param module_name: string with a module name
        """
        self._modules.remove(module_name)

    def register_func(self, func):
        """
        Decorator to register function as a resource
        """
        # todo: copy-paste of the global function
        # kept within object for convenience and backward compatibility
        resource_id = func.__name__
        _resource_makers[resource_id] = {'func': func}
        return func

    def __getattr__(self, item):
        if item.endswith('_ctx'):
            try:
                return self._get_decorator_and_context_manager(item[:-4])
            except RuntimeError as e:
                raise AttributeError(str(e))
        elif item.endswith('_mgr'):
            try:
                return self._get_manager(item[:-4])
            except RuntimeError as e:
                raise AttributeError(str(e))
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

        if resource_id not in self._active_resource_makers():
            raise RuntimeError("Don't know how to create resource %s" % resource_id)
        resource_maker = _resource_makers[resource_id]['func']

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

        if resource_id not in self._active_resource_makers():
            raise RuntimeError("Don't know how to create resource %s" % resource_id)
        resource_maker = _resource_makers[resource_id]['func']
        resource_manager = ResourceManager(self, resource_id, resource_maker)
        self._resource_managers[resource_id] = resource_manager

        return resource_manager

    # some helper functions

    def pdb(self):
        try:
            import ipdb
        except ImportError:
            import pdb as ipdb
        ipdb.set_trace()

    def shell(self, namespace=None):
        try:
            from IPython import embed
        except ImportError:
            import code
            import readline
            import rlcompleter
            # we must pass at least something in here
            if namespace is None:
                namespace = {'resources': resources}
            code.InteractiveConsole(namespace).interact()
        else:
            embed()


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
