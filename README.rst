Resources. A fixture lifecycle management library for your tests
=================================================================

Why do we need this library
--------------------------------------------------

We are not satisfied with classical xUnit way of setup and teardown. We prefer
concise approach of py.test over the verbosity of standard unittest.

We found ourselves copying and pasting the same boilerplate code from one test
to another or creating extensive structure of test class hierarchy.

py.test fixtures, injected in test functions as parameter names, is
different approach for fixture management. It's neither worse nor better,
although it's not as flexible as we need. For example, how can I create a user
with non-default name in the test? Or create two users to see how they interact
with each other? Or is there an easy recipe to create a user first, and then,
say, a todo item for this particular user in another fixture?

Sure enough, we can handle all these issues with xUnit setups and teardowns or
py.test fixtures, but we wanted something more flexible, easy and convenient to
use. That's why we created ``resources`` library.


How do we use it
----------------

First, we define functions which we call "resource makers". They are
responsible for creating and destroying resources. It's like setup and teardown
in one callable.

.. code-block:: python

    from resources import resources

    @resources.register_func
    def user(email='joe@example.com', password='password', username='Joe'):
        user = User.objects.create(email=email, password=password, username=username)
        try:
            yield user
        finally:
            user.delete()

The flow is simple: we create, we yield, we destroy.

We get a number of resource makers, and we group them into modules, like
:file:`tests/resources_core.py`, :file:`tests/resources_users.py`, etc.

Then, in a test file, where we plan to use resources, we import the same global
object, load resource modules we need, and activate them in tests.

.. code-block:: python

    from resources import resources
    resources.register_mod('tests.resources_core')
    resources.register_mod('tests.resources_users')

    def test_user_properties():
        with resources.user_ctx() as user:
            assert user.username == 'Joe'

This is where a little bit of magic happens. Once you define and register the
resource maker with name ``foo``, a context manager ``foo_ctx`` is created for
your convenience. This context manager creates a new resource instance with the
corresponding maker function, and destroys the object the way you defined, once
the code flow abandons a wrapping "with"-context.

When it shines
---------------

At this point and maybe not so exciting. But we also have a bunch of nifty
features making the whole stuff more interesting.

Feature 1. Customizeable resources
----------------------------------

Contexts are better than py.test fixtures, because they are customizeable.
Provide everything you need to context manager, and it will be passed to
resource maker function as an arguments.

.. code-block:: python

    def test_user_properties():
        with resources.user_ctx(name='Mary') as user:
            assert user.username == 'Mary'


Feature 2. Global object scope and denepdent resources
------------------------------------------------------

We need to have access to resources at different stages of our tests: to get
access to object's properties and methods, to initiate another, dependent
instance, and finally to tear down.

As soon as you enter the context with ``resources.foo_ctx()`` a variable
``resources.foo`` will be created and will be available from everywhere,
including your test function, and other resource makers.

The latter fact is especially important, because it's the way we manage
dependent resources. Yet we need some conventions, which resource is created
first, and so on.

.. code-block:: python

    @resources.register_func
    def todo_item(content='Foo'):
        item = TodoItem.objects.create(user=resources.user, content=content)

We agreed that we create user resource first, and todo item afterwards, and
created a new resource maker, taking advantage of this convention.

We use it like this:

.. code-block:: python

    def test_todo_item_properties():
        with resources.user_ctx(), resources.todo_item_ctx():
            assert resources.todo_item.content == 'Foo'

By the way, if you are still stuck with python2.6, several context managers in
the same "with" expression aren't available for you yet. Use ``contextlib.nested``
to avoid deep indentation.


Feature 3. Several resources of the same class, and tuneable resource names
---------------------------------------------------------------------------

Sometimes we need to create a couple of resources of the same type, instead of
just one instance. It's not a problem, if you don't want to use global
namespace to get access to them. Otherwise you must create a unique identifier
for every resource.

Actually, it's trivial. All you should do is provide a special `_name` attribute
to context manager constructor. This
 attribute won't be passed to your resource
maker function.

.. code-block:: python

    def test_a_couple_of_users():
        with resources.user_ctx(username='Adam', _name='adam'), \
             resurces.user_ctx(username='Eve', _name='eve'):
            assert resources.adam.username == 'Adam'
            assert resources.eve.username == 'Eve'


Feature 4. Function decorators
------------------------------

Context manager can work as a decorator too. When we use it like this, an extra
argument will be passed to the function.

.. code-block:: python

    @resources.user_ctx()
    def test_user_properties(user):
        assert user.username == 'Joe'

We should say that usually it works, but to make it work along with py.test
which performs deep introspection of function signatures, we made in with some
"dirty hacks" inside, and you may find out that in some cases the chain of
decorators dies with a misleading exception. We'd recommend to use context
managers instead of decorators, wherever possible.

Feature 5. Resource managers
----------------------------

Yes, we do use setup and teardown methods too. If every function in your test
suite uses the same set of resources, it would be counterproductive to write
the same chain of decorators or context managers over and over again.

In this case we use another concept: resource managers. Every resource maker
``foo`` creates the ``resources.foo_mgr`` instance, having :func:`start` and
:func:`stop` methods. The `start` method accepts all arguments which
the :func:`foo_ctx` function does, including special `_name` argument.
The `stop` method has only one optional `_name` argument, and is used to
destroy previously created instance.

Here is a py.test example

.. code-block:: python

    def setup_function(func):
        resources.user_mgr.start(username='Mary')

    def test_user_properties():
        assert resources.user.username == 'Mary'

    def teardown_function(func):
        resources.user_mgr.stop()


Conclusion
----------

Five extra features to improve your test suite for free! It's already improved
the quailty of our lives in `Doist Inc <http://doist.io>`_, and we do hope it
will does the same for your projects.
